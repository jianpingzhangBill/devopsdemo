#from public.ecr.aws/docker/library/python:3.11
#from 731045533415.dkr.ecr.us-west-2.amazonaws.com/devops/ubuntu/python 
#from public.ecr.aws/docker/library/python:3.11-bookworm
FROM python:3.11-slim-buster

WORKDIR /app

# Install dependencies.
RUN apt update && apt-get install xmlsec1 libxmlsec1-openssl -y && apt clean
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip3 install -r requirements.txt
RUN pip install cython grpcio flask 

# Copy the source code
COPY docker/gunicorn.conf.py .
COPY src/ .
COPY otel-auto-instrumentation-python /otel-auto-instrumentation-python
EXPOSE 5000
ENTRYPOINT ["gunicorn", "app:create_app()"]

# from 731045533415.dkr.ecr.us-west-2.amazonaws.com/devconsolebe:test2-46f29f3


#copy app.py /app.py
#expose 8000
#cmd python /app.py 
