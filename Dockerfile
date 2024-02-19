FROM --platform=linux/amd64 python:3.10

LABEL maintainer="IBM Research Europe - Ireland" \
    name="IBM Scalable IMLA Platform" \
    summary="Docker-based container service for experimenting with Incremental Machine Learning Algorithms (IMLA). It is build on top of IBM SAIL Python library." \
    vendor="IBM Corp."

ENV PYTHONPATH="${PYTHONPATH}:/service"

## install only the service requirements
COPY requirements.txt /service/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade -r /service/requirements.txt

# Needed for tensorboard logging via the torch framework
RUN python -m pip install torch --index-url https://download.pytorch.org/whl/cpu

## add all the rest of the code
ADD imla_platform /service/imla_platform

## Set working directory
WORKDIR /service

## ENTRYPOINT
ENTRYPOINT ["python", "imla_platform/run.py"]
