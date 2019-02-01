from collections import defaultdict
from functools import reduce

from titus_isolate.model.processor import utils


class Cpu:
    def __init__(self, packages):
        if len(packages) < 1:
            raise ValueError("A CPU must contain at least 1 package.")

        self.__packages = packages

    def get_packages(self):
        return self.__packages

    def get_emptiest_package(self):
        emptiest_package = self.__packages[0]
        curr_empty_thread_count = len(emptiest_package.get_empty_threads())

        for package in self.get_packages()[1:]:
            new_empty_thread_count = len(package.get_empty_threads())

            if new_empty_thread_count > curr_empty_thread_count:
                emptiest_package = package
                curr_empty_thread_count = new_empty_thread_count

        return emptiest_package

    def get_cores(self):
        return reduce(list.__add__, [package.get_cores() for package in self.get_packages()])

    def get_threads(self):
        return reduce(list.__add__, [package.get_threads() for package in self.get_packages()])

    def get_empty_threads(self):
        return utils.get_empty_threads(self.get_threads())

    def get_claimed_threads(self):
        return utils.get_claimed_threads(self.get_threads())

    def clear(self):
        for t in self.get_threads():
            t.free()

    def get_workload_ids_to_thread_ids(self):
        res = defaultdict(list)
        for t in self.get_threads():
            if t.is_claimed():
                wid = t.get_workload_id()
                res[wid] = res[wid] + [t.get_id()]
        return res

    def __str__(self):
        n_packages = len(self.get_packages())
        n_cores = n_packages * len(self.get_packages()[0].get_cores())
        return ('%i packages, %i cores per package, %i threads per core\n'
            '%i threads claimed\n'
            '%s') % (
                n_packages,
                n_cores,
                int(len(self.get_threads()) / n_cores),
                len(self.get_claimed_threads()),
                utils.visualize(self)
            )
