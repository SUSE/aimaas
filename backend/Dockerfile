FROM python:3.12-slim

COPY . /opt/aimaas/backend
RUN pip3 install -r /opt/aimaas/backend/requirements.txt; \
    pip3 cache purge

WORKDIR /opt/aimaas

ENV WORKERS=1
ENV ROOT_PATH=/
ENV ALEMBIC_CONFIG=/opt/aimaas/backend/alembic/alembic.ini

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "-c", "uvicorn backend.main:app --port 8000 --host 0.0.0.0 --workers ${WORKERS} --root-path ${ROOT_PATH}"]
