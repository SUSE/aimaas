FROM python:3.9-slim

COPY . /opt/aimaas
RUN pip3 install -r /opt/aimaas/requirements.txt; \
    pip3 cache purge

WORKDIR /opt
EXPOSE 8000
ENV EXPOSED_HOST=localhost
ENTRYPOINT uvicorn aimaas.main:app --port 8000 --host $EXPOSED_HOST
