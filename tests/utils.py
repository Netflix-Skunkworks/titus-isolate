from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread

DEFAULT_PACKAGE_COUNT = 2
DEFAULT_CORE_COUNT = 4
DEFAULT_THREAD_COUNT = 2
DEFAULT_TOTAL_THREAD_COUNT = DEFAULT_PACKAGE_COUNT * DEFAULT_CORE_COUNT * DEFAULT_THREAD_COUNT


def __get_threads(package_index, core_index, package_count, core_count, thread_count=DEFAULT_THREAD_COUNT):
    threads = []
    for row_index in range(thread_count):
        offset = row_index * package_count * core_count
        index = offset + package_index * core_count + core_index
        threads.append(Thread(index))

    return threads


def get_test_cpu(package_count=DEFAULT_PACKAGE_COUNT, core_count=DEFAULT_CORE_COUNT):
    packages = []
    for p_i in range(package_count):

        cores = []
        for c_i in range(core_count):
            cores.append(Core(c_i, __get_threads(p_i, c_i, package_count, core_count)))

        packages.append(Package(p_i, cores))

    return Cpu(packages)
