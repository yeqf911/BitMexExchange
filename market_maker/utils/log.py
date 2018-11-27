import logging
from market_maker import settings


def setup_custom_logger(name, log_level=settings.LOG_LEVEL):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
