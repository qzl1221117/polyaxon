# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import logging

from django.conf import settings

from polyaxon_k8s.constants import ExperimentLifeCycle
from polyaxon_schemas.utils import TaskType
from polyaxon_spawner.spawner import K8SExperimentSpawner

from api.celery_api import app as celery_app
from api.settings import CeleryTasks
from experiments.models import ExperimentJob
from libs.redis_db import RedisExperimentStatus

logger = logging.getLogger('polyaxon.tasks.experiments')


@celery_app.task(name=CeleryTasks.EXPERIMENTS_START)
def start_experiment(experiment_id):
    from experiments.models import Experiment, ExperimentStatus

    try:
        experiment = Experiment.objects.get(id=experiment_id)
    except Experiment.DoesNotExist:
        logger.info('Experiment id `{}` does not exist'.format(experiment_id))
        return

    # Update experiment status to show that its started
    ExperimentStatus.objects.create(experiment=experiment, status=ExperimentLifeCycle.SCHEDULED)

    # Use spawner to start the experiment
    spawner = K8SExperimentSpawner(project_id=experiment.project.id,
                                   spec_id=experiment.spec.id if experiment.spec else '',
                                   experiment_id=experiment.id,
                                   specification=experiment.config,
                                   k8s_config=settings.K8S_CONFIG)
    resp = spawner.start_experiment()

    # Get the number of jobs this experiment started
    ExperimentJob.objects.create(experiment=experiment, definition=resp[TaskType.MASTER])
    for worker in resp[TaskType.WORKER]:
        ExperimentJob.objects.create(experiment=experiment, definition=worker)
        for ps in resp[TaskType.PS]:
            ExperimentJob.objects.create(experiment=experiment, definition=ps)

    # Add the experiment to the list of experiments to monitor
    RedisExperimentStatus.monitor(experiment_id)
