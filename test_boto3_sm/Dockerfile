FROM python:3.11-slim-buster

WORKDIR /app

# Install dependencies.
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy the source code
COPY app.py .
COPY gunicorn.conf.py .
COPY testapps/otel-auto-instrumentation-python /otel-auto-instrumentation-python
EXPOSE 8000
ENTRYPOINT ["gunicorn", "app:create_app()"]