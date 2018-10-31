#!/usr/bin/env python3
import logging

import click
import docker
from titus_isolate.api.status import app, set_wm
from titus_isolate.docker.create_event_handler import CreateEventHandler
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.docker.free_event_handler import FreeEventHandler
from titus_isolate.docker.utils import get_current_workloads
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.utils import get_cpu
from titus_isolate.utils import config_logs

log = logging.getLogger()


@click.command()
@click.option('--package-count', help="The number of packages in the CPU")
@click.option('--cores-per-package', help="The number of cores per package")
@click.option('--threads-per-core', default=2, help="The number of threads per core (default: 2)")
@click.option('--admin-port', default=5000, help="The port for the HTTP server to listen on (default: 5000)")
def main(package_count, cores_per_package, threads_per_core, admin_port):
    log.info("Modeling the CPU...")
    cpu = get_cpu(int(package_count), int(cores_per_package), int(threads_per_core))

    # Setup the workload manager
    log.info("Setting up the workload manager...")
    docker_client = docker.from_env()
    workload_manager = WorkloadManager(cpu, docker_client)
    set_wm(workload_manager)

    # Setup the event handlers
    log.info("Setting up the Docker event handlers...")
    event_logger = EventLogger()
    create_event_handler = CreateEventHandler(workload_manager)
    free_event_handler = FreeEventHandler(workload_manager)
    event_handlers = [event_logger, create_event_handler, free_event_handler]

    # Start event processing
    log.info("Starting Docker event handling...")
    EventManager(docker_client.events(), event_handlers)

    # Initialize currently running containers as workloads
    log.info("Isolating currently running workloads...")
    workload_manager.add_workloads(get_current_workloads(docker_client))

    log.info("Startup complete, waiting for events...")

    # Starting the HTTP server blocks exit forever
    app.run(host="0.0.0.0", debug=False, port=admin_port)


if __name__ == "__main__":
    config_logs()
    main()
