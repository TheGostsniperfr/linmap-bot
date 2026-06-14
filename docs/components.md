# linmap-bot Components & Modules

This document details the decoupled **Core-API & Worker** pattern of the codebase.

## 1. System Components Diagram

```mermaid
graph TD
    subgraph Discord Worker [Discord Bot Pod]
        Bot["src/bot/discord_client.py (Discord Bot)"]
        Client["src/bot/api_client.py (httpx Client)"]
        Bot --> Client
    end

    subgraph FastAPI Core [FastAPI Core Pod]
        App["src/api/app.py (FastAPI App)"]
        Router["src/api/routers/roadmap.py (Roadmap Router)"]
        Config["src/config.py (Pydantic Config)"]
        
        subgraph Logic Engines
            Linear["src/linear/graphql_client.py (LinearClient)"]
            Excel["src/generator/excel.py (Excel Generator)"]
            Gantt["src/generator/timeline.py (Plotly Generator)"]
            Storage["src/storage/gdrive.py (Google Drive)"]
        end
        
        App --> Router
        Router --> Linear
        Router --> Excel
        Router --> Gantt
        Router --> Storage
    end

    Client -->|POST /api/v1/roadmap/generate| App
    Client -->|GET /api/v1/roadmap/image| App
    Client -->|GET /api/v1/roadmap/excel| App
```

## 2. Logical Split and Modules

### Core-API (FastAPI)
The Core-API is stateless and does the heavy lifting:
* **API Bootstrap (`src/api/app.py`)**: Boots up FastAPI and sets up Swagger API documentation.
* **Roadmap Router (`src/api/routers/roadmap.py`)**: Orchestrates the sync, spreadsheet formatting, Gantt generation, and upload steps.
* **Linear Client (`src/linear/graphql_client.py`)**: Handles retries via `tenacity` and executes GraphQL queries.
* **Excel Engine (`src/generator/excel.py`)**: Uses `pandas` and `xlsxwriter` to compile the active roadmaps into spreadsheets.
* **Timeline Engine (`src/generator/timeline.py`)**: Uses `plotly` and `kaleido` to generate static Gantt PNG files.
* **GDrive Client (`src/storage/gdrive.py`)**: Google Service Account connector to replace old files and output shareable URL links.

### Worker (Discord Bot)
The Worker is a lightweight background daemon:
* **Discord Client (`src/bot/discord_client.py`)**: Establishes connection to the Discord gateway, handles slash commands like `/roadmap`, and schedules weekly updates.
* **API Client (`src/bot/api_client.py`)**: Asynchronously queries `/api/v1/roadmap/generate` on the FastAPI pod.
