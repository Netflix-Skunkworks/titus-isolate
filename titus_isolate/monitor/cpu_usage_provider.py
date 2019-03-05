from abc import abstractmethod


class CpuUsageProvider:

    @abstractmethod
    def get_cpu_usage(self, seconds: int) -> dict:
        """
        Returns CPU usage per workload over the last `seconds` seconds
        """
        pass
