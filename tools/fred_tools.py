from mcp.server.fastmcp import FastMCP
from services.fred_service import FREDService

def register_fred_tools(mcp: FastMCP):
    """Register FRED-related tools."""
    fred_service = FREDService()

    @mcp.tool()
    async def search_series(search_text: str) -> str:
        """Search for FRED series by keyword.

        Args:
            search_text: Keyword to search for in FRED series
        """
        return await fred_service.search_series(search_text)

    @mcp.tool()
    async def get_series_observations(series_id: str, limit: int = 100, sort_order: str = 'asc') -> str:
        """Get observations for a specific FRED series.

        Args:
            series_id: The ID of the FRED series (e.g., "GDP", "UNRATE")
            limit: Maximum number of observations to return (default: 100)
            sort_order: Sort order for observations - 'asc' for oldest first, 'desc' for newest first (default: 'asc')
        """
        return await fred_service.get_series_observations(series_id, limit, sort_order)

    @mcp.tool()
    async def get_series_info(series_id: str) -> str:
        """Get information about a specific FRED series.

        Args:
            series_id: The ID of the FRED series (e.g., "GDP", "UNRATE")
        """
        return await fred_service.get_series_info(series_id)

    @mcp.tool()
    async def get_categories() -> str:
        """Get a list of FRED categories.

        Args: None
        """
        return await fred_service.get_categories()

    @mcp.tool()
    async def get_releases() -> str:
        """Get a list of FRED releases.

        Args: None
        """
        return await fred_service.get_releases()

    @mcp.tool()
    async def get_sources() -> str:
        """Get a list of FRED sources.

        Args: None
        """
        return await fred_service.get_sources()

    @mcp.tool()
    async def get_tags() -> str:
        """Get a list of FRED tags.

        Args: None
        """
        return await fred_service.get_tags()