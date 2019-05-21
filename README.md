## Introduction

`titus-isolate` enables the isolated and efficient use of compute resources in a multi-tenant container environment.
Given a machine hosting multiple containers, `titus-isolate` partitions the available compute hardware (hyper-threads) 
to achieve isolation and efficiency goals.

In general greater cost efficiency implies less isolation and vice-versa.  To achieve maximal isolation workloads 
(containers) could each be running on their own dedicated machine, at the cost of great inefficiency.  On the other hand,
to achieve maximal efficiency, many containers (thousands) could be run on the same machine, but at the cost of high
interference and poor performance.

## Isolation

The core mechanism which enables compute isolation is to partition access to sets of hyper-threads on a per workload basis.
This is accomplished by manipulation of the [`cpusets` cgroup](https://www.kernel.org/doc/Documentation/cgroup-v1/cpusets.txt)

Workloads are categorized into either static or burst categories.  Each choice of workload type comes with a cost/benefit trade off.
* static
	* benefit: the workload will be isolated to the greatest degree possible, leading to more consistent performance
	* cost: the workload opts out of consuming unallocated CPU capacity
* burst
	* benefit: the workload may consume unallocate CPU capacity
	* cost: the workload opts in to less isolation from other workloads, and will see greater variance in performance depending on CPU usage
	
Choosing an efficient and performant partitioning of CPU resources is not a perfectly solvable problem.  `titus-isolate`
allows for the specification of two core components which determine actual partitioning behavior: `CpuAllocator` and `FreeThreadProvider`

In general the `CpuAllocator` determines how best to partition CPU resources according to the requested capacity of each
workload.  The `FreeThreadProvider` determines which hyper-threads are "free" and therefore consumable by `burst`
workloads.  The most advanced choices for these components are the `ForecastIPCpuAllocator` and 
`OversubscribeFreeThreadProvider` respectively.

### CPU Diagrams
Let us walk through an example scenario to get a feel for how hyper-thread allocation occurs under different conditions.
We diagram a CPU in the following manner.  Every CPU has two packages (sockets) with indices `0` and `1`.
```
| 0 | 0 | 0 | 0 | 
| 0 | 0 | 0 | 0 |
| ------------- |
| 1 | 1 | 1 | 1 |
| 1 | 1 | 1 | 1 |
```

Each socket has an equal number of cores with corresponding indices:
```
| 0 | 1 | 2 | 3 | 
| 0 | 1 | 2 | 3 |
| ------------- |
| 0 | 1 | 2 | 3 |
| 0 | 1 | 2 | 3 |
```

As far as Linux and `cpuset`s are concerned the only index of note is that of the `thread`.  Thread indices across cores
and sockets are assigned as follows:
```
|  0 |  1 |  2 |  3 | 
|  8 |  9 | 10 | 11 |
| ----------------- |
|  4 |  5 |  6 |  7 |
| 12 | 13 | 14 | 15 |
```

### Example
Below we see a typical example CPU with a single static workload `a` requesting 2 threads.

```
| a | a |   |   |   a: ['static_2']
|   |   |   |   |
| ------------- |
|   |   |   |   |
|   |   |   |   |
```

Note that this allocation has two nice characteristics.
1. The workload is constrained to a single socket
2. The workload does not share a core

Now let's add a `burst` workload requesting 4 threads.
```
| a | a | b | b |   a: ['static_2']
|   |   | b | b |   b: ['burst0_4']
| ------------- |
| b | b | b | b |
| b | b | b | b |
```

In this case workload `b` which requested 4 threads was actually given access to 12.  Note that the `static` workload
still has an optimal arrangement avoiding hyper-threading either with itself or the `burst` workload.

Let's add another `burst` workload requesting 4 threads.
```
| a | a | a | a |   a: ['burst0_4', 'burst1_4']
| a | a | a | a |   b: ['static_2']
| ------------- |
| a | a | b | b |
| a | a |   |   |
```

Most importantly the `static` workload still maintains an optimal placement. The two `burst` workloads now share the
remainder of the compute resources.  The sharing mechanism here is not defined by `titus-isolate`.  The `titus-executor`
has already applied the CFS shares mechanism to provide fair sharing within the confines of the burst footprint.

The scenario above shows the allocation operating in a mode in which the `OversubscribeFreeThreadProvider` is operating 
as conservatively as possible.  The `static` workload is exceeding a CPU usage threshold which guarantees that its 
neighboring hyper-threads and its own occupied hyper-threads do not mingle with the `burst` pool.  However there is an 
opportunity for efficiency here.  If the `static` workload were not using its CPU resources it would be more efficient 
to temporarily donate access to its hardware resources while CPU usage was low.  Below we see this case in which the 
`static` workload's CPU usages is below a configurable threshold.

```
| a | a | b | b |   a: ['burst0_4', 'burst1_4', 'static_2']
| b | b | b | b |   b: ['burst0_4', 'burst1_4']
| ------------- |
| b | b | b | b |
| b | b | b | b |
```

Here we see that the `burst` workloads are given access to _every_ thread.  The `static` workload continues to be
limited to a subset which adheres to its request.

## Operations
`titus-isolate` provides a few read only endpoints to observe the operation of the server.

### Workloads
```
GET /workloads
```
This endpoint provides the `id`, `type` burst or static and `thread count` requested by a workload.
```bash
$ curl -s localhost:5555/workloads | jq
[
  {
    "id": "faddffa5-4227-4d67-a62b-dc4f1c2a07d1",
    "type": "static",
    "thread_count": 1
  }
]
```

### CPU
```
GET /cpu
```
This endpoint describes the structure of the CPU as well as the ids of the static workloads which have claimed particular threads.
```bash
$ curl -s localhost:5555/cpu | jq
{
  "packages": [
    {
      "id": 0,
      "cores": [
        {
          "id": 0,
          "threads": [
            {
              "id": 0,
              "workload_id": ["faddffa5-4227-4d67-a62b-dc4f1c2a07d1"]
            },
            {
              "id": 4,
              "workload_id": []
            }
          ]
        },
        ...
        {
          "id": 3,
          "threads": [
            {
              "id": 3,
              "workload_id": [] 
            },
            {
              "id": 7,
              "workload_id": []
            }
          ]
        }
      ]
    }
  ]
}
```

### Violations
```
GET /violations
```
This endpoint reports information regarding sub-optimal mapping of workloads to threads.  Two violation types are reported: `cross package` and `shared_core`.
* `cross package` indicates that a workload has been assigned threads on more than one package.
* `shared core` indicates that a physical core is being shared by more than one workload.

In the example output below carefully chosen static workload sizes were chosen to force violations.
```bash
$ curl -s localhost:5555/violations | jq
{
  "cross_package": {
    "elastic_poitras": [
      0,
      1
    ]
  },
  "shared_core": {
    "0:3": [
      "cranky_wright",
      "elastic_poitras"
    ],
    "1:1": [
      "heuristic_kapitsa",
      "elastic_poitras"
    ],
    "1:3": [
      "tender_sinoussi",
      "elastic_poitras"
    ]
  }
}
```

Cross package violations are a list of key/value pairs where key and value are as follows.
* key: workload id
* value: and a list of package ids respectively.

In the example above the workload `elastic_poitras` is running on packages `0` and `1`.

Shared core violations are a list of key/value pairs where key and value are as follows.
* key: <package_id>:<core_id>
* value: [workload_id...]

In the example above core `3` on package `0` has two workloads on it: `cranky_wright` and `elastic_poitras`.

### Workload Manager Status
```
GET /workload_manager/status
```
The workload manager is the core event processing and update generating component of `titus-isolate`.  We expose a status endpoint in order to inspect its status.
```bash
$ curl -s localhost:5555/status | jq
{
  "workload_manager": {
    "removed_count": 9,
    "error_count": 0,
    "added_count": 13,
    "success_count": 44,
    "workload_count": 4
  },
  "event_manager": {
    "error_count": 0,
    "processed_count": 63,
    "success_count": 189,
    "queue_depth": 0
  }
}

```

The workload manager is constantly processing a queue of events for adding, removing and re-balancing workloads. 
* queue depth: goes to zero very quickly in a properly operating system
* success count: a count of the number of events it has processed successfully
* error count: indicates how many events it failed to process

## Build a Debian package

First build the docker image used as a build environment.
```bash
$ docker build -t deb release/
```

Then return to the root of the source code and run an instance of the image.
```bash
$ docker run --rm -v $PWD:/src deb:latest
Removing old debs
Removing dist directory
Setting up virtualenv (env)
...
dpkg-buildpackage: full upload (original source is included)
Copying debian package to host
$ ls titus-isolate_*
titus-isolate_0.SNAPSHOT-1_all.deb
```

The result is a debian package that when installed creates the elements needed for instantiating a virtual environment with
all needed dependencies and scripts. For example one could execute the server as follows.
```bash
$ sudo dpkg -i titus-isolate_0.SNAPSHOT-1_all.deb
$ /usr/share/python/titus-isolate/bin/titus-isolate
05-11-2018:19:01:21,265 INFO [titus-isolate:22] Modeling the CPU...
05-11-2018:19:01:21,307 INFO [titus-isolate:26] Setting up the workload manager...
...
```
