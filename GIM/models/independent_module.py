from typing import List
from torch import Tensor
import torch
import torch.nn as nn

# https://github.com/AntixK/PyTorch-VAE/blob/master/models/vanilla_vae.py,
# https://medium.com/dataseries/convolutional-autoencoder-in-pytorch-on-mnist-dataset-d65145c132ac

from models import (
    cnn_encoder,
    loss_InfoNCE,
    autoregressor
)


class IndependentModule(nn.Module):
    def __init__(
        self, opt,
        enc_kernel_sizes, enc_strides, enc_padding, nb_channels_cnn, nb_channels_regress, enc_input=1, calc_accuracy=False,
    ):
        super(IndependentModule, self).__init__()

        self.opt = opt
        self.calc_accuracy = calc_accuracy
        self.nb_channels_cnn = nb_channels_cnn
        self.nb_channels_regressor = nb_channels_regress

        # encoder, out: B x L x C = (22, 55, 512)
        self.encoder = cnn_encoder.CNNEncoder(
            inp_nb_channels=enc_input,
            out_nb_channels=nb_channels_cnn,
            kernel_sizes=enc_kernel_sizes,
            strides=enc_strides,
            padding=enc_padding,
        )

        if self.opt["auto_regressor_after_module"]:
            self.autoregressor = autoregressor.Autoregressor(
                opt=opt, input_size=self.nb_channels_cnn, hidden_dim=self.nb_channels_regressor
            )

            # hidden dim of the autoregressor is the input dim of the loss
            self.loss = loss_InfoNCE.InfoNCE_Loss(
                opt, hidden_dim=self.nb_channels_regressor, enc_hidden=self.nb_channels_cnn, calc_accuracy=calc_accuracy)
        else:
            # hidden dim of the encoder is the input dim of the loss
            self.loss = loss_InfoNCE.InfoNCE_Loss(
                opt, hidden_dim=self.nb_channels_cnn, enc_hidden=self.nb_channels_cnn, calc_accuracy=calc_accuracy)

    def get_latents(self, x):  # Latents now return distribution parameters
        """
        Calculate the latent representation of the input (using both the encoder and the autoregressive model)
        :param x: batch with sampled audios (dimensions: B x C x L)
        :return: c - latent representation of the input (either the output of the autoregressor,
                if use_autoregressor=True, or the output of the encoder otherwise)
                z - latent representation generated by the encoder (or x if self.use_encoder=False)
                both of dimensions: B x L x C
        """
        # encoder in and out: B x C x L, permute to be  B x L x C
        mu, log_var = self.encoder(x)  # (b, 512, 55), (b, 512, 55)

        mu = mu.permute(0, 2, 1)  # (b, 55, 512)
        log_var = log_var.permute(0, 2, 1)

        # if self.opt["auto_regressor_after_module"]:
        #     c = self.autoregressor(z)
        #     return c, z
        # else:
        # return z, z
        return [(mu, log_var), (mu, log_var)]

    # def forward(self, input: Tensor) -> List[Tensor]:
    #     mu, log_var = self.encode(input)
    #     z = self.reparameterize(mu, log_var) # (batch, latent_dim, 3, 3)

    #     x_hat = self.decode(z) # not used
    #     return [x_hat, input, mu, log_var]

    def reparameterize(self, mu: Tensor, logvar: Tensor) -> Tensor:
        """
        Reparameterization trick to sample from N(mu, var) from
        N(0,1).
        :param mu: (Tensor) Mean of the latent Gaussian [B x D]
        :param logvar: (Tensor) Standard deviation of the latent Gaussian [B x D]
        :return: (Tensor) [B x D]
        """
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return eps * std + mu


    # FROM VAE
    def VAE_LOSS_FROM_OTHER_PROJECT(self, recons, input, mu, log_var, kld_weight=0.0025) -> List[Tensor]:
        """
        Computes the VAE loss function.
        KL(N(\mu, \sigma), N(0, 1)) = \log \frac{1}{\sigma} + \frac{\sigma^2 + \mu^2}{2} - \frac{1}{2}
        :param args:
        :param kwargs:
        :return:
        """

        # Account for the minibatch samples from the dataset
        recons_loss = F.mse_loss(recons, input)

        kld_loss = torch.mean(-0.5 * torch.sum(1 + log_var - mu ** 2 - log_var.exp(), dim=1), dim=0)

        loss = recons_loss + kld_weight * kld_loss # shape: (3, 3)
        loss = loss.mean() # shape: (1)
        return [loss, recons_loss.detach(), -kld_loss.detach()]

    def forward(self, x):
        """
        combines all the operations necessary for calculating the loss and accuracy of the network given the input
        :param x: batch with sampled audios (dimensions: B x C x L)
        :return: total_loss - average loss over all samples, timesteps and prediction steps in the batch
                accuracies - average accuracies over all samples, timesteps and predictions steps in the batch
                c - latent representation of the input (either the output of the autoregressor,
                if use_autoregressor=True, or the output of the encoder otherwise)
        """

        # B x L x C = Batch size x #channels x length
        (c_mu, c_log_var), (z_mu, z_log_var) = self.get_latents(x)  # B x L x C

        # !! all of a sudden the c that was equal to z is now a different value.
        # TODO: THINK ABOUT THIS, it could have implications for the loss function if not done correctly

        c = self.reparameterize(c_mu, c_log_var) # (B, L, 512)
        z = self.reparameterize(z_mu, z_log_var)

        log_var = c_log_var
        mu = c_mu

        kld_loss = torch.mean(-0.5 * torch.sum(1 + log_var - mu ** 2 - log_var.exp(), dim=1), dim=0)
        kld_loss = kld_loss.mean() # shape: (1)

        # reconstruction loss
        total_loss, accuracies = self.loss.get_loss(z, c)
        
        kld_weight=0.0025

        total_loss = total_loss + kld_weight * kld_loss

        # KL-divergence loss
        # if self.opt["use_kl_divergence"]:
        # kl_loss = self.loss.get_kl_loss(z)

        # for multi-GPU training
        total_loss = total_loss.unsqueeze(0)
        accuracies = accuracies.unsqueeze(0)

        return total_loss, accuracies, z
