import logging
from functools import lru_cache
from logging.config import dictConfig


@lru_cache
def setup_logging():
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "app": {"handlers": ["console"], "level": "INFO", "propagate": False}
        },
        "root": {"handlers": ["console"], "level": "INFO"},
    }

    dictConfig(log_config)


def get_logger() -> logging.Logger:
    setup_logging()
    return logging.getLogger("app")
