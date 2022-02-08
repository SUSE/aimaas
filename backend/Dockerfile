FROM python:3.9-slim

COPY . /opt/aimaas
RUN pip3 install -r /opt/aimaas/requirements.txt; \
    pip3 cache purge

WORKDIR /opt
EXPOSE 8000
ENTRYPOINT ["uvicorn", "aimaas.main:app", "--port", "8000", "--host", "localhost"]
