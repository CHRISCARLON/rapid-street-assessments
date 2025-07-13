# Rapid Street Assessment Tool

## Overview

Rapid Street Assessment (RSAs) are designed to provide quick, comprehensive analysis of street and land use data - using USRNs (Unique Street Reference Numbers).

It consists of a Python backend using Robyn framework.

## Core Features

### 1. Street Information Analysis

- Fetches and analyses street network data and special designations
- Provides detailed information about:
  - Street characteristics
  - Special designations and restrictions
  - Engineering difficulties
  - Traffic sensitivity
  - Street Manager Aggregated Stats
- Uses chat gpt-4o mini to generate human-readable analysis of the technical data

### 2. Land Use Analysis

- Retrieves and processes land use and building data
- Provides insights about:
  - Property types and distributions
  - Land use categories
  - Total area statistics
  - Building characteristics
- Uses chat gpt-4o mini to generate human-readable analysis of the technical data

### 3. Collaborative Street Works Analysis

- Retrieves and processes street manager data, street information and land use data and combines them into a single object,
- Merges insight from land use and street informatioon to provide a recommendation for collaborative street works
- Uses chat gpt-4o mini to generate human-readable analysis of the technical data

## Technical Architecture

### Backend (Robyn)

- RESTful API endpoints:
  - `/street-info` and `/street-info-llm`: Summary of network and RAMI data as well as street manager stats
  - `/land-use-info` and `/land-use-info-llm`: Summary of Land use and building information
  - `/collaborative-street-works-llm`: Collaborative street works recommendation endpoint
- Asynchronous processing of multiple OS NGD API calls
- Intelligent data filtering and data aggregation
- Integration with OpenAI's chat gpt-4o mini for data interpretation

### Key Dependencies

- Python ≥3.11
- Robyn (API framework)
- LangChain (AI processing)
- MotherDuck (data storage)

## Data Sources

- Ordnance Survey National Geographic Database (NGD)
- Supports multiple OS data collections:
  - RAMI (Routing and Asset Management Information)
  - Network data
  - Land use data
- Street Manager data
