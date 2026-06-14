# linmap-bot

```
https://discord.com/oauth2/authorize?client_id=1515338362221887598&permissions=51200&integration_type=0&scope=bot+applications.commands
```

Automated Roadmap Generator that syncs data from Linear, builds a formatted Excel report and a high-resolution Gantt chart, uploads artifacts to cloud storage, and publishes updates on Discord.

---

## Technical Architecture

```
+------------------+         GraphQL          +-------------+
|    Linear API    | <---------------------- |  linmap-bot |
+------------------+                          +-------------+
                                                     |
                                                     |-- Generates Excel (.xlsx)
                                                     |-- Generates Gantt Chart (.png)
                                                     v
+------------------+         Uploads          +-------------+
|   Google Drive   | <---------------------- |  Cloud Link |
+------------------+                          +-------------+
                                                     |
                                                     | Sends Rich Embed
                                                     v
                                              +-------------+
                                              | Discord Bot |
                                              +-------------+
```

## Setup & Configuration

The application is configured exclusively via environment variables.

| Variable Name | Type | Description | Required |
|---|---|---|---|
| `LOG_LEVEL` | String | Logging level (`INFO`, `DEBUG`, `ERROR`) | No (Default: `INFO`) |
| `LINEAR_API_KEY` | String | Personal API key for Linear authentication | Yes |
| `LINEAR_ORGANIZATION_SLUG` | String | Slug of your Linear workspace (e.g., `sigl-ubsi`) | Yes |
| `DISCORD_TOKEN` | String | Discord Bot secret token | Yes |
| `DISCORD_CHANNEL_ID` | Integer | Destination channel ID for automated updates | Yes |
| `GDRIVE_FOLDER_ID` | String | Google Drive folder ID where Excel files are stored | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | String | Path to the Google Service Account JSON file OR the raw JSON credentials content directly | Yes |

---

## Execution Instructions for the AI Agent (antigravity2)

Your goal is to build this project sequentially. Follow these phases:

### Phase 1: Environment & Settings
1. Set up the Python virtual environment.
2. Implement `src/config.py` using `pydantic-settings` to enforce type safety on environment variables.
3. Configure structured logging to standard output.

### Phase 2: Data Extraction (Linear API client)
1. Implement GraphQL queries in `src/linear/graphql_client.py`.
2. Do not fetch raw issues indiscriminately. Retrieve only non-canceled, non-archived projects and their associated milestones, issues, and target dates.
3. Handle API errors gracefully and implement a retry mechanism.

### Phase 3: Reporting & Visualization Engines
1. In `src/generator/excel.py`, use `pandas` and `xlsxwriter` to create a cleanly formatted table representing the projects, status, target dates, and assignees.
2. In `src/generator/timeline.py`, use `plotly` to build a clean Gantt chart. Use static styling (no complex HTML wrappers). Save it locally as a PNG using `kaleido`. Highlight milestones and key dates (e.g. classes or deliverables) on the timeline.

### Phase 4: Cloud Storage Integration
1. Implement a generic storage interface in `src/storage/base.py`.
2. Implement `src/storage/gdrive.py` using Google API client libraries.
3. The upload process must replace older versions or upload new versions with unified shareable links.

### Phase 5: Discord Orchestrator
1. Implement `src/bot/discord_client.py` using `discord.py` (v2.x).
2. Configure a Slash command `/roadmap` utilizing interaction deferrals (since file generation and GDrive upload take a few seconds).
3. Use a background task loop (using `tasks.loop`) to trigger the generation and upload weekly.
