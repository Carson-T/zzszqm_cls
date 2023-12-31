import torch.optim.lr_scheduler
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler
import torch.backends.cudnn as cudnn
from torchvision import models
import json
import random
import timm
from sklearn.metrics import roc_auc_score, roc_curve, auc
from torch.utils.tensorboard import SummaryWriter
from train import *
from dataset import *
from argparser import args_parser
from model import *
from utils.loss import *
from utils.plot import plot_matrix
from utils.transform import *
from utils.function import *


def set_seed(seed=2023):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    cudnn.benchmark = True
    cudnn.deterministic = True
    os.environ['PYTHONHASHSEED'] = str(seed)


def main(args, model):
    writer = SummaryWriter(log_dir=args["log_dir"] + "/" + args["model_name"])
    # scaler = GradScaler()
    # train_transform, val_transform, test_transform = tv_transform(args)
    train_transform, val_transform, test_transform = at_transform(args)
    train_loader = DataLoader(TrainValDataset(args["train_csv_path"], train_transform, args["mode"]),
                              batch_size=args["batch_size"], shuffle=True, num_workers=args["num_workers"],
                              pin_memory=True, drop_last=True)
    val_loader = DataLoader(TrainValDataset(args["val_csv_path"], val_transform, args["mode"]),
                            batch_size=args["batch_size"], shuffle=True, num_workers=args["num_workers"],
                            pin_memory=True, drop_last=True)

    test_loader = DataLoader(TestDataset(args["test_path"], test_transform, args["mode"]),
                             batch_size=args["batch_size"], shuffle=False, num_workers=args["num_workers"],
                             pin_memory=True, drop_last=False)

    print("num of train images:", len(train_loader.dataset))
    print("num of val images:", len(val_loader.dataset))
    print("num of test images:", len(test_loader.dataset))

    head = model.get_head()
    base_params = filter(lambda p: id(p) not in list(map(id, head.parameters())),
                         model.parameters())
    groups_params = [{"params": base_params, "lr": args["lr"][0]},
                     {"params": head.parameters(), "lr": args["lr"][1]}]

    if args["is_parallel"] == 1:
        model = nn.DataParallel(model, device_ids=args["device_ids"])
    model.to(args["device"])
    # if args["init"] == "xavier":
    #     model.apply(xavier)
    # elif args["init"] == "kaiming":
    #     model.apply(kaiming)

    if args["optim"] == "AdamW":
        optimizer = torch.optim.AdamW(groups_params, weight_decay=args["weight_decay"])
    elif args["optim"] == "SGD":
        optimizer = torch.optim.SGD(groups_params, momentum=0.9, weight_decay=args["weight_decay"])

    if args["loss_func"] == "CEloss":
        loss_func = torch.nn.CrossEntropyLoss().to(args["device"])
    # elif args["loss_func"] == "FocalLoss":
    #     loss_func = FocalLoss().to(args["device"])
    elif args["loss_func"] == "LabelSmoothLoss":
        weight = torch.Tensor([1.0, 1.0]).to(args["device"])
        loss_func = LabelSmoothLoss(weight).to(args["device"])

    if args["lr_scheduler"] == "Warm-up-Cosine-Annealing":
        init_ratio, warm_up_steps, min_lr_ratio, max_steps = args["init_ratio"], args["epochs"] / 10, args[
            "min_lr_ratio"], args["epochs"]
        lr_scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda step: \
            (1 - init_ratio) / (warm_up_steps - 1) * step + init_ratio if step < warm_up_steps - 1 \
                else (1 - min_lr_ratio) * 0.5 * (np.cos(
                (step - (warm_up_steps - 1)) / (max_steps - (warm_up_steps - 1)) * np.pi) + 1) + min_lr_ratio)
    elif args["lr_scheduler"] == "StepLR":
        lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=args["step_size"], gamma=args["gamma"])

    best_test_auc = 0
    best_epoch_metrics = []
    init_epoch = 1

    if args["resume"] != "":
        checkpoint = torch.load(args["resume"])
        model.load_state_dict(checkpoint["model_state"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        lr_scheduler.load_state_dict(checkpoint["lr_scheduler"])
        init_epoch = checkpoint["epoch"] + 1
        best_test_auc = checkpoint["best_test_auc"]

    for iter in range(init_epoch, args["epochs"] + 1):
        train_outputs, train_targets, train_loss = train(train_loader, model, loss_func, optimizer, args)
        val_outputs, val_targets, val_loss = val(val_loader, model, loss_func, args)
        test_outputs, test_targets, test_loss = test(test_loader, model, loss_func, args)
        lr_scheduler.step()

        train_preds = torch.argmax(train_outputs, dim=1)
        val_preds = torch.argmax(val_outputs, dim=1)
        test_preds = torch.argmax(test_outputs, dim=1)

        train_acc = (train_preds == train_targets).sum().item() / len(train_targets)
        val_acc = (val_preds == val_targets).sum().item() / len(val_targets)
        test_acc = (test_preds == test_targets).sum().item() / len(test_targets)

        train_auc = roc_auc_score(train_targets, train_outputs[:, 1])
        val_auc = roc_auc_score(val_targets, val_outputs[:, 1])
        test_auc = roc_auc_score(test_targets, test_outputs[:, 1])

        print(f'Epoch {iter}: train acc: {train_acc}')
        print(f'Epoch {iter}: val acc: {val_acc}')
        print(f'Epoch {iter}: test acc: {test_acc}')
        print(f'Epoch {iter}: train auc: {train_auc}')
        print(f'Epoch {iter}: val auc: {val_auc}')
        print(f'Epoch {iter}: test auc: {test_auc}')

        writer.add_scalars("acc", {"train_acc": train_acc, "val_acc": val_acc, "test_acc": test_acc}, iter)
        writer.add_scalars("auc", {"train_auc": train_auc, "val_auc": val_auc, "test_auc": test_auc}, iter)
        writer.add_scalars("loss",
                           {"train_loss": train_loss / len(train_targets), "val_loss": val_loss / len(val_targets),
                            "test_loss": test_loss / len(test_targets)}, iter)

        if test_auc > best_test_auc:
            best_epoch_metrics = [round(i,4) for i in [train_acc, val_acc, test_acc, train_auc, val_auc, test_auc]]
            best_test_auc = test_auc
            plot_matrix(test_targets, test_preds, [0, 1],
                        args["log_dir"] + "/" + args["model_name"] + "/confusion_matrix.jpg",
                        ['standards', 'non-standards'])
            torch.save(model.state_dict(), args["saved_path"] + "/" + args["model_name"] + ".pth")

        if iter % 10 == 0:
            save_ckpt(args, model, optimizer, lr_scheduler, iter, best_test_auc)

    log_metrics(best_epoch_metrics, args)

if __name__ == '__main__':
    args = vars(args_parser())
    set_seed(2023)

    if args["pretrained_path"]:
        pretrained_model = models.convnext_base()
        pretrained_model.load_state_dict(torch.load(args["pretrained_path"]), strict=True)
        model = Convnext_base_tv(pretrained_model, args["num_classes"])
    else:
        if args["drop_path_rate"] > 0:
            pretrained_model = timm.create_model(args["backbone"], drop_rate=args["drop_rate"],
                                                 drop_path_rate=args["drop_path_rate"], pretrained=True)
        else:
            pretrained_model = timm.create_model(args["backbone"], drop_rate=args["drop_rate"], pretrained=True)

        if "resnet" in args["backbone"]:
            model = Resnet(pretrained_model, args["num_classes"])

        elif "efficientnet" in args["backbone"]:
            model = Efficientnet(pretrained_model, args["num_classes"])

        elif "convnext" in args["backbone"]:
            model = Convnext(pretrained_model, args["num_classes"])

    main(args, model)

    with open(args["log_dir"] + "/" + args["model_name"] + "/parameters.json", "w+") as f:
        json.dump(args, f)
