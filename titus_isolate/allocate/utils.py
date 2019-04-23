import datetime

import boto3 as boto3

from titus_isolate import log
from titus_isolate.config.constants import MODEL_BUCKET_FORMAT_STR, MODEL_BUCKET_PREFIX, \
    DEFAULT_MODEL_BUCKET_PREFIX, MODEL_BUCKET_LEAF, DEFAULT_MODEL_BUCKET_LEAF, MODEL_PREFIX_FORMAT_STR
from titus_isolate.config.utils import get_required_property
from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.workload import Workload
from titus_isolate.utils import get_config_manager


def parse_cpu(cpu_dict: dict) -> Cpu:
    packages = []
    for p in cpu_dict["packages"]:
        cores = []
        for c in p["cores"]:
            threads = []
            for t in c["threads"]:
                thread = Thread(t["id"])
                for w_id in t["workload_id"]:
                    thread.claim(w_id)
                threads.append(thread)
            cores.append(Core(c["id"], threads))
        packages.append(Package(p["id"], cores))

    return Cpu(packages)


def parse_workloads(workloads: dict) -> list:
    __workloads = {}
    for w_id, workload in workloads.items():
        __workloads[w_id] = parse_workload(workload)
    return __workloads


def parse_workload(workload_dict: dict) -> Workload:

    workload = Workload(
        identifier=workload_dict['id'],
        thread_count=workload_dict['thread_count'],
        mem=workload_dict['mem'],
        disk=workload_dict['disk'],
        network=workload_dict['network'],
        app_name=workload_dict['app_name'],
        owner_email=workload_dict['owner_email'],
        image=workload_dict['image'],
        command=workload_dict['command'],
        entrypoint=workload_dict['entrypoint'],
        job_type=workload_dict['job_type'],
        workload_type=workload_dict['type'])

    # Input example:  "2019-03-23 18:03:50.668041"
    creation_time = datetime.datetime.strptime(workload_dict["creation_time"], '%Y-%m-%d %H:%M:%S.%f')
    workload.set_creation_time(creation_time)
    return workload


def parse_cpu_usage(cpu_usage: dict) -> dict:
    parsed_cpu_usage = {}
    for k, v in cpu_usage.items():
        parsed_cpu_usage[k] = [float(val) for val in v]

    return parsed_cpu_usage

def get_cpu_model_bucket_name():
    format_str = get_required_property(MODEL_BUCKET_FORMAT_STR)
    if format_str is None:
        return None

    config_manager = get_config_manager()
    region = config_manager.get_region()
    env = config_manager.get_environment()

    return format_str.format(region, env)


def get_cpu_model_prefix_name():
    config_manager = get_config_manager()
    prefix = config_manager.get_str(MODEL_BUCKET_PREFIX, DEFAULT_MODEL_BUCKET_PREFIX)
    leaf = config_manager.get_str(MODEL_BUCKET_LEAF, DEFAULT_MODEL_BUCKET_LEAF)

    format_str = get_config_manager().get_str(MODEL_PREFIX_FORMAT_STR)
    if format_str is None:
        return None

    return format_str.format(prefix, leaf)


def get_cpu_models():
    bucket_name = get_cpu_model_bucket_name()
    if bucket_name is None:
        log.error("Failed to get cpu model bucket name.")
        return None

    prefix_name = get_cpu_model_prefix_name()
    if prefix_name is None:
        log.error("Failed to get cpu model prefix name.")
        return None

    log.info("Getting model metadata from bucket: '{}', prefix: '{}'".format(bucket_name, prefix_name))

    s3_client = boto3.client('s3')
    paginator = s3_client.get_paginator('list_objects')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix_name)

    CONTENTS = 'Contents'
    models = []
    for page in pages:
        if CONTENTS in page:
            for entry in page[CONTENTS]:
                models.append(entry)

    return models


def get_latest_cpu_model():
    models = get_cpu_models()
    if models is None or len(models) == 0:
        return None

    models = sorted(models, key=lambda e: e['LastModified'], reverse=True)
    log.debug("sorted models: {}".format(models))
    return models[0]


def get_cpu_model_file_path():
    return '/var/lib/titus-isolate-cpu-model.bin'


def download_latest_cpu_model(path=get_cpu_model_file_path()):
    log.info("Downloading latest cpu prediction model.")
    latest_model = get_latest_cpu_model()
    if latest_model is None:
        log.error("Failed to download model because no model found.")
        return

    bucket_name = get_cpu_model_bucket_name()
    key = latest_model['Key']
    s3_client = boto3.client('s3')
    s3_client.download_file(bucket_name, key, path)
    log.info("Downloaded latest cpu prediction model: '{}/{}' to: '{}'".format(bucket_name, key, path))
