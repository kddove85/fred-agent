# fred-agent

AI Agent to retrieve and interpret data from the Federal Reserve Economic Data (FRED) server.

## Overview

`fred-agent` is a Python-based tool that connects to the FRED API, retrieves economic data, and provides AI-powered interpretation of the results. It is designed for researchers, analysts, and developers who need automated access and insights from FRED datasets.

## Features

- Connects to the FRED API using your API key
- Retrieves economic data series
- Interprets and summarizes data using AI
- Simple client-server architecture

## Requirements

- Python 3.12+
- pip

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fred-agent.git cd fred-agent
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

Create a `.env` file in the project root with your FRED API key:

```env
FRED_API_KEY=your_fred_api_key_here

OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=openai_url_base
API_VERSION=api_version
OPENAI_ORGANIZATION=organization_code
MODEL=gpt-4o

MCP_TRANSPORT=stdio
MCP_SERVER_NAME=fred-server
MCP_SERVER_VERSION=1.0.0

LOG_LEVEL=INFO
```
Replace the values with your actual API keys and desired server settings.

## Usage

### Start the client and server:
```bash
python mcp_client.py mcp_server.py
```

Follow the prompts to request and interpret FRED data.
