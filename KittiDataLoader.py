import cv2
import numpy as np
import os
import torch
from torch.utils.data import Dataset, DataLoader
import albumentations as A


class KittiDataset(Dataset):
    def __init__(self, dataset_folder="e://Code/Tez/bts_eren/kitti", is_test=False):
        self.is_test = is_test

        self.transforms = A.Compose([
            A.HorizontalFlip(),
            A.RandomCrop(352, 704, True)
        ], additional_targets={"label": "image"})

        self.test_transforms = A.Compose([
            A.Crop(int((1224-1216)/2), int((370-352)/2), int((1224-1216)/2) + 1216, int((370-352)/2) + 352, True)
        ], additional_targets={"label": "image"})

        self.image_only_transforms = A.Compose([
            A.RandomBrightnessContrast(),
            A.RandomGamma(),
            A.RGBShift(10),
            A.Normalize()
        ])

        self.test_image_only_transforms = A.Compose([
            A.Normalize(always_apply=True)
        ])

        self.train_drives = []
        self.test_drives = []

        self.inputs_path = os.path.join(dataset_folder, "inputs")
        self.outputs_path = os.path.join(dataset_folder, "data_depth_annotated")
        train_drives_path = os.path.join(self.outputs_path, "train")
        print(train_drives_path)
        test_drives_path = os.path.join(self.outputs_path, "val")

        self.img_path = os.path.join("image_03", "data")
        self.velodyne_path = "velodyne_points\data"
        
        self.label_images_path = os.path.join("proj_depth", "groundtruth", "image_03")

        # Get folder names of drives that will be used in training
        for drive in os.listdir(train_drives_path):
            if ("drive" in drive):
                train_drive_images_path = os.path.join(train_drives_path, drive, self.label_images_path)
                train_drive_images = []
                for train_drive_image in os.listdir(train_drive_images_path):
                    train_drive_images.append(train_drive_image)
                self.train_drives.append([len(train_drive_images), drive, train_drive_images])

        # Get folder names of drives that will be used in testing
        for drive in os.listdir(test_drives_path):
            if ("drive" in drive):
                test_drive_images_path = os.path.join(test_drives_path, drive, self.label_images_path)
                test_drive_images = []
                for test_drive_image in os.listdir(test_drive_images_path):
                    test_drive_images.append(test_drive_image)
                self.test_drives.append([len(test_drive_images), drive, test_drive_images])
        
        self.total_len = 0
        if (is_test):
            self.drives = self.test_drives
            self.drive_labels_path = test_drives_path
            for test_drive_len, _, _ in self.test_drives:
                self.total_len += test_drive_len
        else:
            self.drives = self.train_drives
            self.drive_labels_path = train_drives_path
            for train_drive_len, _, _ in self.train_drives:
                self.total_len += train_drive_len

    def load_label_img(self, drive_path, drive_img):
        img_path = os.path.join(self.drive_labels_path, drive_path, self.label_images_path, drive_img)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        img = np.expand_dims(img, axis=3)

        self.last_input_path = img_path
        return img

    def load_input_img(self, drive_path, drive_img):
        drive = drive_path.split("_drive_")[0]
        img_path = os.path.join(self.inputs_path, drive, drive_path, self.img_path, drive_img)
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = np.array(img, dtype=np.uint8)

        self.last_output_path = img_path
        return img

    def __getitem__(self, item):
        for drive_len, drive_path, drive_image_paths in self.drives:
            if (item < drive_len):
                label_img = self.load_label_img(drive_path, drive_image_paths[item])
                input_img = self.load_input_img(drive_path, drive_image_paths[item])
                data = {'image': input_img, 'label': label_img}

                if self.is_test:
                    data = self.test_transforms(**data)
                else:
                    data = self.transforms(**data)

                if self.is_test:
                    data = self.test_image_only_transforms(**data)
                else:
                    data = self.image_only_transforms(**data)

                data["image"] = torch.tensor(data["image"]).float().transpose(0, 2).transpose(1, 2)
                data["label"] = torch.tensor(data["label"]).float().transpose(0, 2).transpose(1, 2)
                return data
            else:
                # Item isnt in this drive, search in next drive folder
                item -= drive_len

    def __len__(self):
        return self.total_len


def KittiDataLoader(batch_size):
    dataset = KittiDataset()
    return torch.utils.data.DataLoader(dataset, batch_size, shuffle=True)