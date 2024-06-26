import torch.nn as nn
import torch

from config_code.config_classes import OptionsConfig, DataSetConfig, Dataset
from utils import utils


class Supervised_Loss(nn.Module):
    def __init__(self, dataset_config: DataSetConfig, hidden_dim, calc_accuracy, device):
        super(Supervised_Loss, self).__init__()

        self.dataset_config = dataset_config

        self.pool = None
        self.hidden_dim = hidden_dim
        self.calc_accuracy = calc_accuracy

        # create linear classifier
        n_classes = utils.get_nb_classes(dataset_config.dataset)

        self.linear_classifier = nn.Sequential(
            nn.Linear(self.hidden_dim, n_classes)
        ).to(device)

        self.classification_loss = nn.CrossEntropyLoss()

        self.label_num = 1

    def forward(self, z, label):
        total_loss, accuracies = self.calc_supervised_loss(
            z, label
        )
        return total_loss, accuracies

    def calc_supervised_loss(self, z, labels):

        # forward pass
        z = nn.functional.adaptive_avg_pool2d(z, 1).squeeze()

        output = self.linear_classifier(z)

        loss = self.classification_loss(output, labels)

        accuracy = torch.zeros(1)
        # calculate accuracy
        if self.calc_accuracy:
            accuracy[0], = utils.accuracy(output.data, labels, topk=(1,))

        return loss, accuracy
