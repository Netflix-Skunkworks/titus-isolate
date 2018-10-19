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
from titus_isolate.isolate.resource_manager import ResourceManager
from titus_isolate.model.processor.utils import get_cpu

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
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

    # Setup the resource manager
    log.info("Setting up the resource manager...")
    docker_client = docker.from_env()
    resource_manager = ResourceManager(cpu, docker_client)

    # Setup the event handlers
    log.info("Setting up the event handlers...")
    event_logger = EventLogger()
    create_event_handler = CreateEventHandler(resource_manager)
    free_event_handler = FreeEventHandler(resource_manager)
    event_handlers = [event_logger, create_event_handler, free_event_handler]

    log.info("Waiting for Docker events...")
    EventManager(docker_client.events(), event_handlers)
    event.wait()


if __name__ == "__main__":
    main()
