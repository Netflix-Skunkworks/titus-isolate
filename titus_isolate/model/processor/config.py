import platform
import subprocess

from titus_isolate.model.processor.core import Core
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.package import Package
from titus_isolate.model.processor.thread import Thread
from titus_isolate.model.processor.utils import DEFAULT_PACKAGE_COUNT, DEFAULT_CORE_COUNT, DEFAULT_THREAD_COUNT


def get_cpu_from_env():
    system = platform.system()
    processor = None

    if system == 'Darwin':
        processor = MacProcessor()
    elif system == 'Linux':
        processor = LinuxProcessor()

    if processor is None:
        raise EnvironmentError("Unexpected system type: '{}'".format(system))

    return get_cpu(processor.get_package_count(), processor.get_cores_per_package(), processor.get_threads_per_core())


def get_cpu(
        package_count=DEFAULT_PACKAGE_COUNT,
        cores_per_package=DEFAULT_CORE_COUNT,
        threads_per_core=DEFAULT_THREAD_COUNT):
    packages = []
    for p_i in range(package_count):

        cores = []
        for c_i in range(cores_per_package):
            cores.append(
                Core(c_i, __get_threads(p_i, c_i, package_count, cores_per_package, threads_per_core)))

        packages.append(Package(p_i, cores))

    return Cpu(packages)


def __get_threads(package_index, core_index, package_count, core_count, thread_count):
    threads = []
    for row_index in range(thread_count):
        offset = row_index * package_count * core_count
        index = offset + package_index * core_count + core_index
        threads.append(Thread(index))

    return threads


class Processor:
    def __init__(self, package_count, cores_per_package, threads_per_core):
        self.__package_count = package_count
        self.__cores_per_package = cores_per_package
        self.__threads_per_core = threads_per_core

    def get_package_count(self):
        return self.__package_count

    def get_cores_per_package(self):
        return self.__cores_per_package

    def get_threads_per_core(self):
        return self.__threads_per_core


class LinuxProcessor(Processor):
    def __init__(self):
        super(LinuxProcessor, self).__init__(
            self.__get_package_count(),
            self.__get_cores_per_package(),
            self.__get_threads_per_core())

    def __get_package_count(self):
        return self.__get_lscpu_value('^Socket')

    def __get_cores_per_package(self):
        return self.__get_lscpu_value('^Core')

    def __get_threads_per_core(self):
        return self.__get_lscpu_value('^Thread')

    @staticmethod
    def __get_lscpu_value(grep_filter):
        output = subprocess.check_output("lscpu | grep -E {}".format(grep_filter), shell=True).decode('utf-8')
        return int(output.split(':')[1].strip())


class MacProcessor(Processor):
    def __init__(self):
        super(MacProcessor, self).__init__(
            self.__get_package_count(),
            self.__get_cores_per_package(),
            self.__get_threads_per_core())

    def __get_package_count(self):
        return self.__get_sysctl_value('hw.packages')

    def __get_cores_per_package(self):
        return int(self.__get_physical_cores() / self.__get_package_count())

    def __get_threads_per_core(self):
        logical_cpus = self.__get_sysctl_value('hw.logicalcpu')
        return int(logical_cpus / self.__get_physical_cores())

    def __get_physical_cores(self):
        return self.__get_sysctl_value('hw.physicalcpu')

    @staticmethod
    def __get_sysctl_value(key):
        return int(subprocess.check_output(['sysctl', '-n', key]).decode('utf-8').strip())
