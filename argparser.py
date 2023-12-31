import torch
import argparse

def args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument('--num_classes', type=int, default=2)

    parser.add_argument('--resize_h', type=int, default=160)
    parser.add_argument('--resize_w', type=int, default=315)
    parser.add_argument('--Blur', type=int, default=1)
    parser.add_argument('--OGE', type=int, default=1)
    parser.add_argument('--CLAHE', type=int, default=1)
    parser.add_argument('--Cutout', type=int, default=1)
    parser.add_argument('--mode', default="J")  # J: jingxi  V: Valsalva
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--num_workers', type=int, default=8)

    parser.add_argument('--optim', default="AdamW")   
    parser.add_argument('--loss_func', default="CEloss")  # LabelSmoothLoss
    parser.add_argument('--lr_scheduler', default="Warm-up-Cosine-Annealing")  #Warm-up-Cosine-Annealing  StepLR

    parser.add_argument('--lr', type=list, default=[0.00001, 0.00005])
    parser.add_argument('--weight_decay', type=float, default=0.01)
    parser.add_argument('--init_ratio', type=float, default=0.1)       # Warm-up-Cosine-Annealing parameters
    parser.add_argument('--min_lr_ratio', type=float, default=0.001)    # Warm-up-Cosine-Annealing parameters
    parser.add_argument('--step_size', type=int, default=30)  # StepLR
    parser.add_argument('--gamma', type=float, default=0.1)  # StepLR

    parser.add_argument('--init', default="")   # network initialization methods, kaiming or xavier 
    parser.add_argument('--drop_rate', type=float, default=0.3)
    parser.add_argument('--drop_path_rate', type=float, default=0.2)
    parser.add_argument('--epochs', type=int, default=100)

    parser.add_argument('--is_parallel', type=int, default=1)    # DataParallel or not
    parser.add_argument('--device_ids', type=list, default=[0,1])    # if is_parallel==1, specify the cuda id

    parser.add_argument('--resume', default="")
    parser.add_argument('--pretrained_path', default="")
    parser.add_argument('--backbone', default="convnextv2_nano.fcmae_ft_in1k")  # efficientnetv2_rw_s.ra2_in1k  convnextv2_nano.fcmae_ft_in1k  resnet50.tv_in1k
    parser.add_argument('--model_name',  default="convnextv2_n-new_data-J-fold5-v1")  # model version
    parser.add_argument('--train_csv_path', default="../new_data/TrainSet/csv/J_train_fold5.csv")  # train csv path
    parser.add_argument('--val_csv_path',  default="../new_data/TrainSet/csv/J_val_fold5.csv")   # test csv path
    parser.add_argument('--test_path',  default="../new_data/TestSet")  # test data path
    parser.add_argument('--saved_path', default='../saved_model/J/convnext')   # model saved path
    parser.add_argument('--ckpt_path', default='../checkpoints/J/convnext')  # checkpoints path for resume
    parser.add_argument('--log_dir', default="../log/J/convnext")  # tensorboard log path
    parser.add_argument('--metrics_log_path', default="../new_logs.csv")

    args, _ = parser.parse_known_args()
    return args
