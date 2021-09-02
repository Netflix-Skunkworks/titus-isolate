import random
from typing import List

from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse, get_workload_allocations
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.model.processor.cpu import Cpu
from titus_isolate.model.processor.thread import Thread
from titus_isolate import log


class NaiveCpuAllocator(CpuAllocator):

    def isolate(self, request: AllocateRequest) -> AllocateResponse:
        cpu = request.get_cpu()

        # If a workload is on a thread and not mentioned in the request it should be removed from every thread
        for thread in cpu.get_threads():
            workload_ids_to_be_removed = [w_id for w_id in thread.get_workload_ids() if w_id not in request.get_workloads()]
            log.info("workloads to be removed from thread: %s --> %s", thread.get_id(), workload_ids_to_be_removed)
            for w_id in workload_ids_to_be_removed:
                log.info("free thread: %s of workload: %s", thread.get_id(), w_id)
                thread.free(w_id)

        # If a workload is requested but not currently isolated, isolate it
        currently_isolated_workload_ids = cpu.get_workload_ids_to_thread_ids().keys()
        log.info("currently isolate workloads: %s", currently_isolated_workload_ids)
        for workload in request.get_workloads().values():
            if workload.get_task_id() not in currently_isolated_workload_ids:
                threads = self._get_assign_threads(cpu, workload.get_thread_count())
                for thread in threads:
                    log.info("claim thread: %s for workload: %s", thread.get_id(), workload.get_task_id())
                    thread.claim(workload.get_task_id())

        return AllocateResponse(
            cpu,
            get_workload_allocations(cpu, list(request.get_workloads().values())),
            self.get_name())

    @staticmethod
    def _get_assign_threads(cpu: Cpu, thread_count: int) -> List[Thread]:
        empty_threads = cpu.get_empty_threads()

        if len(empty_threads) >= thread_count:
            random.shuffle(empty_threads)
            return empty_threads[:thread_count]

        # If there aren't enough empty threads, fill the gap with random claimed threads
        claimed_threads = cpu.get_claimed_threads()
        random.shuffle(claimed_threads)
        claimed_threads = claimed_threads[:thread_count - len(empty_threads)]

        return empty_threads + claimed_threads

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass
