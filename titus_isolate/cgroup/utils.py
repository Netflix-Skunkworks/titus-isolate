def extract_cpuset_path(cpuset_list_str):
    rows = cpuset_list_str.split()
    for row in rows:
        r = row.split(":")
        name = r[1]
        path = r[2]

        if name == "cpuset":
            return path

    return None
