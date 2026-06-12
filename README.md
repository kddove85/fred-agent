# fred-agent

AI Agent to retrieve and interpret data from the Federal Reserve Economic Data (FRED) server.

## Overview

`fred-agent` is a Python-based tool that connects to the FRED API, retrieves economic data, and provides AI-powered interpretation of the results. It is designed for researchers, analysts, and developers who need automated access and insights from FRED datasets.

## Features

- MCP server exposing FRED economic data tools
- Stock market data via yfinance
- RSS feed tools for economic news
- Supports stdio, SSE, and streamable-http transports
- Docker-ready

## Requirements

- Python 3.12+
- pip

## Installation

1. Clone the repository:
```bash
git clone https://github.com/kddove85/fred-agent.git
```
2. Navigate to the project directory:
```bash
cd fred-agent
```
3. Activate the virtual environment. (See [Python venv docs](https://docs.python.org/3/tutorial/venv.html#creating-virtual-environments))
4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
FRED_API_KEY=your_fred_api_key_here

MCP_SERVER_NAME=fred-server
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8000

LOG_LEVEL=INFO

FRED_HTTP_TIMEOUT=30
FRED_HTTP_MAX_RETRIES=2
FRED_HTTP_RETRY_BACKOFF=0.5
```
Replace `FRED_API_KEY` with your actual key. Set `MCP_TRANSPORT` to `stdio`, `sse`, or `streamable-http`.

`FRED_HTTP_TIMEOUT`, `FRED_HTTP_MAX_RETRIES`, and `FRED_HTTP_RETRY_BACKOFF` control request resilience to FRED transient errors such as `429` and `5xx`.

## Usage

### Run the MCP server directly:
```bash
python mcp_server.py
```

### Run with Docker:
```bash
docker compose up --build
```
The server will be available on port 8093 (mapped from container port 8000).

## FRED Tool Output Format

FRED tools now return structured JSON text for consistent LLM parsing:

- `ok`: `true` for success, `false` for errors
- `endpoint`: FRED endpoint called
- `params`: request parameters used
- `data`: payload (list/object)
- `meta`: additional paging/summary fields (success only)
- `error`: error code/message (error only)
- `status_code`: HTTP code when available (error only)

## Interval-Aware Observations

`get_series_observations` supports the key interval and transformation parameters from FRED docs:

- `series_id` (required)
- `observation_start` and `observation_end` (`YYYY-MM-DD`)
- `frequency` (`d`, `w`, `bw`, `m`, `q`, `sa`, `a`, `wef`, `weth`, `wew`, `wetu`, `wem`, `wesu`, `wesa`, `bwew`, `bwem`)
- `aggregation_method` (`avg`, `sum`, `eop`) when `frequency` is set
- `units` (`lin`, `chg`, `ch1`, `pch`, `pc1`, `pca`, `cch`, `cca`, `log`)
- `sort_order` (`asc` or `desc`)
- `limit` (`1-100000`) and `offset` (`>= 0`)

Example query intent:

- "Get CPI observations from 2019-01-01 to 2024-12-31 as quarterly averages with percent change".

Set:

- `series_id="CPIAUCSL"`
- `observation_start="2019-01-01"`
- `observation_end="2024-12-31"`
- `frequency="q"`
- `aggregation_method="avg"`
- `units="pch"`
