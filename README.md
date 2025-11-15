# Rapid Street Assessment Tool

## Overview

Rapid Street Assessment (RSAs) are designed to provide quick, comprehensive analysis of street and land use data - using USRNs (Unique Street Reference Numbers).

### Backend (FastAPI)

- RESTful API endpoints:
  - `/street-info-llm`: Summary of network and RAMI data
  - `/land-use-info-llm`: Summary of Land use and building information

## Data Sources

- Ordnance Survey National Geographic Database (NGD)
- Supports multiple OS data collections:
  - RAMI (Routing and Asset Management Information)
  - Network data
  - Land use data
