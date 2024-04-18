import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging(level: str):
    logging.captureWarnings(True)

    handler = logging.StreamHandler(stream=sys.stdout)
    logfmt = "%(asctime)s [%(name)s] %(funcName)s - %(lineno)d - %(levelname)s: %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%SZ"

    formatter = jsonlogger.JsonFormatter(
        fmt=logfmt,
        datefmt=datefmt,
        json_ensure_ascii=False,
        rename_fields={
            "asctime": "log_time",
            "levelname": "level",
            "message": "content",
            "funcName": "func",
            "otelTraceID": "TraceId",
            "otelSpanID": "SpanId",
        },
    )
    handler.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=[handler])
