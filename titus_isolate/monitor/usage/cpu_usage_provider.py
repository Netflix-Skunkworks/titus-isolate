from abc import abstractmethod


class CpuUsageProvider:

    @abstractmethod
    def get_cpu_usage(self, seconds: int, agg_granularity_secs : int) -> dict:
        """
        Returns CPU usage per workload over the last `seconds` seconds, aggregated at `agg_granularity_secs`.
        """
        pass
