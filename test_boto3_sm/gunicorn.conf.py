# https://docs.gunicorn.org/en/stable/settings.html#settings
from logging import Filter

bind = "0.0.0.0:8000"
worker_class = "gevent"
workers = 1
access_log_format = (
    'Got request from %(h)s(refeerer %(f)s, user agent %(a)s) -> "%(r)s", '
    "and return response[%(s)s](cost time: %(M)sms)"
)


class HealthCheckFilter(Filter):
    def filter(self, record) -> bool:
        if record.args["U"] == "/health_check":
            return False
        else:
            return True


logconfig_dict = {
    "version": 1,
    "formatters": {
        "generic": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "[%(levelname)s] func=%(name)s.%(funcName)s|content=%(message)s",
            "timestamp": "logtime",
            "rename_fields": {"levelname": "level", "funcName": "function", "message": "content"},
        }
    },
    "filters": {"healthcheck_filter": {"()": HealthCheckFilter, "name": ""}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "gunicorn.access": {
            "propagate": True,
            "filters": ["healthcheck_filter"],
        },
        "gunicorn.error": {"propagate": True},
        "botocore": {"propagate": False},
        "elasticsearch": {"propagate": False},
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
    "incremental": False,
    "disable_existing_loggers": True,
}
