from config_code.config_classes import EncoderConfig, DataSetConfig, Dataset, OptionsConfig, Loss, ClassifierConfig, \
    DecoderConfig, DecoderLoss
from config_code.architecture_config import ArchitectureConfig, ModuleConfig, DecoderArchitectureConfig
import torch


class CPCSetup:
    def __init__(self):
        # Original dimensions given in CPC paper (Oord et al.).
        kernel_sizes = [10, 8, 4, 4, 4]
        strides = [5, 4, 2, 2, 2]
        padding = [2, 2, 2, 2, 1]
        cnn_hidden_dim = 512
        regressor_hidden_dim = 256
        cpc = True  # Contrastive Predictive Coding

        modules = [
            ModuleConfig(
                max_pool_k_size=None,
                max_pool_stride=None,
                kernel_sizes=kernel_sizes,
                strides=strides,
                padding=padding,
                cnn_hidden_dim=cnn_hidden_dim,
                is_autoregressor=True,
                regressor_hidden_dim=regressor_hidden_dim,
                prediction_step=12,
                predict_distributions=False,
                # !!
                is_cnn_and_autoregressor=cpc
            )]

        ARCHITECTURE = ArchitectureConfig(modules=modules, is_cpc=cpc)

        DATASET = DataSetConfig(
            dataset=Dataset.LIBRISPEECH,
            split_in_syllables=False,
            batch_size=8,
            limit_train_batches=1.0,
            limit_validation_batches=1.0,
        )

        self.ENCODER_CONFIG = EncoderConfig(
            start_epoch=0,
            num_epochs=1_000,
            negative_samples=10,
            subsample=True,
            architecture=ARCHITECTURE,
            kld_weight=0,
            learning_rate=2e-4,  # = 0.0002
            decay_rate=1,
            train_w_noise=False,
            dataset=DATASET,
        )

        self.CLASSIFIER_CONFIG_PHONES = ClassifierConfig(
            num_epochs=20,
            learning_rate=1e-4,  # = 0.0001
            # Deep copy of the dataset, to avoid changing the original dataset
            dataset=DATASET.__copy__(),
            # For loading a specific model from a specific epoch, to use by the classifier
            encoder_num=self.ENCODER_CONFIG.num_epochs - 1
        )
        self.CLASSIFIER_CONFIG_PHONES.dataset.batch_size = 8

        self.CLASSIFIER_CONFIG_SPEAKERS = ClassifierConfig(
            num_epochs=50,
            learning_rate=1e-3,  # = 0.001
            dataset=DATASET.__copy__(),
            # For loading a specific model from a specific epoch, to use by the classifier
            encoder_num=self.ENCODER_CONFIG.num_epochs - 1
        )
        self.CLASSIFIER_CONFIG_SPEAKERS.dataset.batch_size = 64

        self.CLASSIFIER_CONFIG_SYLLABLES = ClassifierConfig(
            num_epochs=20,
            learning_rate=1e-3,  # = 0.001
            dataset=DataSetConfig(
                dataset=Dataset.DE_BOER_RESHUFFLED,
                split_in_syllables=True,
                batch_size=128,
                limit_train_batches=1.0,
                limit_validation_batches=1.0,
            ),
            # For loading a specific model from a specific epoch, to use by the classifier
            encoder_num=self.ENCODER_CONFIG.num_epochs - 1
        )

        self.DECODER_CONFIG = DecoderConfig(
            num_epochs=200,
            learning_rate=2e-4,
            dataset=DataSetConfig(
                dataset=Dataset.DE_BOER_RESHUFFLED,
                split_in_syllables=False,
                batch_size=64,
                limit_train_batches=1.0,
                limit_validation_batches=1.0,
            ),
            encoder_num=self.ENCODER_CONFIG.num_epochs - 1,
            architecture=DecoderArchitectureConfig(
                # decoder is trained on second to last module (skip the autoregressor)
                kernel_sizes=kernel_sizes[::-1],
                strides=strides[::-1],
                paddings=padding[::-1],
                output_paddings=[1, 0, 1, 3, 4],
                input_dim=cnn_hidden_dim,
                hidden_dim=cnn_hidden_dim,
                output_dim=1
            ),
            decoder_loss=DecoderLoss.MSE
        )

    def get_options(self, experiment_name) -> OptionsConfig:
        options = OptionsConfig(
            seed=2,
            validate=True,
            loss=Loss.INFO_NCE,
            experiment='audio',
            save_dir=experiment_name,
            log_every_x_epochs=1,
            encoder_config=self.ENCODER_CONFIG,
            phones_classifier_config=self.CLASSIFIER_CONFIG_PHONES,
            speakers_classifier_config=self.CLASSIFIER_CONFIG_SPEAKERS,
            syllables_classifier_config=self.CLASSIFIER_CONFIG_SYLLABLES,
            decoder_config=self.DECODER_CONFIG,
        )

        return options