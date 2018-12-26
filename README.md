## Introduction

`titus-isolate` applies isolation primitives to workloads running on a given agent in an attempt to control the impact of "noisy neighbors" depending on user requirements.

## Install Dependencies

First we setup a virtual environment.
```bash
$ virtualenv env
New python executable in <OMITTED>
Installing setuptools, pip, wheel...done.
$ . env/bin/activate
```

Then we install the package.
```bash
$ python3 setup.py install
running install
running build
running build_py
running build_scripts
running install_lib
running install_scripts
changing mode of <OMITTED>/titus-isolate/venv/bin/titus-isolate to 755
changing mode of <OMITTED>/titus-isolate/venv/bin/main.py to 755
running install_egg_info
Removing <OMITTED>/titus-isolate/venv/lib/python3.7/site-packages/titus_isolate-0.SNAPSHOT-py3.7.egg-info
Writing <OMITTED>/titus-isolate/venv/lib/python3.7/site-packages/titus_isolate-0.SNAPSHOT-py3.7.egg-info
```

See `Usage` for starting the `titus-isolate` server.

## Usage
In order to use `titus-isolate` two components must cooperate.  A server subscribes to events from Docker and workloads adhere to a container labeling convention.

### Server

The server must be started with three arguments indicating the structure of the CPU which workloads will consume.
```bash
$ titus-isolate --help
Usage: titus-isolate [OPTIONS]

Options:
  --admin-port INTEGER  The port for the HTTP server to listen on (default:
                        5000)
  --help                Show this message and exit.
```

The server will automatically determine the topology of the CPU on which it is running.  It supports MacOS and Linux systems today.
It requires that the python method `platform.system()` return either `Darwin` or `Linux`.  For example:

```bash
$ python
Python 3.7.0 (default, Oct  2 2018, 09:20:07)
[Clang 10.0.0 (clang-1000.11.45.2)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import platform
>>> platform.system()
'Darwin'
```

### Workloads
Workloads must indicate that they are opting into isolation by the `titus-isolate` component.  They do this through the Docker conatainer label mechanism.

Workloads must provide two pieces of information: number of "cpus" and workload type.
* cpus: an integer indicating an abstract amount of processing capacity which may refer to threads or cores depending on the underlying hardware.
* type: one of either "static" or "burst"

This information is provided using the following labels: `com.netflix.titus.cpu` and `com.netflix.titus.workload.type`.

If a `titus-isolate` server is already running on the current host we could add a workload as follows.
```bash
$ docker run --rm -l com.netflix.titus.cpu=2 -l com.netflix.titus.workload.type=static ubuntu:latest sleep 30
```

We should expect to see logs like the following emitted by the server.
```
30-10-2018:18:40:16,789 INFO [workload_manager.py:30] Adding workloads: ['frosty_swartz']
30-10-2018:18:40:16,791 INFO [cpu.py:16] Assigning '2' thread(s) to workload: 'frosty_swartz'
30-10-2018:18:40:16,791 INFO [cpu.py:29] Claiming package:core:thread '0:0:0' for workload 'frosty_swartz'
30-10-2018:18:40:16,791 INFO [cpu.py:29] Claiming package:core:thread '0:0:32' for workload 'frosty_swartz'
30-10-2018:18:40:16,791 INFO [update.py:15] workload: 'frosty_swartz' updated threads from: '[]' to: '[0, 32]'
30-10-2018:18:40:16,791 INFO [workload_manager.py:93] Found footprint updates: '{'frosty_swartz': [0, 32], 'burst': [1, 33, 2, 34, 3, 35, ... 30, 62, 31, 63]}'
...
```

Above we see that the launched static workload is assigned two particular threads: `0` and `32` and generates updates indicating that the pool of threads available for burst workloads has changed.

## Isolation

### CPU
The first isolation primitive to be applied is the CPU affinity capability enabled by the [`cpusets` cgroup](https://www.kernel.org/doc/Documentation/cgroup-v1/cpusets.txt).

Workloads are categorized into either static or burst categories.  Each choice of workload type comes with a cost/benefit trade off.
* static
	* benefit: the workload will be isolated to the greatest possible, leading to more consistent performance
	* cost: the workload opts out of consuming unallocated CPU capacity
* burst
	* benefit: the workload may consume unallocate CPU capacity
	* cost: the workload opts in to less isolation from other workloads, and will see greater variance in performance depending on CPU usage

Each static workload is assigned a set of threads to which they have exclusive access.  All burst workloads share all those threads which are not claimed by static workloads.

The primary placement algorithm is implemented in `titus-optimize` and relies on solving an integer program. Please refer to `titus-optimize`
for further details.
Once all the static workloads have been placed, burst workloads get the remaining CPU capacity.

## Test
We use `tox` to run tests.  After setting up a virtual environment, requirements and `tox` must be installed.
```bash
(venv) $ pip3 install -r requirements.txt
(venv) $ pip3 install tox
(venv) $ tox
...
```

## Operations
`titus-isolate` provides a few read only endpoints to observe the operation of the server.

Unless otherwise stated, in the following examples we started the `titus-isolate` server with the following options.
```bash
$ ./main.py --package-count 1 --cores-per-package 4 --threads-per-core 2 --admin-port 5555
```
One workload was started as follows.
```bash
$ docker run --rm -l com.netflix.titus.cpu=1 -l com.netflix.titus.workload.type=static ubuntu:latest sleep 30
```

### Workloads
```
GET /workloads
```
This endpoint provides the `id`, `type` burst or static and `thread count` requested by a workload.
```bash
$ curl -s localhost:5555/workloads | jq
[
  {
    "id": "pedantic_hermann",
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
              "workload_id": "pedantic_hermann"
            },
            {
              "id": 4,
              "workload_id": null
            }
          ]
        },
        ...
        {
          "id": 3,
          "threads": [
            {
              "id": 3,
              "workload_id": null
            },
            {
              "id": 7,
              "workload_id": null
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
