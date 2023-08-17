FROM --platform=linux/amd64 python:3.10

LABEL maintainer="IBM Research Europe - Ireland" \
    name="SAIL Docker Service" \
    summary="Docker-based container service for SAIL library" \
    vendor="IBM Corp."

ENV PYTHONPATH="${PYTHONPATH}:/service"

## install only the service requirements
COPY requirements.txt /service/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade -r /service/requirements.txt

## add all the rest of the code
ADD forecasting_service /service/forecasting_service

## Set working directory
WORKDIR /service

## ENTRYPOINT
ENTRYPOINT ["python", "forecasting_service/run.py"]
