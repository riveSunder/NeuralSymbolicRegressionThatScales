import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import time
import torch.nn.functional as F
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning import Trainer, seed_everything
from typing import Tuple
from nesymres.benchmark import evaluate_model
from nesymres.architectures.model import Model
from nesymres.architectures.data import DataModule
from nesymres.dclasses import Params, DataModuleParams, FitParams, ArchitectureParams, NNEquation,BFGSParams
from nesymres.utils import load_metadata_hdf5
from functools import partial
import hydra

@hydra.main(config_name="fitfunc")
def main(cfg):
    model_path = hydra.utils.to_absolute_path(cfg.model_path)
    test_data = load_metadata_hdf5(hydra.utils.to_absolute_path(cfg.test_path))
    data_params = Params(datamodule_params_test=DataModuleParams(
                                total_variables=list(test_data.total_variables), 
                                total_coefficients=list(test_data.total_coefficients)),num_of_workers=0)

    architecture_params = ArchitectureParams()
    params_fit = FitParams(word2id=test_data.word2id, 
                            id2word=test_data.id2word, 
                            una_ops=test_data.una_ops, 
                            bin_ops=test_data.bin_ops, 
                            total_variables=list(test_data.total_variables),  
                            total_coefficients=list(test_data.total_coefficients),
                            rewrite_functions=list(test_data.rewrite_functions),
                            beam_size=cfg.fitparams.beam_size,
                            bfgs=BFGSParams(
                                add_coefficients_if_not_existing=cfg.fitparams.beamsearch.add_coefficients_if_not_existing)
                            )
    data = DataModule(
        None,
        None,
        hydra.utils.to_absolute_path(cfg.test_path),
        cfg=data_params
    )
    data.setup()
    model = Model.load_from_checkpoint(model_path, cfg=architecture_params)
    model.eval()
    model.cuda()
    fitfunc = partial(model.fitfunc,cfg_params=params_fit)
    for batch in data.test_dataloader():
        if not len(batch[0]):
            continue
        eq = NNEquation(batch[0][0],batch[1][0],batch[2][0])
        X,y = eq.numerical_values[None,:-1],eq.numerical_values[None,-1:] 
        if len(X.reshape(-1)) == 0:
            print("Skipping equation because no points are valid")
            continue
        print(f"Testing expressions {eq.expr}")
        output = fitfunc(X,y) 
        print(f"GT: {eq.expr}")
        print(f'Prediction: {output["best_bfgs_preds"]}')
        print("Evaluating")
        breakpoint()

if __name__ == "__main__":
    #os.environ["CUDA_VISIBLE_DEVICES"] = "0,2"  # ,1,2,4,5,6,7" Change Me
    #print(f"Starting a run with {config}")
    main()