# %%
"""
This file is used to analyse the hidden representation of the audio signal.
- It stores the hidden representation of the audio signal for each batch in a tensor.
- The tensor is then visualised using a scatter plot.
"""
import importlib
import random
import numpy as np
import torch
from GIM_encoder import GIM_Encoder
import helper_functions
from options import OPTIONS as opt
from options_anal_hidd_repr import LOG_PATH, EPOCH_VERSION, SAVE_ENCODINGS, GENERATE_VISUALISATIONS, AUTO_REGRESSOR_AFTER_MODULE, ENCODER_MODEL_DIR

from arg_parser import arg_parser
from data import get_dataloader


random.seed(0)

if(True):
    importlib.reload(helper_functions)
    from helper_functions import *

device = 'cuda' if torch.cuda.is_available() else 'cpu'


def visualise_2d_tensor(tensor, GIM_model_name, target_dir, name):
    nd_arr = tensor.to('cpu').numpy()
    length, nb_channels = nd_arr.shape

    nd_arr_flat = nd_arr.flatten()  # (length * nb_channels)
    s = nd_arr_flat / np.max(nd_arr_flat)
    xs = np.repeat(np.arange(0, length, 1), nb_channels)  # length
    ys = np.tile(np.arange(0, nb_channels, 1), length)  # channels

    fig, ax = plt.subplots(figsize=(20, 20))
    ax.scatter(ys, xs, s=100*(s**4), marker="s", c='orange', alpha=0.3)
    ax.set_aspect('equal')

    ax.set_xlabel('Channels')
    ax.set_ylabel('Signal length')
    ax.set_title(
        f'Hidden representation of the audio signal - {GIM_model_name} - {name}')

    # Show the plot
    plt.savefig(f"{target_dir}/{name}.png")
    # plt.show()


def _save_encodings(root_dir, data_type, encoder: GIM_Encoder, data_loader):
    assert data_type in ["train", "test"]

    # audio, filename, pronounced_syllable, full_word
    for idx, (batch_org_audio, filenames, pronounced_syllable, _) in enumerate(iter(data_loader)):
        batch_org_audio = batch_org_audio.to(device)
        batch_enc_audio_per_module = encoder(batch_org_audio)

        for module_idx, batch_enc_audio in enumerate(batch_enc_audio_per_module):
            # eg: 01GIM_L{layer_depth}/module=1/train/
            target_dir = f"{root_dir}/module={module_idx + 1}/{data_type}/"
            create_log_dir(target_dir)

            print(
                f"Batch {idx} - {batch_enc_audio.shape} - Mean: {torch.mean(batch_enc_audio)} - Std: {torch.std(batch_enc_audio)}")

            torch.save(batch_enc_audio,
                       f"{target_dir}/batch_encodings_{idx}.pt")
            torch.save(filenames, f"{target_dir}/batch_filenames_{idx}.pt")
            torch.save(pronounced_syllable,
                       f"{target_dir}/batch_pronounced_syllable_{idx}.pt")


def generate_and_save_encodings(encoder_model_path):
    encoder: GIM_Encoder = GIM_Encoder(opt, path=encoder_model_path)
    split = True
    train_loader, _, test_loader, _ = get_dataloader.get_de_boer_sounds_data_loaders(
        opt, shuffle=False, split_and_pad=split, train_noise=False)

    target_dir = f"{LOG_PATH}/hidden_repr/{'split' if split else 'full'}"

    _save_encodings(target_dir, "train", encoder, train_loader)
    _save_encodings(target_dir, "test", encoder, test_loader)


def _generate_visualisations(data_dir, GIM_model_name, target_dir):
    # iterate over files in train_dir
    for file in os.listdir(data_dir):  # Generated via copilot
        if file.endswith(".pt") and file.startswith("batch_encodings"):
            # load the file
            batch_encodings = torch.load(f"{data_dir}/{file}")
            batch_filenames = torch.load(
                f"{data_dir}/{file.replace('encodings', 'filenames')}")
            try:
                batch_pronounced_syllable_idices = torch.load(
                    f"{data_dir}/{file.replace('encodings', 'pronounced_syllable')}").numpy()
            except FileNotFoundError:
                batch_pronounced_syllable_idices = batch_filenames

            # iterate over the batch
            for idx, (enc, name, pronounced_syllable_idx) in enumerate(zip(batch_encodings, batch_filenames, batch_pronounced_syllable_idices)):
                name = name.split("_")[0]  # eg: babugu_1 -> babugu
                if name != pronounced_syllable_idx: # simple check to deal with split/full audio files
                    pronounced_syllable = translate_number_to_syllable(pronounced_syllable_idx)
                    name = f"{name} - {pronounced_syllable}"

                visualise_2d_tensor(enc, GIM_model_name, target_dir, f"{name}")

                if idx > 2:  # only do 2 visualisations per batch. So if 17 batches, 34 visualisations
                    break

# TODO: iterate over all pytorch files and generate t-sne plots


def generate_visualisations():
    # eg LOG_PATH = ./GIM\logs\audio_experiment_3_lr_noise\analyse_hidden_repr\
    for split in ['split', 'full']:
        if split == 'full':  # TODO: temporary disabled as full is not yet implemented
            continue

        saved_modules_dir = f"{LOG_PATH}/hidden_repr/{split}/"
        nb_modules = len(os.listdir(saved_modules_dir))  # module=1, ...

        for module_idx in range(1, nb_modules + 1):
            saved_files_dir = f"{LOG_PATH}/hidden_repr/{split}/module={module_idx}/"

            train_dir = f"{saved_files_dir}/train/"
            test_dir = f"{saved_files_dir}/test/"

            target_dir = f"{LOG_PATH}/hidden_repr_vis/{split}/module={module_idx}/"
            train_vis_dir = f"{target_dir}/train"
            test_vis_dir = f"{target_dir}/test/"
            create_log_dir(train_vis_dir)
            create_log_dir(test_vis_dir)

            _generate_visualisations(train_dir, "GIM", train_vis_dir)
            _generate_visualisations(test_dir, "GIM", test_vis_dir)


if __name__ == "__main__":
    assert SAVE_ENCODINGS or GENERATE_VISUALISATIONS

    torch.cuda.empty_cache()
    arg_parser.create_log_path(opt)
    opt['batch_size'] = 64 + 32
    opt['batch_size_multiGPU'] = opt['batch_size']
    opt['auto_regressor_after_module'] = AUTO_REGRESSOR_AFTER_MODULE

    logs = logger.Logger(opt)

    ENCODER_NAME = f"model_{EPOCH_VERSION}.ckpt"
    ENCODER_MODEL_PATH = f"{ENCODER_MODEL_DIR}/{ENCODER_NAME}"

    if SAVE_ENCODINGS:
        generate_and_save_encodings(ENCODER_MODEL_PATH)

    # todo: THEN GENERATE T-sne visualisations on larger samples.
    if GENERATE_VISUALISATIONS:
        generate_visualisations()

    # **** audio samples on syllables ****

    torch.cuda.empty_cache()
