from __future__ import print_function

import logging

from bcc import BPF, PerfType, PerfHWConfig

# load BPF program
from titus_isolate.utils import get_logger

bpf_text = """
#include <linux/ptrace.h>
#include <uapi/linux/bpf_perf_event.h>

struct key_t {
    int cpu;
    int pid;
    char name[TASK_COMM_LEN];
};

BPF_HASH(ref_count, struct key_t);
BPF_HASH(miss_count, struct key_t);

static inline __attribute__((always_inline)) void get_key(struct key_t* key) {
    key->cpu = bpf_get_smp_processor_id();
    key->pid = bpf_get_current_pid_tgid();
    bpf_get_current_comm(&(key->name), sizeof(key->name));
}

int on_cache_miss(struct bpf_perf_event_data *ctx) {
    struct key_t key = {};
    get_key(&key);

    miss_count.increment(key, ctx->sample_period);

    return 0;
}

int on_cache_ref(struct bpf_perf_event_data *ctx) {
    struct key_t key = {};
    get_key(&key);

    ref_count.increment(key, ctx->sample_period);

    return 0;
}
"""

# The sample period designates how frequently the callback method will be called.  e.g. Every 100 cache miss events for
# a given pid will call the on_cache_miss function
SAMPLE_PERIOD = 100

log = get_logger(logging.DEBUG)


b = BPF(text=bpf_text)
try:
    b.attach_perf_event(
        ev_type=PerfType.HARDWARE, ev_config=PerfHWConfig.CACHE_MISSES,
        fn_name="on_cache_miss", sample_period=SAMPLE_PERIOD)
    b.attach_perf_event(
        ev_type=PerfType.HARDWARE, ev_config=PerfHWConfig.CACHE_REFERENCES,
        fn_name="on_cache_ref", sample_period=SAMPLE_PERIOD)
except:
    log.exception("Failed to attach to a hardware event. Is this a virtual machine?")
    exit()


def get_bpf():
    return b
