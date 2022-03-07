FROM python:3.9-slim

COPY . /opt/aimaas
RUN pip3 install -r /opt/aimaas/requirements.txt; \
    pip3 cache purge

WORKDIR /opt

ENV WORKERS=1
ENV ROOT_PATH=/

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "-c", "uvicorn aimaas.main:app --port 8000 --host 0.0.0.0 --workers ${WORKERS} --root-path ${ROOT_PATH}"]
