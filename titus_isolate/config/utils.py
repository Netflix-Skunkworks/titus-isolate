from titus_isolate import log
from titus_isolate.config.constants import CPU_ALLOCATORS, CPU_ALLOCATOR_CLASS_MAP


def get_cpu_allocator_index(cpu_allocator_name):
    index = -1
    try:
        name = CPU_ALLOCATOR_CLASS_MAP.get(cpu_allocator_name, None)
        if name is None:
            log.error("Unknown allocator name mapping for: '{}'".format(cpu_allocator_name))
            return index

        index = CPU_ALLOCATORS.index(name)
    except:
        log.warn("Failed to find allocator index for: '{}', reporting: '{}'".format(cpu_allocator_name, index))

    return index
