import copy
import logging
import os
import unittest

from tests.config.test_property_provider import TestPropertyProvider
from tests.utils import config_logs
from titus_isolate.cgroup.utils import _get_cgroup_path_from_list, CPUSET, get_cgroup_path_from_file, \
     parse_cpuacct_usage_all, parse_cpuset
from titus_isolate.config.config_manager import ConfigManager
from titus_isolate.utils import set_config_manager

config_logs(logging.DEBUG)

test_input = [
    "11:perf_event:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "10:memory:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "9:cpu,cpuacct:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "8:devices:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "7:pids:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "6:blkio:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "5:hugetlb:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "4:cpuset:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "3:freezer:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "2:net_cls,net_prio:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868",
    "1:name=systemd:/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868"
]

expected_path = "/containers.slice/d6d503e8-2223-4ad2-9133-ca6cce6a80d0/ed56135367095a907399275e562c50e49c724f9f5a874f352a849f4269f20868"

test_cpuacct_usage_all = """cpu user system
0 1814944364271 6577923615
1 1779435414091 7480246384
2 1777382071858 3717455388
3 94650661840 3906076701
4 87260321116 3252257410
5 85394260758 2670064564
6 81348987784 2903042963
7 84444557805 3166412338
8 78788893824 2597013237
9 81123332620 2430059387
10 77804993859 3992121849
11 80491181515 2835111623
12 78390730581 2598913135
13 79170459307 2576604949
14 78085525474 2023339699
15 78904731716 3034411871
16 1832461038817 5622984712
17 1805302725812 4828766873
18 111138113817 5322901202
19 115662196792 5069102029
20 117655593009 4803084062
21 112501851830 4862298631
22 104506498456 5303581829
23 101552871369 5485873125
24 105234698881 5026816265
25 111687985392 4714329942
26 109537017993 4560444421
27 101638461760 4717127659
28 97073733942 5047125018
29 96233847582 4760209668
30 97098316228 4964947706
31 99771347463 4420455868
32 102989024416 2596330795
33 69549473754 1798438738
34 84514184030 1707737680
35 88798735080 1946080701
36 80938596751 2420131592
37 82885024719 2327264133
38 80298747220 2215716707
39 84467693309 2467366465
40 79474923562 2292270740
41 81210515049 2481097132
42 77948367990 2259990447
43 84721153886 2471078314
44 79727906088 2213784661
45 81314937088 2087414684
46 78805639713 2048293349
47 107504180309 4172866070
48 103890519040 5458058474
49 102044545879 4505705701
50 100302149626 4596966906
51 104743553188 4636868434
52 102275945668 4372605348
53 100438920253 4261728837
54 97024213652 4400524105
55 99740976671 4681548505
56 106898061032 4336172719
57 104851869980 4097362348
58 102344479456 4586906394
59 100618023739 4513969593
60 99883051429 4289557124
61 93867374960 4106993824
62 108722794361 4090185066
63 136320936103 3576909590
64 0 0
65 0 0
66 0 0
67 0 0
68 0 0
69 0 0
70 0 0
71 0 0
72 0 0
73 0 0
74 0 0
75 0 0
76 0 0
77 0 0
78 0 0
79 0 0
80 0 0
81 0 0
82 0 0
83 0 0
84 0 0
85 0 0
86 0 0
87 0 0
88 0 0
89 0 0
90 0 0
91 0 0
92 0 0
93 0 0
94 0 0
95 0 0
96 0 0
97 0 0
98 0 0
99 0 0
100 0 0
101 0 0
102 0 0
103 0 0
104 0 0
105 0 0
106 0 0
107 0 0
108 0 0
109 0 0
110 0 0
111 0 0
112 0 0
113 0 0
114 0 0
115 0 0
116 0 0
117 0 0
118 0 0
119 0 0
120 0 0
121 0 0
122 0 0
123 0 0
124 0 0
125 0 0
126 0 0
127 0 0
"""


class TestUtils(unittest.TestCase):

    def test_parse_cpuset_path_success(self):
        self.assertEqual(expected_path, _get_cgroup_path_from_list(test_input, CPUSET))

    def test_parse_cpuset_path_failure(self):
        # Note that the cpuset line is missing when compared to the success case
        cgroups_list = copy.deepcopy(test_input)
        cgroups_list.pop(7)
        self.assertEqual(None, _get_cgroup_path_from_list(cgroups_list, CPUSET))

    def test_parse_from_file(self):
        set_config_manager(ConfigManager(TestPropertyProvider({})))
        dir = os.path.dirname(os.path.abspath(__file__))
        self.assertEqual(expected_path, get_cgroup_path_from_file(dir + "/test_cgroup_file", CPUSET))

    def test_parse_cpuacct_usage_all(self):
        lines = parse_cpuacct_usage_all(test_cpuacct_usage_all)
        self.assertEqual(128, len(lines))

        # Spot check the first two rows
        # 0 1814944364271 6577923615
        # 1 1779435414091 7480246384

        self.assertEqual(0, lines[0].pu_id)
        self.assertEqual(1814944364271, lines[0].user)
        self.assertEqual(6577923615, lines[0].system)

        self.assertEqual(1, lines[1].pu_id)
        self.assertEqual(1779435414091, lines[1].user)
        self.assertEqual(7480246384, lines[1].system)

    def test_parse_cpuset(self):
        s = "2"
        threads = parse_cpuset(s)
        self.assertEqual([2], threads)

        s = "7-9"
        threads = parse_cpuset(s)
        self.assertEqual([7, 8, 9], threads)

        s = "7-8"
        threads = parse_cpuset(s)
        self.assertEqual([7, 8], threads)

        s = "2,5,7-9,12"
        threads = parse_cpuset(s)
        self.assertEqual([2, 5, 7, 8, 9, 12], threads)

        s = "5,2,12,7-9"
        threads = sorted(parse_cpuset(s))
        self.assertEqual([2, 5, 7, 8, 9, 12], threads)


