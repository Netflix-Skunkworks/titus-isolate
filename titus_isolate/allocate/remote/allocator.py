from collections import defaultdict
import copy

import grpc
import titus_isolate.allocate.remote.isolate_pb2 as pb
import titus_isolate.allocate.remote.isolate_pb2_grpc as pb_grpc

from titus_isolate import log
from titus_isolate.allocate.allocate_request import AllocateRequest
from titus_isolate.allocate.allocate_response import AllocateResponse, deserialize_response
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.allocate.constants import UNKNOWN_CPU_ALLOCATOR
from titus_isolate.allocate.cpu_allocate_exception import CpuAllocationException
from titus_isolate.allocate.cpu_allocator import CpuAllocator
from titus_isolate.allocate.workload_allocate_response import WorkloadAllocateResponse
from titus_isolate.config.constants import NEW_REMOTE_ALLOC_ENDPOINT, NEW_REMOTE_ALLOC_CLIENT_CALL_TIMEOUT_MS, \
    NEW_REMOTE_ALLOC_DEFAULT_CLIENT_CALL_TIMEOUT_MS, \
    MAX_SOLVER_CONNECT_SEC, DEFAULT_MAX_SOLVER_CONNECT_SEC
from titus_isolate.kub.constants import *
from titus_isolate.kub.utils import get_node
from titus_isolate.model.processor.config import get_cpu_from_env
from titus_isolate.utils import get_config_manager


ALLOCATOR_NAME = "RemoteIsolationAllocator"
REQ_TYPE_METADATA_KEY = "req_type"

class Allocator(CpuAllocator):

    def __create_stub(self) -> pb_grpc.IsolationServiceStub:
        channel = grpc.insecure_channel(self.__endpoint)
        # todo: timeout on connect
        
        return pb_grpc.IsolationServiceStub(channel)

    def __pull_context(self) -> pb.InstanceContext:
        node = get_node()
        ctx = pb.InstanceContext()
        ctx.instance_id = node.metadata.name
        ctx.stack = node.metadata.annotations.get(ANNOTATION_KEY_STACK, '')
        ctx.cluster = node.metadata.annotations.get(ANNOTATION_KEY_CLUSTER, '') 
        ctx.autoscale_group = node.metadata.annotations.get(ANNOTATION_KEY_ASG, '')
        ctx.resource_pool = node.metadata.annotations.get(LABEL_KEY_RESOURCE_POOL, '')
        ctx.instance_type = node.metadata.annotations.get(ANNOTATION_KEY_INSTANCE_TYPE, '')
        return ctx

    def __init__(self, free_thread_provider):
        config_manager = get_config_manager()
        self.__endpoint = config_manager.get_str(NEW_REMOTE_ALLOC_ENDPOINT, None)
        if not self.__endpoint:
            raise Exception("Could not get remote allocator endpoint address.")
        self.__call_timeout_secs = 1000.0 * config_manager.get_int(NEW_REMOTE_ALLOC_CLIENT_CALL_TIMEOUT_MS,
            NEW_REMOTE_ALLOC_DEFAULT_CLIENT_CALL_TIMEOUT_MS)

        self.__stub = self.__create_stub()
        self.__instance_ctx = self.__pull_context()
        self.__reg = None
        self.__empty_cpu = get_cpu_from_env()
        self.__natural2original_indexing = self.__empty_cpu.get_natural_indexing_2_original_indexing()
        self.__original2natural_indexing = {v: k for k,v in self.__natural2original_indexing.items()}

    def __build_base_req(self, cpu) -> pb.PlacementRequest:
        req = pb.PlacementRequest()
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

    def __deser(self, response : pb.PlacementResponse) -> AllocateResponse:
        new_cpu = copy.deepcopy(self.__empty_cpu)
        id2workloads = defaultdict(list)
        wa_responses = []
        for wid, assignment in response.assignments.items():
            thread_ids = [self.__natural2original_indexing[tid] for tid in assignment.thread_ids]
            war = WorkloadAllocateResponse(
                wid,
                thread_ids,
                1, # TODO
                1, #TODO
                False, False, False

            )
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

        metadata = {} # cell should be filled by service

        return AllocateResponse(new_cpu, wa_responses, ALLOCATOR_NAME, metadata)

    def __process(self, request: AllocateRequest, req_type : str, is_delete : bool) -> AllocateResponse:
        req_wid = ''
        if isinstance(request, AllocateThreadsRequest):
            req_wid = request.get_workload_id()
        req = self.__build_base_req(request.get_cpu())
        req.metadata[REQ_TYPE_METADATA_KEY] = req_type # for logging purposes server side

        for wid, w in request.get_workloads().items():
            req.task_to_job_id[wid] = w.get_job_id()
            if is_delete and wid == req_wid:
                continue
            req.tasks_to_place.append(wid)

        try:
            log.info("remote %s (tasks_to_place=%s)", req_type, req.tasks_to_place)
            response = self.__stub.ComputePlacement(req, timeout=self.__call_timeout_secs)
        except grpc.RpcError as e:
            log.error("remote %s failed (tasks_to_place=%s):\n%s", req_type, req.tasks_to_place, repr(e))
            raise e

        try:
            return self.__deser(response)
        except Exception as e:
            log.error("failed to deseralize response for remote %s of %s:\n%s", req_type, req_wid, repr(e))
            raise e

    def assign_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        return self.__process(request, "assign", False)

    def free_threads(self, request: AllocateThreadsRequest) -> AllocateResponse:
        return self.__process(request, "free", True)

    def rebalance(self, request: AllocateRequest) -> AllocateResponse:
        return self.__process(request, "rebalance", False)

    def get_name(self) -> str:
        return ALLOCATOR_NAME

    def set_registry(self, registry, tags):
        pass

    def report_metrics(self, tags):
        pass
