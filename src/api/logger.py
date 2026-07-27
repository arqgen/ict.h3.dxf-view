import logging
import sys

import colorlog

_LEVEL_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}


def _build_logger() -> logging.Logger:
    instance = logging.getLogger("cad_viewer")
    if instance.handlers:
        return instance

    handler = colorlog.StreamHandler(stream=sys.stdout)
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(asctime)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
            log_colors=_LEVEL_COLORS,
        )
    )

    instance.addHandler(handler)
    instance.setLevel(logging.DEBUG)
    instance.propagate = False
    return instance


logger = _build_logger()
