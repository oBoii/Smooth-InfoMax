import torch.nn as nn
import torch

from config_code.config_classes import OptionsConfig
from data import get_dataloader
from models import loss
from utils import utils


class Syllables_Loss(loss.Loss):
    def __init__(self, opt: OptionsConfig, hidden_dim, calc_accuracy):
        super(Syllables_Loss, self).__init__()

        self.opt = opt
        self.hidden_dim = hidden_dim
        self.calc_accuracy = calc_accuracy

        num_syllables = 9

        # Adjust the output dimension to match the number of syllables
        self.linear_classifier = nn.Sequential(nn.Linear(self.hidden_dim, num_syllables)).to(
            opt.device
        )

        self.label_num = 1
        self.syllables_loss = nn.CrossEntropyLoss()

    def get_loss(self, x, z, c, targets):
        total_loss, accuracies = self.calc_supervised_syllables_loss(
            c, targets,
        )
        return total_loss, accuracies

    def calc_supervised_syllables_loss(self, c, targets):
        # forward pass
        c = c.permute(0, 2, 1)

        pooled_c = nn.functional.adaptive_avg_pool1d(c, self.label_num)
        pooled_c = pooled_c.permute(0, 2, 1).reshape(-1, self.hidden_dim)

        syllables_out = self.linear_classifier(pooled_c)

        assert syllables_out.shape[0] == targets.shape[0]

        loss = self.syllables_loss(syllables_out, targets)

        accuracy = torch.zeros(1)
        # calculate accuracy
        if self.calc_accuracy:
            _, predicted = torch.max(syllables_out.data, 1)
            total = targets.size(0)
            correct = (predicted == targets).sum().item()
            accuracy[0] = correct / total

        return loss, accuracy