FROM public.ecr.aws/docker/library/python:3.11

WORKDIR /app
RUN apt update && apt install curl net-tools ncat -y
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
#RUN pip install opentelemetry-distro opentelemetry-exporter-otlp && opentelemetry-bootstrap -a install
COPY gunicorn.conf.py .
COPY src .

EXPOSE 8000
cmd ["python", "test.py"]
#CMD [ "gunicorn", "app:create_app()" ]
#CMD ["opentelemetry-instrument",  "gunicorn", "--config", "geventlet-config.py", "app:create_app()"]
# CMD ["opentelemetry-instrument",  "python", "demo.py"]
