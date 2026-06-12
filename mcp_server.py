import os
import logging
import sys

from mcp.server.fastmcp import FastMCP
from tools.fred_tools import register_fred_tools
from tools.geofred_tools import register_geofred_tools
from tools.census_tools import register_census_tools
from tools.rss_feed_tools import register_rss_feed_tools
from tools.mcp_stock_tools import register_stock_tools

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

server_name = os.getenv('MCP_SERVER_NAME', 'fred-server')
host = os.getenv('MCP_HOST', '0.0.0.0')
port = int(os.getenv('MCP_PORT', '8000'))
fred_api_key = os.getenv('FRED_API_KEY')
census_api_key = os.getenv('CENSUS_API_KEY')
mcp = FastMCP(server_name, host=host, port=port)

logger.info("Registering tools...")
if not fred_api_key:
    logger.warning("FRED_API_KEY is not set. FRED tools will return configuration errors until it is configured.")
if not census_api_key:
    logger.warning("CENSUS_API_KEY is not set. Census tools will return configuration errors until it is configured. Get a free key at https://api.census.gov/data/key_signup.html")
register_fred_tools(mcp)
register_geofred_tools(mcp)
register_census_tools(mcp)
register_rss_feed_tools(mcp)
register_stock_tools(mcp)

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