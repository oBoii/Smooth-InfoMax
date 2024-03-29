import os
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.manifold import TSNE
import torch

from config_code.config_classes import OptionsConfig


def get_device(opt, input_tensor):
    if opt.device.type != "cpu":
        cur_device = input_tensor.get_device()
    else:
        cur_device = opt.device

    return cur_device


def accuracy(output, target, topk=(1,)):
    """Computes the accuracy over the k top predictions for the specified values of k"""
    with torch.no_grad():
        maxk = max(topk)
        batch_size = target.size(0)

        _, pred = output.topk(maxk, 1, True, True)
        pred = pred.t()

        # print(pred.min(), pred.max(), target.min(), target.max())

        correct = pred.eq(target.view(1, -1).expand_as(pred))

        correct = correct.contiguous()  # required for pytorch V1.7 view()

        res = []
        for k in topk:
            correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
            res.append(correct_k.mul_(100.0 / batch_size).item())
        return res


def scatter(opt, x, colors, label):
    """
    creates scatter plot for t-SNE visualization
    :param x: 2-D latent space as output by t-SNE
    :param colors: labels for each datapoint in x, used to assign different colors to them
    :param idx: used for naming the file, to be able to track progress throughout training
    """
    # We choose a color palette with seaborn.
    palette = np.array(sns.color_palette("hls", 10))

    # We create a scatter plot.
    plt.figure(figsize=(8, 8))
    ax = plt.subplot(aspect="equal")
    ax.scatter(x[:, 0], x[:, 1], lw=0, s=40,
               c=palette[colors.ravel().astype(np.int)])
    plt.xlim(-25, 25)
    plt.ylim(-25, 25)
    ax.axis("off")
    ax.axis("tight")

    # save fig
    plt.savefig(
        os.path.join(opt.log_path_latent, f"latent_space_{label}.png"), dpi=120
    )

    # save data to numpy csv (x, colors)
    np.savetxt(os.path.join(opt.log_path_latent,
                            f"latent_space_x_{label}.csv"), x, delimiter=",")

    np.savetxt(os.path.join(
        opt.log_path_latent, f"latent_space_colors_{label}.csv"), colors, delimiter=",")

    plt.close()


def fit_TSNE_and_plot(opt, feature_space, speaker_labels, label):
    projection = TSNE(init='random',
                      learning_rate=200.0,
                      perplexity=30).fit_transform(feature_space)

    scatter(opt, projection, speaker_labels, label)


def retrieve_existing_wandb_run_id(opt: OptionsConfig):
    # Save the run id to a file in the logs directory
    if os.path.exists(os.path.join(opt.log_path, 'wandb_run_id.txt')):
        with open(os.path.join(opt.log_path, 'wandb_run_id.txt'), 'r') as f:
            text = f.read()
            # first line is the run id, second line is the project name (second line is optional)
            run_id = text.split('\n')[0]
            project_name = text.split('\n')[1] if len(text.split('\n')) > 1 else None

    # if file doesn't exist, return None
    else:
        run_id = None
        project_name = None

    return run_id, project_name


def set_seed(seed):
    if seed == -1:
        return
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    np.random.seed(seed)
