import os
import tempfile

import pytest
import torch

from collie_recs.interactions import (ApproximateNegativeSamplingInteractionsDataLoader,
                                      HDF5InteractionsDataLoader,
                                      InteractionsDataLoader)
from collie_recs.model import (CollaborativeMetricLearningModel,
                               CollieMinimalTrainer,
                               CollieTrainer,
                               DeepFM,
                               HybridPretrainedModel,
                               MatrixFactorizationModel,
                               MLPMatrixFactorizationModel,
                               NeuralCollaborativeFiltering,
                               NonlinearMatrixFactorizationModel)
from collie_recs.utils import pandas_df_to_hdf5


@pytest.fixture(scope='session')
def implicit_model(train_val_implicit_data, gpu_count):
    train, val = train_val_implicit_data
    model = MatrixFactorizationModel(train=train,
                                     val=val,
                                     embedding_dim=10,
                                     lr=1e-1)
    model_trainer = CollieTrainer(model=model,
                                  gpus=gpu_count,
                                  max_epochs=10,
                                  deterministic=True,
                                  logger=False,
                                  checkpoint_callback=False)
    model_trainer.fit(model)
    model.eval()

    return model


@pytest.fixture(scope='session')
def implicit_model_no_lightning(train_val_implicit_data, gpu_count):
    train, val = train_val_implicit_data
    model = MatrixFactorizationModel(train=train,
                                     val=val,
                                     embedding_dim=10,
                                     lr=1e-1)
    model_trainer = CollieMinimalTrainer(model=model,
                                         gpus=gpu_count,
                                         max_epochs=10,
                                         deterministic=True,
                                         logger=False,
                                         early_stopping_patience=False)
    model_trainer.fit(model)
    model.freeze()

    return model


@pytest.fixture(scope='session')
def untrained_implicit_model(train_val_implicit_data):
    train, val = train_val_implicit_data
    model = MatrixFactorizationModel(train=train, val=val)

    return model


@pytest.fixture(scope='session')
def untrained_implicit_model_no_val_data(train_val_implicit_data):
    train, _ = train_val_implicit_data
    model = MatrixFactorizationModel(train=train, val=None)

    return model


@pytest.fixture(params=['mf_hdf5',
                        'mf_with_y_range',
                        'collaborative_metric_learning',
                        'sparse_collaborative_metric_learning',
                        'mlp_mf',
                        'mlp_mf_with_y_range',
                        'sparse_mf',
                        'mf_no_val',
                        'mf_non_approximate',
                        'mf_approximate',
                        'nonlinear_mf',
                        'nonlinear_mf_with_y_range',
                        'neucf',
                        'neucf_sigmoid',
                        'neucf_relu',
                        'neucf_leaky_rulu',
                        'neucf_custom',
                        'deep_fm',
                        'deep_fm_sigmoid',
                        'deep_fm_relu',
                        'deep_fm_leaky_rulu',
                        'deep_fm_custom',
                        'hybrid_pretrained',
                        'hybrid_pretrained_metadata_layers'])
