# System Architecture & Agent Workflow

This document outlines the system architecture, state management, and multi-agent tool boundaries for the broadband line-of-sight risk evaluation pipeline.

## 1. Architecture Diagram

The system operates on a hub-and-spoke model where the PostGIS database acts as the central state machine. 

```mermaid
graph TD
    %% Define Actors and Components
    User[Human Operator]
    CSV[locations.csv]
    PostGIS[(PostGIS DB)]
    
    subgraph "Batch Pipeline (High-Throughput)"
        Ingest[process_csv.py]
        Analysis[analysis.py Orchestrator]
        ExternalAPI((USGS REST API))
    end
    
    subgraph "Tool Tier (Strict Boundaries)"
        DataTool[data_tool.py]
        AnalysisTool[analysis_tool.py]
    end
    
    subgraph "Agentic Tier (Interactive/Validation)"
        Supervisor[supervisor.py]
        Claude[Claude 3.5 Haiku LLM]
    end

    %% Data Flow
    CSV -->|Read| Ingest
    Ingest -->|Bulk Insert| PostGIS
    
    %% Batch Flow
    Analysis -->|Fetch Batch| DataTool
    DataTool -->|Query| PostGIS
    DataTool -->|Point Query| ExternalAPI
    Analysis -->|Calculate| AnalysisTool
    AnalysisTool -->|Evaluate| Analysis
    Analysis -->|Bulk Update| PostGIS
    
    %% Agent Flow
    User -->|Prompts| Supervisor
    Supervisor <-->|Reasoning Loop| Claude
    Claude -->|Request Tool| Supervisor
    Supervisor -->|Invoke| DataTool
    Supervisor -->|Invoke| AnalysisTool
    
    %% Human Intervention
    PostGIS -.->|Anomalies Identified| User
    User -.->|Manual Override| PostGIS