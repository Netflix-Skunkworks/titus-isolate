import logging


def config_logs(level=logging.INFO):
    logging.basicConfig(
        format='%(asctime)s,%(msecs)d %(levelname)s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%d-%m-%Y:%H:%M:%S',
        level=level)
