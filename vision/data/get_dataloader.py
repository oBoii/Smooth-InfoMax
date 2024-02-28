import torch
import torchvision.transforms as transforms
import torchvision
import os
import numpy as np
from torchvision.transforms import transforms

from config_code.config_classes import DataSetConfig, Dataset

NUM_WORKERS = 0 #1 #16

def get_dataloader(config: DataSetConfig, purpose_is_unsupervised_learning: bool):
    if config.dataset == Dataset.STL10:
        train_loader, train_dataset, supervised_loader, supervised_dataset, test_loader, test_dataset = get_stl10_dataloader(
            config, purpose_is_unsupervised_learning
        )
    else:
        raise Exception("Invalid option")

    return (
        train_loader,
        train_dataset,
        supervised_loader,
        supervised_dataset,
        test_loader,
        test_dataset,
    )


def get_stl10_dataloader(config: DataSetConfig, purpose_is_unsupervised_learning: bool):
    base_folder = os.path.join(config.data_input_dir, "stl10_binary")

    aug = {
        "stl10": {
            "randcrop": 64,
            "flip": True,
            "grayscale": config.grayscale,
            "mean": [0.4313, 0.4156, 0.3663],  # values for train+unsupervised combined
            "std": [0.2683, 0.2610, 0.2687],
            "bw_mean": [0.4120],  # values for train+unsupervised combined
            "bw_std": [0.2570],
        }  # values for labeled train set: mean [0.4469, 0.4400, 0.4069], std [0.2603, 0.2566, 0.2713]
    }
    transform_train = transforms.Compose(
        [get_transforms(eval=False, aug=aug["stl10"])]
    )
    transform_valid = transforms.Compose(
        [get_transforms(eval=True, aug=aug["stl10"])]
    )

    unsupervised_dataset = torchvision.datasets.STL10(
        base_folder,
        split="unlabeled",
        transform=transform_train,
        download=True,
    )  # set download to True to get the dataset

    train_dataset = torchvision.datasets.STL10(
        base_folder, split="train", transform=transform_train, download=True
    )

    test_dataset = torchvision.datasets.STL10(
        base_folder, split="test", transform=transform_valid, download=True
    )

    # default dataset loaders
    train_loader = torch.utils.data.DataLoader(
        train_dataset, batch_size=config.batch_size_multiGPU, shuffle=True, num_workers=NUM_WORKERS
    )

    unsupervised_loader = torch.utils.data.DataLoader(
        unsupervised_dataset,
        batch_size=config.batch_size_multiGPU,
        shuffle=True,
        num_workers=NUM_WORKERS,
    )

    test_loader = torch.utils.data.DataLoader(
        test_dataset, batch_size=config.batch_size_multiGPU, shuffle=False, num_workers=NUM_WORKERS
    )

    # create train/val split
    # TODO
    validate = True
    if validate:
        print("Use train / val split")

        # "train" for train, "unlabeled" for unsupervised, "test" for test
        if purpose_is_unsupervised_learning:
            dataset_size = len(train_dataset)
            train_sampler, valid_sampler = create_validation_sampler(dataset_size)

            train_loader = torch.utils.data.DataLoader(
                train_dataset,
                batch_size=config.batch_size_multiGPU,
                sampler=train_sampler,
                num_workers=NUM_WORKERS,
            )
        else:  # supervised learning, with the smaller labeled dataset
            dataset_size = len(unsupervised_dataset)
            train_sampler, valid_sampler = create_validation_sampler(dataset_size)

            unsupervised_loader = torch.utils.data.DataLoader(
                unsupervised_dataset,
                batch_size=config.batch_size_multiGPU,
                sampler=train_sampler,
                num_workers=NUM_WORKERS,
            )

        # overwrite test_dataset and _loader with validation set
        test_dataset = torchvision.datasets.STL10(
            base_folder,
            # split=config.training_dataset,
            # split can be "train" or "test" or "unlabeled"
            split="train" if purpose_is_unsupervised_learning else "unlabeled",
            transform=transform_valid,
            download=True,
        )

        test_loader = torch.utils.data.DataLoader(
            test_dataset,
            batch_size=config.batch_size_multiGPU,
            sampler=valid_sampler,
            num_workers=NUM_WORKERS,
        )

    else:
        print("Use (train+val) / test split")

    return (
        unsupervised_loader,
        unsupervised_dataset,
        train_loader,
        train_dataset,
        test_loader,
        test_dataset,
    )


def create_validation_sampler(dataset_size):
    # Creating data indices for training and validation splits:
    validation_split = 0.2
    shuffle_dataset = True

    indices = list(range(dataset_size))
    split = int(np.floor(validation_split * dataset_size))
    if shuffle_dataset:
        np.random.shuffle(indices)
    train_indices, val_indices = indices[split:], indices[:split]

    # Creating data samplers and loaders:
    train_sampler = torch.utils.data.sampler.SubsetRandomSampler(train_indices)
    valid_sampler = torch.utils.data.sampler.SubsetRandomSampler(val_indices)

    return train_sampler, valid_sampler


def get_transforms(eval=False, aug=None):
    trans = []

    if aug["randcrop"] and not eval:
        trans.append(transforms.RandomCrop(aug["randcrop"]))

    if aug["randcrop"] and eval:
        trans.append(transforms.CenterCrop(aug["randcrop"]))

    if aug["flip"] and not eval:
        trans.append(transforms.RandomHorizontalFlip())

    if aug["grayscale"]:
        trans.append(transforms.Grayscale())
        trans.append(transforms.ToTensor())
        trans.append(transforms.Normalize(mean=aug["bw_mean"], std=aug["bw_std"]))
    elif aug["mean"]:
        trans.append(transforms.ToTensor())
        trans.append(transforms.Normalize(mean=aug["mean"], std=aug["std"]))
    else:
        trans.append(transforms.ToTensor())

    trans = transforms.Compose(trans)
    return trans
