# Abstract Information Management and Authority Service (_aimaas_) 

_aimaas_ aims to be a central authoritative web service for information management. Main aspects in
(future) development are:

* [EAV](https://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model) data model
* Modular architecture
* Easy to use interfaces for humans (WebUI) and machines (API)
* Role-based permission management
* Traceability of information changes

For more details on _aimaas_ see: 
[Philosophy & Architecture](https://github.com/SUSE/aimaas/wiki/Philosophy-&-Architecture).

## Status

This project is currently under _active development_.

# Getting started

We assume that interested parties are familiar with Python, JavaScript, FastAPI and NodeJs.

## Setup
In a nutshell, these are the steps to set up a development environment:

1. Install PostgreSQL.
2. Create a database.
3. Backend
   1. Create a file with environment variable definitions (See [config.py](backend/config.py) for 
      which variables are available/required).
   2. Create a Python virtualenv (Our suggestion: Python 3.12).
   3. Install Python dependencies with `pip`.
   4. Run database migrations: `alembic upgrade head`.
4. Frontend
   1. Install `npm` (and `nodejs`, our suggestion: v20).
   2. Install JS dependencies with `npm install`.

### Updating NPM packages

The safe way to update packages is to run:

```shell
npm update
```

If you want to upgrade more aggressively (i.e. potentially introduce breaking changes) you can 
consider something like this:

```shell
npm install ---no-save npm-check-updates
ncu --upgrade
npm install
```

## Running development servers

### Backend

Having set up the Python backend as described you should now be able to run the backend with this 
command:

```shell
uvicorn backend.main:app --reload  # --env-file <path_to_your_envfile>
```

**Note**: The `--env-file` argument is not required, if your env. file is stored in the project root
directory.

This will run the backend on `localhost:8000`.

### Frontend

Having set up the NodeJS frontend as described you should now be able to run the frontend with this
command:

```shell
cd frontend
npm run dev
```

This will run the frontend on `localhost:5173`.

**Note**: The dev server is configured to proxy API requests to `localhost:8000` by default. If your
backend development server is listening somewhere else, make sure to adjust the proxy target in 
[vite.config.js](frontend/vite.config.js)!

## Building production images

In order to build a production-ready container images you can simply run:

```shell
make all
```

The resulting images can be started like this:

```shell
docker run \
  -d \                                 # Demonize
  --restart unless-stopped \           # Automatically restart
  --name aimaas_ui \                   # Easy to remember name
  aimaas-ui:latest \                   # Our container image

docker run \
  -d \                                 # Demonize
  --restart unless-stopped \           # Automatically restart
  --env-file <path_to_your_envfile> \  # Use the config
  --name aimaas_api \                  # Easy to remember name
  aimaas-api:latest \                  # Our container image
  --workers 4                          # Parameters for `uvicorn`
  --root_path /api
```

**Caveat**: This obviously requires that `make` and `docker` are installed.

**Caveat**: A central assumption is, that the backend is reachable via the same base URL as the 
frontend, e.g. if the frontend is available at `http://example.com/`, the backend is expected at 
`http://example.com/api/`. For the development environment a reverse proxy is pre-configured. On 
production, this needs to be handled explicitly!

## Cheat Sheet

This is a collection of helpful links:

* [Create database migration](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)

# Contributing

Right now anyone can contribute by defining requirements or submitting pull requests.
