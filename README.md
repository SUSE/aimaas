# Abstract Information Management and Authority Service (aimaas) 

aimaas aims to be a central authoritative web service for information management. Main aspects in
(future) development are:

* [EAV](https://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model) data model
* Modular architecture
* Easy to use interfaces for humans (WebUI) and machines (API)
* Role-based permission management
* Traceability of information changes

## What does this mean?

Are you familiar with [PIM](https://en.wikipedia.org/wiki/Product_information_management) systems 
for eCommerce? They are central hubs for product information and related media. They can be the
primary authority for this information or an intermediary between systems providing the data (e.g. a
company's internal system) and system consuming the data (e.g. a webshop on the internet).

Did you notice the limitation to *product* information? What if we want to manage information of
different types, say additional *product bundles*? This is where the **abstract** comes into play.
aimaas wants to allow users to define their own object types with different attributes and value 
types in a traceable way.

Think of aimaas as an abstraction of an SQL database where traceability information is also inside
the database instead of log files.

## Status

This project is currently in the initial planning phase.

## Contributing

Right now anyone can contribute by defining requirements.
