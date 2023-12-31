import os
import cv2
import numpy as np
from torch.utils.data import Dataset
import pandas as pd
from PIL import Image


class TrainValDataset(Dataset):
    def __init__(self, csv_path, transform, mode):
        super(TrainValDataset, self).__init__()
        self.csv_path = csv_path
        if mode == 'J':
            self.class_dict = {"1.静息-标准": 0, "2.静息-非标准": 1}  # label dictionary
        else:
            self.class_dict = {"3.Valsalva-标准": 0, "4.Valsalva-非标准": 1}  # label dictionary
        self.transform = transform
        self.img_paths, self.labels = self._make_dataset()  # make dataset

    def __len__(self):
        return len(self.img_paths)

    def __getitem__(self, idx):
        img_path = self.img_paths[idx]
        label = self.labels[idx]
        # img = Image.open(img_path)
        img = cv2.imread(img_path)
        # img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), -1)
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        if self.transform:
            # img = self.transform(img)
            img = self.transform(image=img)["image"]
        return img, label

    def _make_dataset(self):
        data = pd.read_csv(self.csv_path)
        img_paths = data["path"].values.tolist()
        labels = [self.class_dict[i] for i in data["label"].values]

        return img_paths, labels


class TestDataset(Dataset):
    def __init__(self, testpath, transform, mode):
        super(TestDataset, self).__init__()
        self.testpath = testpath
        if mode == 'J':
            self.class_dict = {"1.静息-标准": 0, "2.静息-非标准": 1}  # label dictionary
        else:
            self.class_dict = {"3.Valsalva-标准": 0, "4.Valsalva-非标准": 1}  # label dictionary
        self.groups = ["白银", "佛山市一", "广医附三", "湖南省妇幼", "岭南迈瑞"]
        self.transform = transform
        self.img_paths, self.labels = self._make_dataset()  # make dataset

    def __len__(self):
        return len(self.img_paths)

    def __getitem__(self, idx):
        img_path = self.img_paths[idx]
        label = self.labels[idx]
        # img = Image.open(img_path)
        img = cv2.imread(img_path)
        # img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), -1)
        if self.transform:
            # img = self.transform(img)
            img = self.transform(image=img)["image"]
        return img, label

    def _make_dataset(self):
        img_paths = []
        labels = []
        for group in self.groups:
            group_path = os.path.join(self.testpath, group)
            for class_name in self.class_dict:
                class_path = os.path.join(group_path, class_name)
                label = self.class_dict[class_name]
                for file_name in os.listdir(class_path):
                    img_path = os.path.join(class_path, file_name)
                    img_paths.append(img_path)
                    labels.append(label)

        return img_paths, labels

