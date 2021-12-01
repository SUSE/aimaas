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

This project is currently under active development.

## Contributing

Right now anyone can contribute by defining requirements or submitting pull requests.

# Getting started

We assume that interested parties are familiar with Python, JavaScript, FastAPI and NodeJs.

## Setup
In a nutshell these are the steps to set up a development environment:

1. Install PostgreSQL.
2. Create a database.
3. Create a config file: `.env`.
4. Create a Python virtualenv.
5. Install Python dependencies with `pip`.
6. Run database migrations: `alembic upgrade head`.

## Cheat Sheet

This is a collection of helpful links:

* [Create database migration](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
