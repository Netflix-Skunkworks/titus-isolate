from functools import reduce


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

    def get_empty_threads(self):
        return reduce(list.__add__, [package.get_empty_threads() for package in self.get_packages()])
