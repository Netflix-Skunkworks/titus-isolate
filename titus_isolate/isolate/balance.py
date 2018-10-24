from titus_isolate.isolate.detect import get_cross_package_violations, get_shared_core_violations


def has_better_isolation(cur_cpu, new_cpu):
    """
    Here we determine whether a proposed placement of workloads improves upon the current workload placement.

    There are two possible violations:
       1. shared_core: a core is shared by multiple workloads
       2. cross_package: a workload is placed on multiple packages

    Below we describe a matrix answering the follow question: The new workload placement is better?

    There are 9 possible cases to consider.
        '-' indicates a decrease
        '0' indicates no change
        '+' indicates an increase
        'count' refers to how many workloads are affected by the violation



                                    shared_core_count
                                    -      0      +

                                -   T      T      T


            cross_package_count 0   T      F      F


                                +   F      F      F


        Only two controversial answers exist.  They are in the lower-left and upper-right hand corners.

            lower-left: shared_core_count has decreased, but cross_package_count has increased
            upper-right: cross_package_count has decreased, but shared_core_count has increased

        In both cases we make the assumption that avoiding cross package workloads is to be preferred.

    NOTE: We do not consider the placement of burst workloads when comparing the two placement options.

    :return: True if the new_cpu has better placement, False otherwise
    """
    cur_cross_package_violation_count = len(get_cross_package_violations(cur_cpu))
    new_cross_package_violation_count = len(get_cross_package_violations(new_cpu))

    cur_shared_core_violation_count = len(get_shared_core_violations(cur_cpu))
    new_shared_core_violation_count = len(get_shared_core_violations(new_cpu))

    # More violations is bad, so a positive change is bad
    cross_package_violation_change = new_cross_package_violation_count - cur_cross_package_violation_count
    shared_core_violation_change = new_shared_core_violation_count - cur_shared_core_violation_count

    # Top row of matrix
    if cross_package_violation_change < 0:
        return True

    # Bottom row of matrix
    if cross_package_violation_change > 0:
        return False

    # Middle row of matrix, can assume cross_package_violation_change == 0
    return shared_core_violation_change < 0

