import math
import unittest
import uuid

from titus_isolate.allocate.constants import CPU_USAGE, MEM_USAGE, NET_RECV_USAGE, NET_TRANS_USAGE, DISK_USAGE
from titus_isolate.monitor.resource_usage import GlobalResourceUsage, deserialize_global_resource_usage


class TestResourceUsage(unittest.TestCase):

    def test_simple_usage(self):
        w_id0 = str(uuid.uuid4())
        w_id1 = str(uuid.uuid4())

        input_usage0 = [0.0, 1.0, 2.0]
        padded_usage0 = [float('nan'), float('nan'), 0.0, 1.0, 2.0]
        input_usage1 = [3.0, 4.0, 5.0]
        padded_usage1 = [float('nan'), float('nan'), 3.0, 4.0, 5.0]

        raw_usage = {
            CPU_USAGE: {
                w_id0: input_usage0,
                w_id1: input_usage1
            },
            MEM_USAGE: {
                w_id0: input_usage0,
                w_id1: input_usage1
            },
            NET_RECV_USAGE: {
                w_id0: input_usage0,
                w_id1: input_usage1
            },
            NET_TRANS_USAGE: {
                w_id0: input_usage0,
                w_id1: input_usage1
            },
            DISK_USAGE: {
                w_id0: input_usage0,
                w_id1: input_usage1
            }
        }

        ru = GlobalResourceUsage(raw_usage, 5)

        def __assert_expected(expected_usage, w_id):
            self.__assert_list_equal_with_nans(expected_usage, ru.get_cpu_usage()[w_id])
            self.__assert_list_equal_with_nans(expected_usage, ru.get_mem_usage()[w_id])
            self.__assert_list_equal_with_nans(expected_usage, ru.get_net_trans_usage()[w_id])
            self.__assert_list_equal_with_nans(expected_usage, ru.get_net_recv_usage()[w_id])
            self.__assert_list_equal_with_nans(expected_usage, ru.get_disk_usage()[w_id])

        def __assert_all_expected(expected_usage, all_usage):
            self.__assert_list_equal_with_nans(expected_usage, all_usage[CPU_USAGE])
            self.__assert_list_equal_with_nans(expected_usage, all_usage[MEM_USAGE])
            self.__assert_list_equal_with_nans(expected_usage, all_usage[NET_RECV_USAGE])
            self.__assert_list_equal_with_nans(expected_usage, all_usage[NET_TRANS_USAGE])
            self.__assert_list_equal_with_nans(expected_usage, all_usage[DISK_USAGE])

        __assert_expected(padded_usage0, w_id0)
        __assert_expected(padded_usage1, w_id1)
        __assert_all_expected(padded_usage0, ru.get_all_usage_for_workload(w_id0))
        __assert_all_expected(padded_usage1, ru.get_all_usage_for_workload(w_id1))

        # serialize/deserialize and assert again
        serial_ru = ru.serialize()
        ru = deserialize_global_resource_usage(serial_ru)

        __assert_expected(padded_usage0, w_id0)
        __assert_expected(padded_usage1, w_id1)
        __assert_all_expected(padded_usage0, ru.get_all_usage_for_workload(w_id0))
        __assert_all_expected(padded_usage1, ru.get_all_usage_for_workload(w_id1))

    def test_empty_usage(self):
        ru = GlobalResourceUsage({})

        def __assert_empty():
            self.assertIsNotNone(ru)
            self.assertEqual({}, ru.serialize())
            self.assertEqual({}, ru.get_all_usage_for_workload("foo"))
            self.assertIsNone(ru.get_cpu_usage())
            self.assertIsNone(ru.get_mem_usage())
            self.assertIsNone(ru.get_net_recv_usage())
            self.assertIsNone(ru.get_net_trans_usage())
            self.assertIsNone(ru.get_disk_usage())

        __assert_empty()

        # serialize/deserialize and assert again
        serial_du = ru.serialize()
        ru = deserialize_global_resource_usage(serial_du)
        __assert_empty()

    def __assert_list_equal_with_nans(self, l0, l1):
        self.assertEqual(len(l0), len(l1))
        for i in range(len(l0)):
            e0 = l0[i]
            e1 = l1[i]
            if math.isnan(e0):
                self.assertTrue(math.isnan(e1))
            else:
                self.assertEqual(e0, e1)
