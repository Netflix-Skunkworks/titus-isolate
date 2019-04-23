import copy
import json
import logging
import os
import tempfile
import unittest

import pytest

from titus_isolate.allocate.allocate_response import deserialize_response
from titus_isolate.allocate.allocate_threads_request import AllocateThreadsRequest
from titus_isolate.api.testing import set_testing

set_testing()

from tests.allocate.crashing_allocators import CrashingAllocator
from tests.utils import get_test_workload, config_logs, DEFAULT_TEST_REQUEST_METADATA
from titus_isolate import log
from titus_isolate.allocate.greedy_cpu_allocator import GreedyCpuAllocator
from titus_isolate.api.solve import parse_workload, parse_cpu, app, set_cpu_allocator
from titus_isolate.event.constants import STATIC
from titus_isolate.model.processor.config import get_cpu

config_logs(logging.DEBUG)


@pytest.fixture
def client():
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    client = app.test_client()
    yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


class TestStatus(unittest.TestCase):

    def setUp(self):
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    def test_parse_workload(self):
        w_in = get_test_workload("a", 2, STATIC)
        log.info("w_in : {}".format(w_in))

        w_out = parse_workload(w_in.to_dict())
        log.info("w_out: {}".format(w_out))

        self.assertEqual(w_in.to_dict(), w_out.to_dict())

    def test_parse_cpu(self):
        cpu_in = get_cpu()
        log.info("cpu_in : {}".format(cpu_in))

        cpu_out = parse_cpu(cpu_in.to_dict())
        log.info("cpu_out: {}".format(cpu_out))

        self.assertEqual(cpu_in.to_dict(), cpu_out.to_dict())

    def test_allocator_failure(self):
        set_cpu_allocator(CrashingAllocator())
        response = self.client.put("/assign_threads")
        self.assertEqual(500, response.status_code)

        response = self.client.put("/free_threads")
        self.assertEqual(500, response.status_code)

        response = self.client.put("/rebalance")
        self.assertEqual(500, response.status_code)

    def test_assign_free_threads(self):
        cpu = get_cpu()
        workload = get_test_workload("a", 2, STATIC)
        workloads = {
            workload.get_id(): workload
        }

        cpu_allocator = GreedyCpuAllocator()
        set_cpu_allocator(cpu_allocator)

        # Assign threads
        log.info("Assign threads")
        cpu_in_0 = copy.deepcopy(cpu)
        request = AllocateThreadsRequest(cpu_in_0, workload.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu_out_0 = cpu_allocator.assign_threads(request).get_cpu()

        cpu_in_1 = copy.deepcopy(cpu)
        body = AllocateThreadsRequest(cpu_in_1, workload.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA).to_dict()
        cpu_out_1 = self.client.put(
            "/assign_threads",
            data=json.dumps(body),
            content_type='application/json')
        cpu_out_1 = deserialize_response(cpu_out_1.headers, cpu_out_1.json).get_cpu()

        log.info("cpu_out_0: {}".format(cpu_out_0))
        log.info("cpu_out_1: {}".format(cpu_out_1))
        self.assertEqual(cpu_out_0.to_dict(), cpu_out_1.to_dict())

        # Free threads
        log.info("Free threads")
        cpu_in_0 = copy.deepcopy(cpu_out_0)
        request = AllocateThreadsRequest(cpu_in_0, workload.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA)
        cpu_out_0 = cpu_allocator.free_threads(request).get_cpu()

        cpu_in_1 = copy.deepcopy(cpu_out_1)
        body = AllocateThreadsRequest(cpu_in_1, workload.get_id(), workloads, {}, DEFAULT_TEST_REQUEST_METADATA).to_dict()
        cpu_out_1 = self.client.put(
            "/free_threads",
            data=json.dumps(body),
            content_type='application/json')
        cpu_out_1 = deserialize_response(cpu_out_1.headers, cpu_out_1.json).get_cpu()

        log.info("cpu_out_0: {}".format(cpu_out_0))
        log.info("cpu_out_1: {}".format(cpu_out_1))
        self.assertEqual(cpu_out_0.to_dict(), cpu_out_1.to_dict())