def models_trained_for_one_step(request,
                                train_val_implicit_sample_data,
                                movielens_metadata_df,
                                movielens_implicit_df,
                                train_val_implicit_pandas_data,
                                gpu_count):
    train, val = train_val_implicit_sample_data

    if request.param == 'mf_hdf5':
        # create, fit, and return the model all at once so we can close the HDF5 file
        train_pandas_df, val_pandas_df = train_val_implicit_pandas_data

        with tempfile.TemporaryDirectory() as temp_dir:
            pandas_df_to_hdf5(df=train_pandas_df,
                              out_path=os.path.join(temp_dir, 'train.h5'),
                              key='interactions')
            pandas_df_to_hdf5(df=val_pandas_df,
                              out_path=os.path.join(temp_dir, 'val.h5'),
                              key='interactions')

            train_loader = HDF5InteractionsDataLoader(hdf5_path=os.path.join(temp_dir, 'train.h5'),
                                                      user_col='user_id',
                                                      item_col='item_id',
                                                      num_users=train.num_users,
                                                      num_items=train.num_items,
                                                      batch_size=1024,
                                                      shuffle=True)
            val_loader = HDF5InteractionsDataLoader(hdf5_path=os.path.join(temp_dir, 'val.h5'),
                                                    user_col='user_id',
                                                    item_col='item_id',
                                                    num_users=val.num_users,
                                                    num_items=val.num_items,
                                                    batch_size=1024,
                                                    shuffle=False)

            model = MatrixFactorizationModel(train=train_loader,
                                             val=val_loader,
                                             embedding_dim=15,
                                             dropout_p=0.1,
                                             lr=1e-1,
                                             bias_lr=1e-2,
                                             optimizer='adam',
                                             bias_optimizer='sgd',
                                             weight_decay=1e-7,
                                             loss='bpr',
                                             sparse=False)

            model_trainer = CollieTrainer(model=model,
                                          gpus=gpu_count,
                                          max_steps=1,
                                          deterministic=True,
                                          logger=False,
                                          checkpoint_callback=False)

            model_trainer.fit(model)
            model.eval()

            return model

    elif request.param == 'sparse_mf':
        model = MatrixFactorizationModel(train=train,
                                         val=val,
                                         embedding_dim=15,
                                         dropout_p=0.1,
                                         lr=1e-1,
                                         bias_lr=1e-2,
                                         optimizer='sparse_adam',
                                         bias_optimizer='sgd',
                                         weight_decay=0,
                                         loss='hinge',
                                         sparse=True)
    elif request.param == 'mf_no_val':
        model = MatrixFactorizationModel(train=train, val=None)
    elif request.param == 'mf_non_approximate' or request.param == 'mf_approximate':
        if request.param == 'mf_non_approximate':
            train_loader = InteractionsDataLoader(interactions=train, batch_size=1024, shuffle=True)
            val_loader = InteractionsDataLoader(interactions=val, batch_size=1024, shuffle=False)
        else:
            train_loader = ApproximateNegativeSamplingInteractionsDataLoader(interactions=train,
                                                                             batch_size=1024,
                                                                             shuffle=True)
            val_loader = ApproximateNegativeSamplingInteractionsDataLoader(interactions=val,
                                                                           batch_size=1024,
                                                                           shuffle=False)

        model = MatrixFactorizationModel(train=train_loader,
                                         val=val_loader,
                                         embedding_dim=15,
                                         dropout_p=0.1,
                                         lr=1e-1,
                                         bias_lr=1e-2,
                                         optimizer='adam',
                                         bias_optimizer='sgd',
                                         weight_decay=1e-7,
                                         loss='bpr',
                                         sparse=False)
    elif request.param == 'mf_with_y_range':
        model = MatrixFactorizationModel(train=train,
                                         val=val,
                                         y_range=(0, 4))
    elif request.param == 'collaborative_metric_learning':
        model = CollaborativeMetricLearningModel(train=train,
                                                 val=val,
                                                 embedding_dim=15,
                                                 lr=1e-1,
                                                 optimizer='adam',
                                                 loss='hinge')
    elif request.param == 'sparse_collaborative_metric_learning':
        model = CollaborativeMetricLearningModel(train=train,
                                                 val=val,
                                                 embedding_dim=15,
                                                 lr=1e-1,
                                                 optimizer='sparse_adam',
                                                 loss='hinge',
                                                 sparse=True)
    elif request.param == 'mlp_mf':
        model = MLPMatrixFactorizationModel(train=train,
                                            val=val,
                                            embedding_dim=15,
                                            num_layers=3,
                                            dropout_p=0.1,
                                            lr=1e-1,
                                            bias_lr=1e-2,
                                            optimizer='adam',
                                            bias_optimizer='sgd',
                                            weight_decay=1e-7,
                                            loss='hinge')
    elif request.param == 'mlp_mf_with_y_range':
        model = MLPMatrixFactorizationModel(train=train,
                                            val=val,
                                            y_range=(0, 2))
    elif request.param == 'nonlinear_mf':
        model = NonlinearMatrixFactorizationModel(train=train,
                                                  val=val,
                                                  user_embedding_dim=15,
                                                  item_embedding_dim=15,
                                                  user_dense_layers_dims=[15, 10],
                                                  item_dense_layers_dims=[15, 10],
                                                  embedding_dropout_p=0.05,
                                                  dense_dropout_p=0.1,
                                                  lr=1e-1,
                                                  bias_lr=1e-2,
                                                  optimizer='adam',
                                                  bias_optimizer='sgd',
                                                  weight_decay=1e-7,
                                                  loss='bpr')
    elif request.param == 'nonlinear_mf_with_y_range':
        model = NonlinearMatrixFactorizationModel(train=train,
                                                  val=val,
                                                  y_range=(0, 4))
    elif request.param == 'neucf':
        model = NeuralCollaborativeFiltering(train=train,
                                             val=val,
                                             embedding_dim=10,
                                             num_layers=1,
                                             dropout_p=0.1,
                                             lr=1e-3,
                                             weight_decay=0.,
                                             optimizer='adam',
                                             loss='adaptive')
    elif request.param == 'neucf_sigmoid':
        model = NeuralCollaborativeFiltering(train=train,
                                             val=val,
                                             final_layer='sigmoid')
    elif request.param == 'neucf_relu':
        model = NeuralCollaborativeFiltering(train=train,
                                             val=val,
                                             final_layer='relu')
    elif request.param == 'neucf_leaky_rulu':
        model = NeuralCollaborativeFiltering(train=train,
                                             val=val,
                                             final_layer='leaky_relu')
    elif request.param == 'neucf_custom':
        model = NeuralCollaborativeFiltering(train=train,
                                             val=val,
                                             final_layer=torch.tanh)
    elif request.param == 'deep_fm':
        model = DeepFM(train=train,
                       val=val,
                       embedding_dim=10,
                       num_layers=1,
                       dropout_p=0.1,
                       lr=1e-3,
                       weight_decay=0.,
                       optimizer='adam',
                       bias_optimizer=None,
                       loss='hinge')
    elif request.param == 'deep_fm_sigmoid':
        model = DeepFM(train=train,
                       val=val,
                       final_layer='sigmoid')
    elif request.param == 'deep_fm_relu':
        model = DeepFM(train=train,
                       val=val,
                       final_layer='relu')
    elif request.param == 'deep_fm_leaky_rulu':
        model = DeepFM(train=train,
                       val=val,
                       final_layer='leaky_relu')
    elif request.param == 'deep_fm_custom':
        model = DeepFM(train=train,
                       val=val,
                       final_layer=torch.tanh)
    elif (
        request.param == 'hybrid_pretrained' or request.param == 'hybrid_pretrained_metadata_layers'
    ):
        implicit_model = MatrixFactorizationModel(train=train,
                                                  val=val,
                                                  embedding_dim=10,
                                                  lr=1e-1,
                                                  optimizer='adam')
        implicit_model_trainer = CollieTrainer(model=implicit_model,
                                               gpus=gpu_count,
                                               max_steps=1,
                                               deterministic=True,
                                               logger=False,
                                               checkpoint_callback=False)
        implicit_model_trainer.fit(implicit_model)
        implicit_model.eval()

        genres = (
            torch.tensor(movielens_metadata_df[
                [c for c in movielens_metadata_df.columns if 'genre' in c]
            ].values)
            .topk(1)
            .indices
            .view(-1)
        )

        if request.param == 'hybrid_pretrained_metadata_layers':
            metadata_layers_dims = [16, 12]
        else:
            metadata_layers_dims = None

        model_frozen = HybridPretrainedModel(train=train,
                                             val=val,
                                             item_metadata=movielens_metadata_df,
                                             trained_model=implicit_model,
                                             metadata_layers_dims=metadata_layers_dims,
                                             freeze_embeddings=True,
                                             dropout_p=0.15,
                                             loss='warp',
                                             lr=.01,
                                             optimizer=torch.optim.Adam,
                                             metadata_for_loss={'genre': genres},
                                             metadata_for_loss_weights={'genre': .4},
                                             weight_decay=0.0)
        model_frozen_trainer = CollieTrainer(model=model_frozen,
                                             gpus=gpu_count,
                                             max_steps=1,
                                             deterministic=True,
                                             logger=False,
                                             checkpoint_callback=False)
        model_frozen_trainer.fit(model_frozen)

        model = HybridPretrainedModel(train=train,
                                      val=val,
                                      item_metadata=movielens_metadata_df,
                                      trained_model=implicit_model,
                                      metadata_layers_dims=metadata_layers_dims,
                                      freeze_embeddings=False,
                                      dropout_p=0.15,
                                      loss='bpr',
                                      lr=1e-4,
                                      optimizer=torch.optim.Adam,
                                      metadata_for_loss={'genre': genres},
                                      metadata_for_loss_weights={'genre': .4},
                                      weight_decay=0.0)
        model.load_from_hybrid_model(model_frozen)

    model_trainer = CollieTrainer(model=model,
                                  gpus=gpu_count,
                                  max_steps=1,
                                  deterministic=True,
                                  logger=False,
                                  checkpoint_callback=False)

    if request.param == 'mf_no_val':
        with pytest.warns(UserWarning):
            model_trainer.fit(model)
    else:
        model_trainer.fit(model)

    model.eval()

    return model
