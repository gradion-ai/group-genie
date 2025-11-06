import logging
from contextlib import contextmanager
from logging import Formatter, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Iterator


@contextmanager
def configure_logging(
    format: str = "%(asctime)s %(levelname)s %(name)s: %(message)s",
    levels: dict[str, int] | None = None,
) -> Iterator[None]:
    listener = setup_logging(format, levels)
    yield
    shutdown_logging(listener)


def setup_logging(
    format: str,
    levels: dict[str, int] | None = None,
) -> QueueListener:
    """Set up asyncio-safe logging.

    Args:
        format: Format string for the logger.
        config: Dict mapping logger names to logging levels.
                Defaults to {"group_genie": logging.INFO}

    Returns:
        QueueListener instance - caller must call shutdown_logging() on application exit
    """
    levels = levels.copy() if levels else {}

    if "group_genie" not in levels:
        levels["group_genie"] = logging.INFO

    formatter = Formatter(format)

    stream_handler = StreamHandler()
    stream_handler.setFormatter(formatter)

    queue = Queue()  # type: ignore
    queue_handler = QueueHandler(queue)
    queue_listener = QueueListener(queue, stream_handler)

    for name, level in levels.items():
        logger = logging.getLogger(name)
        logger.addHandler(queue_handler)
        logger.setLevel(level)

    queue_listener.start()
    return queue_listener


def shutdown_logging(listener: QueueListener):
    """Gracefully shut down the logging queue listener.

    Args:
        listener: The QueueListener instance returned by setup_logging()
    """
    listener.stop()
