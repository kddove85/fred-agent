import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    FRED_API_KEY = os.getenv('FRED_API_KEY')
    CENSUS_API_KEY = os.getenv('CENSUS_API_KEY')

    MCP_SERVER_NAME = os.getenv('MCP_SERVER_NAME', 'fred-server')
    MCP_HOST = os.getenv('MCP_HOST', '0.0.0.0')
    MCP_PORT = int(os.getenv('MCP_PORT', '8000'))
    MCP_TRANSPORT = os.getenv('MCP_TRANSPORT', 'stdio')

    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
