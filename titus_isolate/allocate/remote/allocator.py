from collections import defaultdict
import copy

import grpc
import titus_isolate.allocate.remote.isolate_pb2 as pb
import titus_isolate.allocate.remote.isolate_pb2_grpc as pb_grpc

from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.allocate.workload_allocate_response import WorkloadAllocateResponse
from titus_isolate.config.constants import GRPC_REMOTE_ALLOC_ENDPOINT, GRPC_REMOTE_ALLOC_CLIENT_CALL_TIMEOUT_MS, \
    GRPC_REMOTE_ALLOC_DEFAULT_CLIENT_CALL_TIMEOUT_MS
from titus_isolate.kub.constants import *
from titus_isolate.kub.utils import get_node
from titus_isolate.model.processor.config import get_cpu_from_env
from titus_isolate.utils import get_config_manager

REQ_TYPE_METADATA_KEY = "req_type"


class GrpcRemoteIsolationAllocator(CpuAllocator):

    def __init__(self):
        config_manager = get_config_manager()
        self.__endpoint = config_manager.get_cached_str(GRPC_REMOTE_ALLOC_ENDPOINT, None)
        if self.__endpoint is None:
            raise Exception("Could not get remote allocator endpoint address.")
        self.__call_timeout_secs = config_manager.get_cached_int(GRPC_REMOTE_ALLOC_CLIENT_CALL_TIMEOUT_MS,
                                                                 GRPC_REMOTE_ALLOC_DEFAULT_CLIENT_CALL_TIMEOUT_MS) / 1000.0

        self.__stub = self.__create_stub()
        self.__instance_ctx = self.__pull_context()
        self.__reg = None
        self.__empty_cpu = get_cpu_from_env()
        self.__natural2original_indexing = self.__empty_cpu.get_natural_indexing_2_original_indexing()
        self.__original2natural_indexing = {v: k for k, v in self.__natural2original_indexing.items()}

    def __build_base_req(self, cpu) -> pb.IsolationRequest:
        req = pb.IsolationRequest()
        packages = []
        for p in cpu.get_packages():
            cores = []
            num_cores = 0
            for c in p.get_cores():
                num_cores += 1
                threads = []
                threads_per_core = 0
                for t in c.get_threads():
                    threads_per_core += 1
                    task_ids = t.get_workload_ids()
                    if len(task_ids) > 0:
                        pt = pb.Thread()
                        pt.id = self.__original2natural_indexing[t.get_id()]
                        for tid in task_ids:
                            pt.task_ids.append(tid)
                        threads.append(pt)
                if len(threads) > 0:
                    pc = pb.Core()
                    pc.id = c.get_id()
                    pc.threads.extend(threads)
                    cores.append(pc)
            pp = pb.Package()
            pp.id = p.get_id()
            pp.num_cores = num_cores
            pp.cores.extend(cores)
            packages.append(pp)
        req.layout.packages.extend(packages)
        req.layout.threads_per_core = threads_per_core
        req.instance_context.CopyFrom(self.__instance_ctx)
        return req

    def __deser(self, response: pb.IsolationResponse) -> AllocateResponse:
        new_cpu = copy.deepcopy(self.__empty_cpu)
        id2workloads = defaultdict(list)
        wa_responses = []
        for wid, cpuset in response.cpusets.items():
            thread_ids = [self.__natural2original_indexing[tid] for tid in cpuset.thread_ids]
            war = WorkloadAllocateResponse(
                wid,
                thread_ids,
                cpuset.cfs_tunables.shares,
                cpuset.cfs_tunables.quota_us,
                cpuset.cpuset_tunables.memory_migrate,
                cpuset.cpuset_tunables.memory_spread_page,
                cpuset.cpuset_tunables.memory_spread_slab)
            wa_responses.append(war)
            for tid in thread_ids:
                id2workloads[tid].append(wid)
        for package in new_cpu.get_packages():
            for core in package.get_cores():
                for thread in core.get_threads():
                    workloads = id2workloads.get(thread.get_id(), None)
                    if workloads is not None:
                        for wid in workloads:
                            thread.claim(wid)

        return AllocateResponse(new_cpu, wa_responses, self.get_name(), {})

    def __process(self, request: AllocateRequest) -> AllocateResponse:
        req = self.__build_base_req(request.get_cpu())
        req.metadata[REQ_TYPE_METADATA_KEY] = "isolate" # for logging purposes server side

        for wid, w in request.get_workloads().items():
            req.task_to_job_id[wid] = w.get_job_id()
            req.tasks_to_place.append(wid)

        try:
            log.info("remote isolate (tasks_to_place=%s)", req.tasks_to_place)
            response = self.__stub.ComputeIsolation(req, timeout=self.__call_timeout_secs)
        except grpc.RpcError as e:
            log.exception("remote isolate failed (tasks_to_place=%s)")
            raise e

        try:
            return self.__deser(response)
        except Exception as e:
            log.exception("failed to deseralize response for remote isolate request")
            raise e

    def __create_stub(self) -> pb_grpc.IsolationServiceStub:
        channel = grpc.insecure_channel(self.__endpoint,
                                        compression=grpc.Compression.Gzip)

        return pb_grpc.IsolationServiceStub(channel)

    @staticmethod
    def __pull_context() -> pb.InstanceContext:
        node = get_node()
        ctx = pb.InstanceContext()
        ctx.instance_id = node.metadata.name
        ctx.stack = node.metadata.annotations.get(ANNOTATION_KEY_STACK, '')
        ctx.cluster = node.metadata.annotations.get(ANNOTATION_KEY_CLUSTER, '')
        ctx.autoscale_group = node.metadata.annotations.get(ANNOTATION_KEY_ASG, '')
        ctx.resource_pool = node.metadata.annotations.get(LABEL_KEY_RESOURCE_POOL, '')
        ctx.instance_type = node.metadata.annotations.get(ANNOTATION_KEY_INSTANCE_TYPE, '')
        return ctx

    def isolate(self, request: AllocateRequest) -> AllocateResponse:
        return self.__process(request)

    def get_name(self) -> str:
        return self.__class__.__name__

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass
