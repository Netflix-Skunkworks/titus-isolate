import collections


class PmcSubscriber:
    def __init__(self):
        self.q = collections.deque()

    def handle_nowait(self, metric):
        self.q.appendleft(metric)
