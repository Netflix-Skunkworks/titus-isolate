# ARCHIVED - `titus-isolate`

## Introduction

`titus-isolate` enables the isolated and efficient use of compute resources in a multi-tenant container environment.
Given a machine hosting multiple containers, `titus-isolate` partitions the available compute hardware (hyper-threads) 
to achieve isolation and efficiency goals.

In general greater cost efficiency implies less isolation and vice-versa. To achieve maximal isolation workloads 
(containers) could each be running on their own dedicated machine, at the cost of great inefficiency.  On the other hand,
to achieve maximal efficiency, many containers (thousands) could be run on the same machine, but at the cost of high
interference and poor performance.

## Isolation

The core mechanism which enables compute isolation is to partition access to sets of hyper-threads on a per workload basis.
This is accomplished by manipulation of the [`cpusets` cgroup](https://www.kernel.org/doc/Documentation/cgroup-v1/cpusets.txt)
	
Choosing an efficient and performant partitioning of CPU resources is not a perfectly solvable problem.  `titus-isolate`
delegates the choice of cpusets to a remote gRPC service, which is called through the `GrpcRemoteIsolationAllocator` client,
a specialized kind of `CpuAllocator`. This remote service runs a MIP solver and come up with a placement proposal maximizing overall
isolation and efficiency (balanced usage of hyper-threads, minimal overlap between cpusets etc.).

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

```
GET /cpu_viz
```
This endpoint prints out a human readable ascii cpu diagram with the current tasks.
```bash
$ curl -s localhost:5555/cpu_viz
| a | a | a | a |   a: ['burst0_4', 'burst1_4']
| a | a | a | a |   b: ['static_2']
| ------------- |
| a | a | b | b |
| a | a |   |   |
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

### Specifying custom placement constraints
For debugging purposes or experiments, it might be useful to specify custom constraints to the placement oof the containers one wants.
`titus-isolate` and its remote service counterpart offer an API to do so. Note that this mode of operation is only designed for manual
one-off interventions on specific machines by responsible users and in particular should **NOT** be automated against.

If a file is present at `/opt/venvs/titus-isolate/constraints.json` on the Titus agent, it will be parsed and the constraints defined
in this file will be added to every isolation request submitted to the service. It is not necessary to restart the `titus-isolate` unit, 
as this file is read every time a request is submitted.

The content of this file has to be a valid `json` representation of the `Constraints` protobuf API defined at `allocate/remote/isolate_pb2.py`.
If the file is invalid, its content will be ignored, and a stack trace will be reported in `titus-isolate` logs.

Here is an example of such file:
```json
{
    "antiAffinities": [
        {
            "first_task": "a",
            "second_task": "*"
        }
    ],
    "cotenancies": [
        {
            "target_task": "b",
            "co_tenant_tasks": ["c", "d"]
        },
        {
            "target_task": "e",
            "prct_slack_occupied": 30.0
        }
    ],
    "maxCoresToUsePerPackage": 21
}
```
#### Anti-affinity
For a given target task, one can specify which tasks should not have overlapping cpusets with it. Specifying * means "No other task should overlap with me" (ie: no oversubscription).
In the above example, we want Titus task `a` to have guaranteed dedicated cpus.

#### Co-Tenancy
##### Percent Slack Occupied
For a given target task (`e`) in the example above, the solver will try to find a combination of other tasks making use of the specified percentage of slack of the target task,
where slack is defined as `cgroup.limit - usage`.

##### Co-tenant tasks
For a given target task (victim, `b` in the example above), one can specify which specific other tasks (offenders: `c` and `d`) should overlap as much as possible with it. If an offender cpuset A is smaller or equal to the victim cpuset V, we will search for a solution such that A \in V. If the offender cpuset B is bigger than the victim, we will search a solution such that V \in B

#### Max cores to use per package
Allows to compress placements globally (and hence drive contention on the host) by avoiding any layout on a specified number of cores per socket.


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
