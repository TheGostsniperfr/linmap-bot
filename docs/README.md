# linmap-bot Technical Documentation

This directory contains the split modular technical specifications of **`linmap-bot`**.

> [!IMPORTANT]
> **Instructions for AI Agents & Developers**:
> When modifying components, adding routes, or changing configuration parameters, you **MUST** update the diagrams and text sections of the corresponding documents to ensure technical alignment.

## Documentation Structure

1. **[System Components & Modules](file:///home/brian/Documents/aepita/other-project/linmap-bot/docs/components.md)**: Detailed information on the decoupled Core-API (FastAPI) & Worker (Discord Bot) architecture, module maps, and directories structure.
2. **[Sequence & Data Flow](file:///home/brian/Documents/aepita/other-project/linmap-bot/docs/sequence.md)**: Sequential description of how data flows from a slash command or scheduled event, through the processing pipeline, to Google Drive and Discord.
3. **[Deployment & Topology](file:///home/brian/Documents/aepita/other-project/linmap-bot/docs/deployment.md)**: Network architecture, Service and Deployment layouts in the k3s cluster, and secrets management/volume mounts.
