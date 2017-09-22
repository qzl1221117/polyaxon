# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import tensorflow as tf
import polyaxon as plx

from tensorflow.contrib.keras.python.keras.backend import set_learning_phase

from polyaxon_schemas.optimizers import AdamConfig
from polyaxon_schemas.losses import SigmoidCrossEntropyConfig
from polyaxon_schemas.metrics import StreamingAccuracyConfig


def graph_fn(mode, features):
    set_learning_phase(plx.Modes.is_train(mode))

    x = plx.layers.Conv2D(filters=32, kernel_size=5)(features['image'])
    x = plx.layers.MaxPooling2D(pool_size=2)(x)
    x = plx.layers.Conv2D(filters=64, kernel_size=5)(x)
    x = plx.layers.MaxPooling2D(pool_size=2)(x)
    x = plx.layers.Flatten()(x)
    x = plx.layers.Dense(units=10)(x)
    return x


def model_fn(features, labels, params, mode, config):
    model = plx.models.Classifier(
        mode=mode,
        graph_fn=graph_fn,
        loss_config=SigmoidCrossEntropyConfig(),
        optimizer_config=AdamConfig(
            learning_rate=0.007, decay_type='exponential_decay', decay_rate=0.1),
        eval_metrics_config=[StreamingAccuracyConfig()],
        summaries='all',
        one_hot_encode=True,
        n_classes=10)
    return model(features=features, labels=labels, params=params, config=config)


def experiment_fn(output_dir):
    """Creates an experiment using Lenet network.

    Links:
        * http://yann.lecun.com/exdb/publis/pdf/lecun-01a.pdf
    """
    dataset_dir = '../data/mnist'
    plx.datasets.mnist.prepare(dataset_dir)
    train_input_fn, eval_input_fn = plx.datasets.mnist.create_input_fn(dataset_dir)

    experiment = plx.experiments.Experiment(
        estimator=plx.estimators.Estimator(model_fn=model_fn, model_dir=output_dir),
        train_input_fn=train_input_fn,
        eval_input_fn=eval_input_fn,
        train_steps=10000,
        eval_steps=10,
        eval_every_n_steps=5)

    return experiment


def main(*args):
    plx.experiments.run_experiment(experiment_fn=experiment_fn,
                                   output_dir="/tmp/polyaxon_logs/lenet",
                                   schedule='continuous_train_and_evaluate')


if __name__ == "__main__":
    tf.logging.set_verbosity(tf.logging.INFO)
    tf.app.run()
