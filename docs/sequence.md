# linmap-bot Sequence & Data Flow

This document outlines the sequential flow of data during generation.

## 1. Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as Discord User
    participant Bot as Discord Bot
    participant Client as API Client
    participant API as FastAPI Core
    participant Linear as Linear API
    participant Drive as Google Drive

    User->>Bot: Run /roadmap slash command
    Bot->>Bot: Defer response (loading state)
    Bot->>Client: trigger_generation()
    Client->>API: POST /api/v1/roadmap/generate
    activate API
    API->>Linear: fetch_roadmap_data() (GraphQL)
    Linear-->>API: Roadmap JSON data
    API->>API: generate_excel_report()
    API->>API: generate_gantt_chart() (Plotly + Kaleido)
    opt Optional Google Drive Fallback
        API->>Drive: upload_file() (Excel Report)
        Drive-->>API: Google Drive shareable link (excel_url)
    end
    API-->>Client: {status, message, excel_url, gantt_image_path}
    deactivate API
    Client-->>Bot: JSON response metadata
    par Fetch Gantt Image
        Bot->>Client: fetch_gantt_image()
        Client->>API: GET /api/v1/roadmap/image
        API-->>Client: image/png binary data
        Client-->>Bot: PNG bytes
    and Fetch Excel Spreadsheet
        Bot->>Client: fetch_excel_file()
        Client->>API: GET /api/v1/roadmap/excel
        API-->>Client: Excel binary data
        Client-->>Bot: Excel bytes
    end
    Bot->>User: Post Embed + dual attachments (PNG & Excel) + optional Drive link
```

## 2. Step-by-Step Data Flow

1. **User Request / Scheduler**: An execution is triggered either by a Discord user running the `/roadmap` command or by the background task scheduler `discord.ext.tasks.loop`.
2. **Acknowledgment**: The bot immediately defers the Discord interaction response, presenting a loading/waiting state.
3. **API Dispatch**: The Bot client triggers a REST request to the FastAPI application's `/roadmap/generate` route.
4. **Data Sync**: The FastAPI Core queries the Linear API for all non-canceled and non-archived projects.
5. **Report Generation**: The active projects and milestones are compiled into a formatted Excel sheet and a PNG Gantt chart locally.
6. **Optional Cloud Upload**: If configured, the Excel sheet is uploaded to Google Drive. Any upload failure is handled gracefully without stopping the pipeline.
7. **Asset Retrieval**: The Bot retrieves both the visual Gantt chart image and the Excel spreadsheet binaries in parallel from the FastAPI Core.
8. **Dual-Attachment Broadcast**: The Bot attaches both in-memory file buffers directly to the Discord message alongside a rich embed (which includes the Google Drive link if successfully generated/uploaded).
