from mcp.server.fastmcp import FastMCP
from services.fred_service import FREDService

def register_geofred_tools(mcp: FastMCP):
    """Register GeoFRED tools for regional/geographic economic data."""
    fred_service = FREDService()

    @mcp.tool()
    async def get_geofred_series_group(series_id: str) -> str:
        """Get metadata for a geographic FRED series (GeoFRED).

        Returns the series group ID, region type, title, seasonality, units,
        frequency, and date range. Use the returned series_group ID with
        get_geofred_regional_data to fetch cross-sectional regional data.

        Args:
            series_id: A FRED series ID that has regional coverage (e.g., "WIPCPI")
        """
        return await fred_service.get_geofred_series_group(series_id)

    @mcp.tool()
    async def get_geofred_series_data(
        series_id: str,
        date: str | None = None,
        start_date: str | None = None,
    ) -> str:
        """Get cross-sectional regional data for a geographic FRED series.

        Returns data values for all regions at a given date (or date range).
        Use this to compare an economic indicator across all states, counties,
        or metro areas at once.

        Args:
            series_id: A FRED series ID with regional coverage (e.g., "WIPCPI")
            date: Observation date in YYYY-MM-DD format (returns single snapshot)
            start_date: Start of date range in YYYY-MM-DD format (returns range)
        """
        return await fred_service.get_geofred_series_data(series_id, date, start_date)

    @mcp.tool()
    async def get_geofred_regional_data(
        series_group: str,
        region_type: str,
        date: str,
        season: str,
        units: str,
        frequency: str,
        start_date: str | None = None,
        transformation: str | None = None,
        aggregation_method: str | None = None,
    ) -> str:
        """Get cross-sectional regional economic data by series group (GeoFRED).

        Fetches the same economic indicator across all regions of a given type
        at a specific point in time. For example: unemployment rates for all 50
        states, or per-capita income for all counties.

        Args:
            series_group: Series group ID (get from get_geofred_series_group)
            region_type: Geographic region type - one of: 'state', 'county', 'msa',
                'bea', 'frb', 'necta', 'country', 'censusregion'
            date: Observation date in YYYY-MM-DD format
            season: Seasonal adjustment - 'SA' (adjusted), 'NSA' (not adjusted),
                'SSA' (smoothed adjusted), 'SAAR', or 'NSAAR' (annualized rates)
            units: Unit description string (e.g., "Dollars", "Percent")
            frequency: Required frequency code - e.g., 'a' (annual), 'q' (quarterly),
                'm' (monthly), 'w' (weekly), 'd' (daily)
            start_date: Start of date range in YYYY-MM-DD format
            transformation: Data transformation code (e.g., 'lin', 'pch', 'pc1', 'log')
            aggregation_method: How to aggregate when changing frequency - 'avg', 'sum', or 'eop'
        """
        return await fred_service.get_geofred_regional_data(
            series_group, region_type, date, season, units, frequency,
            start_date, transformation, aggregation_method,
        )

    @mcp.tool()
    async def get_geofred_shapes(shape: str) -> str:
        """Get GeoJSON boundary files for geographic regions (GeoFRED).

        Returns a GeoJSON FeatureCollection with boundary polygons for all
        regions of the given type. Useful for mapping economic data onto
        geographic visualizations.

        Warning: county-level shapes can be several MB. Prefer 'state' or
        broader region types when possible.

        Args:
            shape: Region type for boundary data - one of: 'state', 'county',
                'msa', 'bea', 'frb', 'necta', 'country', 'censusregion', 'censusdivision'
        """
        return await fred_service.get_geofred_shapes(shape)
