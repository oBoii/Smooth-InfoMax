from optparse import OptionParser
import time
import os
import torch
import numpy as np

from config_code.config_classes import OptionsConfig
from vision.arg_parser import reload_args, GIM_args, general_args


def parse_args():
    # load parameters and options
    parser = OptionParser()

    parser = general_args.parse_general_args(parser)
    parser = GIM_args.parse_GIM_args(parser)
    parser = reload_args.parser_reload_args(parser)

    (opt, _) = parser.parse_args()

    opt.time = time.ctime()

    # Device configuration
    opt.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    return opt


def create_log_path(opt: OptionsConfig, add_path_var=""):
    assert opt.save_dir != "", "save_dir must not be empty"
    assert opt.log_path != "", "log_path must not be empty"

    # remove ":" from name as windows can't handle it
    # opt.log_path = opt.log_path.replace(":", "_")

    if add_path_var is not None:  # overwrite the log_path and append the add_path_var
        opt.log_path = os.path.join(opt.log_path, add_path_var)

    if not os.path.exists(opt.log_path):
        os.makedirs(opt.log_path)

    if not os.path.exists(opt.log_path_latent):
        os.makedirs(opt.log_path_latent)

