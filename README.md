## Introduction

`titus-isolate` applies isolation primitives to workloads running on a given agent in an attempt to control the impact of "noisy neighbors" depending on user requirements.

## Install Dependencies

First we setup a virtual environment.
```bash
$ virtualenv env
New python executable in <OMITTED>
Installing setuptools, pip, wheel...done.
```

Then we install our dependencies.
```bash
$ pip3 install -r requirements.txt
...
Installing collected packages: click, idna, certifi, chardet, urllib3, requests, six, docker-pycreds, websocket-client, docker
Successfully installed certifi-2018.10.15 chardet-3.0.4 click-7.0 docker-3.5.1 docker-pycreds-0.3.0 idna-2.7 requests-2.20.0 six-1.11.0 urllib3-1.24 websocket-client-0.53.0
```

See `Usage` for starting the `titus-isolate` server.

## Usage
In order to use `titus-isolate` two componentes must cooperate.  A server subscribes to events from Docker and workloads adhere to a container labeling convention.

### Server

The server must be started with three arguments indicating the structure of the CPU which workloads will consume.
```bash
$ python3 ./run.py --help
Usage: run.py [OPTIONS]

Options:
  --package-count TEXT        The number of packages in the CPU
  --cores-per-package TEXT    The number of cores per package
  --threads-per-core INTEGER  The number of threads per core
  --help                      Show this message and exit.
```

On linux the required information can normally be found using `lscpu`.
```bash
$ lscpu
...
CPU(s):                64
On-line CPU(s) list:   0-63
Thread(s) per core:    2
Core(s) per socket:    16
Socket(s):             2
...
```

Using this information we should start `titus-isolate` as follows.
```bash
$ python3 ./run.py --package-count 2 --cores-per-package 16 --threads-per-core 2
30-10-2018:11:28:45,934 INFO [run.py:35] Modeling the CPU...
30-10-2018:11:28:45,934 INFO [run.py:39] Setting up the workload manager...
30-10-2018:11:28:45,935 INFO [workload_manager.py:16] Created workload manager
30-10-2018:11:28:45,935 INFO [run.py:44] Setting up the Docker event handlers...
30-10-2018:11:28:45,935 INFO [run.py:51] Starting Docker event handling...
30-10-2018:11:28:45,948 INFO [run.py:55] Isolating currently running workloads...
30-10-2018:11:28:45,961 INFO [run.py:58] Startup complete, waiting for events...
...
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

The placement algorithm is very simple.  It attempts to place static workloads entirely on a single package if possible and consume whole physical cores.
```
get_processors(processor_count):
	processor_ids = []
	
	# Return an empty list if no processors were requested
	if processor_count == 0:
		return processor_ids

    p = get_emptiest_package()

    while processor_count > 0 and not is_full(p):
	    core = get_emptiest_core(p)
		empty_processors = get_empty_processors(core)
		
		# Update the package’s capacity
		consume_processors(p, empty_processors)
 
		# Record the processors to be allocated
        processor_ids + empty_processors
		processor_count -= len(empty_processors)

	return processor_ids + get_processors(processor_count)
```

After all placements have been made for workloads arriving on the Docker event stream a rebalance operaation is performed.  It sorts all static workloads from largest to smallest based on their declared CPU requiremetns and runs the algorithm on each in turn.  Burst workloads get the remaining CPU capacity.
Needless migration of workloads is avoided by only applying the outcome of the rebalance operation if some improvement in placement is detected.  An improvement is detected when cross package workload placement and the number of shared physical cores is minimized.
