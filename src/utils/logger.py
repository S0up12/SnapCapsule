import logging
import os
import sys

_LOGGER_NAME = "snapcapsule"
_CONFIGURED = False

_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def _resolve_level(level):
    if isinstance(level, int):
        return level
    name = (level or os.getenv("SNAPCAPSULE_LOG_LEVEL", "INFO")).upper()
    return _LEVELS.get(name, logging.INFO)


def configure_logging(level=None):
    """Configure the shared logger once with a predictable format."""
    global _CONFIGURED
    logger = logging.getLogger(_LOGGER_NAME)
    if _CONFIGURED:
        if level is not None:
            logger.setLevel(_resolve_level(level))
        return logger

    logger.setLevel(_resolve_level(level))
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    _CONFIGURED = True
    return logger


def get_logger(name=None):
    configure_logging()
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


def set_log_level(level):
    logger = configure_logging(level)
    logger.setLevel(_resolve_level(level))


def debug(msg, *args, **kwargs):
    get_logger().debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    get_logger().info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    get_logger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    get_logger().error(msg, *args, **kwargs)


def exception(msg, *args, **kwargs):
    get_logger().exception(msg, *args, **kwargs)
