import os
import logging
import sys

from mcp.server.fastmcp import FastMCP
from tools.fred_tools import register_fred_tools

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

server_name = os.getenv('MCP_SERVER_NAME', 'weather-transfer-server')
host = os.getenv('MCP_HOST', '0.0.0.0')
port = int(os.getenv('MCP_PORT', '8000'))
mcp = FastMCP(server_name, host=host, port=port)

logger.info("Registering weather tools...")
register_fred_tools(mcp)

def main():
    """Initialize and run the MCP server."""
    logger.info(f"Starting MCP Server: {server_name}")
    transport = os.getenv('MCP_TRANSPORT', 'stdio').lower()
    logger.info(f"Transport: {transport}")

    try:
        if transport == 'sse':
            logger.info(f"Server running in SSE mode on {host}:{port}")
            mcp.run(transport="sse")
        elif transport == 'streamable-http':
            logger.info(f"Server running in Streamable HTTP mode on {host}:{port}")
            mcp.run(transport="streamable-http")
        else:
            logger.info("Server running with stdio transport")
            mcp.run(transport='stdio')
    except (BrokenPipeError, KeyboardInterrupt):
        logger.info("Server stopped or client disconnected")
    except Exception as e:
        logger.error(f"Server error: {e}")
        if transport != 'stdio':
            logger.info("Falling back to stdio transport")
            mcp.run(transport='stdio')

if __name__ == "__main__":
    main()