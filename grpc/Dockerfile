FROM --platform=linux/amd64 python:3.10

LABEL maintainer="IBM Research Europe - Ireland" \
    name="IBM Forecasting GRPC Server" \
    summary="GRPC Server for MORE Forecasting tools" \
    vendor="IBM Corp."

ENV PYTHONPATH="${PYTHONPATH}:/service"

## install only the service requirements
COPY requirements.txt /service/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade -r /service/requirements.txt

## add all the rest of the code
ADD serving /service/serving

## add config files
ADD configs /service/configs

## Set working directory
WORKDIR /service

## ENTRYPOINT
ENTRYPOINT ["python", "serving/grpc_server.py"]
