import logging
import signal
import sys
from threading import Event

import click
import docker
from titus_isolate.docker.create_event_handler import CreateEventHandler
from titus_isolate.docker.event_logger import EventLogger
from titus_isolate.docker.event_manager import EventManager
from titus_isolate.docker.free_event_handler import FreeEventHandler
from titus_isolate.docker.utils import get_current_workloads
from titus_isolate.isolate.resource_manager import ResourceManager
from titus_isolate.isolate.workload_manager import WorkloadManager
from titus_isolate.model.processor.utils import get_cpu
from titus_isolate.utils import config_logs

log = logging.getLogger()

event = Event()


def signal_handler(sig, frame):
    event.set()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


@click.command()
@click.option('--package-count', help="The number of packages in the CPU")
@click.option('--cores-per-package', help="The number of cores per package")
@click.option('--threads-per-core', default=2, help="The number of threads per core")
def main(package_count, cores_per_package, threads_per_core):
    log.info("Modeling the CPU...")
    cpu = get_cpu(int(package_count), int(cores_per_package), int(threads_per_core))

    # Setup the workload manager
    log.info("Setting up the resource manager...")
    docker_client = docker.from_env()
    workload_manager = WorkloadManager(ResourceManager(cpu, docker_client))

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

    # Block exit forever
    event.wait()


if __name__ == "__main__":
    config_logs()
    main()
