all: backend frontend

backend:
	bash -c "docker build -t aimaas-api:latest backend"

frontend:
	bash -c "docker build -t aimaas-ui:latest frontend"
