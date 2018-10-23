import time

DEFAULT_TIMEOUT_SECONDS = 3


def wait_until(func, timeout=DEFAULT_TIMEOUT_SECONDS, period=0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if func():
            return
        time.sleep(period)

    raise TimeoutError(
        "Function did not succeed within timeout: '{}'.".format(timeout))
