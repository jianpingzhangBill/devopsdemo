# https://docs.gunicorn.org/en/stable/settings.html#


workers = 1
worker_class = "gevent"
bind = "0.0.0.0:8000"
