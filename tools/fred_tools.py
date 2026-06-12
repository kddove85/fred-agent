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
    async def get_series_observations(
        series_id: str,
        limit: int = 100,
        sort_order: str = "asc",
        observation_start: str | None = None,
        observation_end: str | None = None,
        frequency: str | None = None,
        aggregation_method: str = "avg",
        units: str = "lin",
        offset: int = 0,
    ) -> str:
        """Get observations for a specific FRED series.

        Args:
            series_id: The ID of the FRED series (e.g., "GDP", "UNRATE")
            limit: Maximum number of observations to return (1-100000, default: 100)
            sort_order: Sort order for observations - 'asc' or 'desc' (default: 'asc')
            observation_start: Start date in YYYY-MM-DD format
            observation_end: End date in YYYY-MM-DD format
            frequency: Optional lower frequency aggregation target (e.g., 'q', 'a', 'wef')
            aggregation_method: Aggregation method when frequency is set ('avg', 'sum', 'eop')
            units: Value transform key (e.g., 'lin', 'pch', 'pc1', 'log')
            offset: Pagination offset (default: 0)
        """
        return await fred_service.get_series_observations(
            series_id=series_id,
            limit=limit,
            sort_order=sort_order,
            observation_start=observation_start,
            observation_end=observation_end,
            frequency=frequency,
            aggregation_method=aggregation_method,
            units=units,
            offset=offset,
        )

    @mcp.tool()
    async def get_series_info(series_id: str) -> str:
        """Get information about a specific FRED series.

        Args:
            series_id: The ID of the FRED series (e.g., "GDP", "UNRATE")
        """
        return await fred_service.get_series_info(series_id)

    @mcp.tool()
    async def get_categories(category_id: int = 0) -> str:
        """Get a list of FRED categories.

        Args:
            category_id: Parent category ID to fetch children for (default: 0 for root)
        """
        return await fred_service.get_categories(category_id)

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

    # -------------------------------------------------------------------------
    # Group 1: Series metadata
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def get_series_categories(
        series_id: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get the categories that a FRED series belongs to.

        Args:
            series_id: The FRED series ID (e.g., "GDP", "UNRATE")
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
        """
        return await fred_service.get_series_categories(series_id, realtime_start, realtime_end)

    @mcp.tool()
    async def get_series_release(
        series_id: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get the release that a FRED series belongs to.

        Args:
            series_id: The FRED series ID (e.g., "GDP", "UNRATE")
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
        """
        return await fred_service.get_series_release(series_id, realtime_start, realtime_end)

    @mcp.tool()
    async def get_series_tags(
        series_id: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        order_by: str | None = None,
        sort_order: str | None = None,
    ) -> str:
        """Get the FRED tags assigned to a series.

        Args:
            series_id: The FRED series ID (e.g., "GDP", "UNRATE")
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            order_by: Attribute to order results by (e.g., 'name', 'popularity', 'series_count')
            sort_order: Sort direction - 'asc' or 'desc'
        """
        return await fred_service.get_series_tags(series_id, realtime_start, realtime_end, order_by, sort_order)

    @mcp.tool()
    async def get_series_updates(
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 100,
        offset: int = 0,
        filter_value: str | None = None,
    ) -> str:
        """Get recently updated FRED series.

        Args:
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)
            filter_value: Filter by geography type - 'macro', 'regional', or 'all' (default: all)
        """
        return await fred_service.get_series_updates(realtime_start, realtime_end, limit, offset, filter_value)

    @mcp.tool()
    async def get_series_vintagedates(
        series_id: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_order: str = "asc",
    ) -> str:
        """Get the vintage dates available for a FRED series (for real-time data analysis).

        Args:
            series_id: The FRED series ID (e.g., "GDP", "UNRATE")
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.get_series_vintagedates(series_id, realtime_start, realtime_end, limit, offset, sort_order)

    @mcp.tool()
    async def search_series_tags(
        series_search_text: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        tag_names: str | None = None,
        tag_group_id: str | None = None,
        tag_search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags associated with a series search query.

        Args:
            series_search_text: The series search text to find matching tags for
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            tag_names: Semicolon-separated list of tag names to filter by
            tag_group_id: Filter by tag group (e.g., 'freq', 'gen', 'geo', 'geot', 'seas', 'src')
            tag_search_text: Filter tags by name substring
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by (e.g., 'name', 'popularity', 'series_count')
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.search_series_tags(series_search_text, realtime_start, realtime_end, tag_names, tag_group_id, tag_search_text, limit, offset, order_by, sort_order)

    @mcp.tool()
    async def search_series_related_tags(
        series_search_text: str,
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        tag_group_id: str | None = None,
        tag_search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags related to a series search, filtered by existing tag names.

        Args:
            series_search_text: The series search text
            tag_names: Required semicolon-separated tag names to filter from (e.g., 'annual;usa')
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            exclude_tag_names: Semicolon-separated tag names to exclude
            tag_group_id: Filter by tag group
            tag_search_text: Filter tags by name substring
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.search_series_related_tags(series_search_text, tag_names, realtime_start, realtime_end, exclude_tag_names, tag_group_id, tag_search_text, limit, offset, order_by, sort_order)

    # -------------------------------------------------------------------------
    # Group 2: Category deep-dive
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def get_category(category_id: int) -> str:
        """Get information about a specific FRED category.

        Args:
            category_id: The FRED category ID
        """
        return await fred_service.get_category(category_id)

    @mcp.tool()
    async def get_category_related(
        category_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get categories related to a FRED category.

        Args:
            category_id: The FRED category ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
        """
        return await fred_service.get_category_related(category_id, realtime_start, realtime_end)

    @mcp.tool()
    async def get_category_series(
        category_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
        filter_variable: str | None = None,
        filter_value: str | None = None,
        tag_names: str | None = None,
        exclude_tag_names: str | None = None,
    ) -> str:
        """Get series belonging to a FRED category.

        Args:
            category_id: The FRED category ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order results by (e.g., 'series_id', 'title', 'popularity')
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
            filter_variable: Filter by attribute - 'frequency', 'units', or 'seasonal_adjustment'
            filter_value: Value for the filter_variable
            tag_names: Semicolon-separated tag names to include
            exclude_tag_names: Semicolon-separated tag names to exclude
        """
        return await fred_service.get_category_series(category_id, realtime_start, realtime_end, limit, offset, order_by, sort_order, filter_variable, filter_value, tag_names, exclude_tag_names)

    @mcp.tool()
    async def get_category_tags(
        category_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags for series in a FRED category.

        Args:
            category_id: The FRED category ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            tag_names: Semicolon-separated tag names to filter by
            tag_group_id: Filter by tag group (e.g., 'freq', 'gen', 'geo', 'geot', 'seas', 'src')
            search_text: Filter tags by name substring
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.get_category_tags(category_id, realtime_start, realtime_end, tag_names, tag_group_id, search_text, limit, offset, order_by, sort_order)

    @mcp.tool()
    async def get_category_related_tags(
        category_id: int,
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags related to a FRED category, filtered by existing tag names.

        Args:
            category_id: The FRED category ID
            tag_names: Required semicolon-separated tag names to filter from
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            exclude_tag_names: Semicolon-separated tag names to exclude
            tag_group_id: Filter by tag group
            search_text: Filter tags by name substring
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.get_category_related_tags(category_id, tag_names, realtime_start, realtime_end, exclude_tag_names, tag_group_id, search_text, limit, offset, order_by, sort_order)

    # -------------------------------------------------------------------------
    # Group 3: Releases
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def get_release(
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get information about a specific FRED release.

        Args:
            release_id: The FRED release ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
        """
        return await fred_service.get_release(release_id, realtime_start, realtime_end)

    @mcp.tool()
    async def get_releases_dates(
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
        include_release_dates_with_no_data: bool = False,
    ) -> str:
        """Get release dates for all FRED releases (the economic data calendar).

        Args:
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by (e.g., 'release_date', 'release_id', 'release_name')
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
            include_release_dates_with_no_data: Include dates with no data (default: False)
        """
        return await fred_service.get_releases_dates(realtime_start, realtime_end, limit, offset, order_by, sort_order, include_release_dates_with_no_data)

    @mcp.tool()
    async def get_release_dates(
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 10000,
        offset: int = 0,
        sort_order: str = "asc",
        include_release_dates_with_no_data: bool = False,
    ) -> str:
        """Get release dates for a specific FRED release.

        Args:
            release_id: The FRED release ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            limit: Maximum number of results (default: 10000)
            offset: Pagination offset (default: 0)
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
            include_release_dates_with_no_data: Include dates with no data (default: False)
        """
        return await fred_service.get_release_dates(release_id, realtime_start, realtime_end, limit, offset, sort_order, include_release_dates_with_no_data)

    @mcp.tool()
    async def get_release_series(
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
        filter_variable: str | None = None,
        filter_value: str | None = None,
        tag_names: str | None = None,
        exclude_tag_names: str | None = None,
    ) -> str:
        """Get series belonging to a FRED release.

        Args:
            release_id: The FRED release ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by (e.g., 'series_id', 'title', 'popularity')
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
            filter_variable: Filter by attribute - 'frequency', 'units', or 'seasonal_adjustment'
            filter_value: Value for the filter_variable
            tag_names: Semicolon-separated tag names to include
            exclude_tag_names: Semicolon-separated tag names to exclude
        """
        return await fred_service.get_release_series(release_id, realtime_start, realtime_end, limit, offset, order_by, sort_order, filter_variable, filter_value, tag_names, exclude_tag_names)

    @mcp.tool()
    async def get_release_sources(
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get data sources for a FRED release.

        Args:
            release_id: The FRED release ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
        """
        return await fred_service.get_release_sources(release_id, realtime_start, realtime_end)

    @mcp.tool()
    async def get_release_tags(
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags for series in a FRED release.

        Args:
            release_id: The FRED release ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            tag_names: Semicolon-separated tag names to filter by
            tag_group_id: Filter by tag group
            search_text: Filter tags by name substring
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.get_release_tags(release_id, realtime_start, realtime_end, tag_names, tag_group_id, search_text, limit, offset, order_by, sort_order)

    @mcp.tool()
    async def get_release_related_tags(
        release_id: int,
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags related to a FRED release, filtered by existing tag names.

        Args:
            release_id: The FRED release ID
            tag_names: Required semicolon-separated tag names to filter from
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            exclude_tag_names: Semicolon-separated tag names to exclude
            tag_group_id: Filter by tag group
            search_text: Filter tags by name substring
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.get_release_related_tags(release_id, tag_names, realtime_start, realtime_end, exclude_tag_names, tag_group_id, search_text, limit, offset, order_by, sort_order)

    @mcp.tool()
    async def get_release_tables(
        release_id: int,
        element_id: int | None = None,
        include_observation_values: bool = False,
        observation_date: str | None = None,
    ) -> str:
        """Get release table data for a FRED release.

        Args:
            release_id: The FRED release ID
            element_id: Element ID of the table to start from (optional)
            include_observation_values: Include data values in the response (default: False)
            observation_date: Date for observation values in YYYY-MM-DD format
        """
        return await fred_service.get_release_tables(release_id, element_id, include_observation_values, observation_date)

    # -------------------------------------------------------------------------
    # Group 4: Sources
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def get_source(
        source_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get information about a specific FRED data source.

        Args:
            source_id: The FRED source ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
        """
        return await fred_service.get_source(source_id, realtime_start, realtime_end)

    @mcp.tool()
    async def get_source_releases(
        source_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get releases published by a specific FRED data source.

        Args:
            source_id: The FRED source ID
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by (e.g., 'release_id', 'name', 'press_release', 'realtime_start')
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.get_source_releases(source_id, realtime_start, realtime_end, limit, offset, order_by, sort_order)

    # -------------------------------------------------------------------------
    # Group 5: Tags
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def get_related_tags(
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get FRED tags related to one or more specified tags.

        Args:
            tag_names: Required semicolon-separated tag names (e.g., 'annual;usa')
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            exclude_tag_names: Semicolon-separated tag names to exclude
            tag_group_id: Filter by tag group (e.g., 'freq', 'gen', 'geo', 'geot', 'seas', 'src')
            search_text: Filter tags by name substring
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by (e.g., 'name', 'popularity', 'series_count')
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.get_related_tags(tag_names, realtime_start, realtime_end, exclude_tag_names, tag_group_id, search_text, limit, offset, order_by, sort_order)

    @mcp.tool()
    async def get_tags_series(
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get FRED series matching one or more tags.

        Args:
            tag_names: Required semicolon-separated tag names (e.g., 'annual;usa')
            realtime_start: Start of real-time period in YYYY-MM-DD format
            realtime_end: End of real-time period in YYYY-MM-DD format
            exclude_tag_names: Semicolon-separated tag names to exclude
            limit: Maximum number of results (default: 1000)
            offset: Pagination offset (default: 0)
            order_by: Attribute to order by (e.g., 'series_id', 'title', 'popularity')
            sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')
        """
        return await fred_service.get_tags_series(tag_names, realtime_start, realtime_end, exclude_tag_names, limit, offset, order_by, sort_order)