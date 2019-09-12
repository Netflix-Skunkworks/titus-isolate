def get_threads(cpu, workload_id):
    return [t.get_id() for t in cpu.get_threads() if workload_id in t.get_workload_ids()]
