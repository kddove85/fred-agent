from mcp.server.fastmcp import FastMCP
from services.census_service import CensusService


def register_census_tools(mcp: FastMCP):
    """Register US Census Bureau data tools."""
    census_service = CensusService()

    @mcp.tool()
    async def get_acs_income(
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get income and poverty estimates from the American Community Survey (ACS 5-Year).

        Returns median household income, per capita income, and poverty counts
        for states or counties. Data year: 2023.

        Args:
            state_fips: 2-digit state FIPS code (e.g. '06' for California), state name
                (e.g. 'California'), or '*' for all states
            county_fips: 3-digit county FIPS code (e.g. '037' for Los Angeles County).
                If omitted, returns all counties in the state (or state-level if state='*')
        """
        return await census_service.get_acs_income(state_fips, county_fips)

    @mcp.tool()
    async def get_acs_demographics(
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get demographic estimates from the American Community Survey (ACS 5-Year).

        Returns total population and breakdowns by sex and race/ethnicity
        for states or counties. Data year: 2023.

        Args:
            state_fips: 2-digit state FIPS code (e.g. '06' for California), state name
                (e.g. 'Texas'), or '*' for all states
            county_fips: 3-digit county FIPS code. If omitted, returns all counties
                in the state (or state-level if state='*')
        """
        return await census_service.get_acs_demographics(state_fips, county_fips)

    @mcp.tool()
    async def get_acs_employment(
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get labor force and employment estimates from the American Community Survey (ACS 5-Year).

        Returns civilian labor force size, employed count, unemployed count, and
        population not in the labor force. More detailed than FRED's national unemployment
        rate — provides county-level labor force statistics. Data year: 2023.

        Args:
            state_fips: 2-digit state FIPS code (e.g. '48' for Texas), state name,
                or '*' for all states
            county_fips: 3-digit county FIPS code. If omitted, returns all counties
                in the state (or state-level if state='*')
        """
        return await census_service.get_acs_employment(state_fips, county_fips)

    @mcp.tool()
    async def get_acs_housing(
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get housing characteristic estimates from the American Community Survey (ACS 5-Year).

        Returns total housing units, occupancy status, owner vs. renter-occupied counts,
        median home value, and median gross rent. Data year: 2023.

        Args:
            state_fips: 2-digit state FIPS code (e.g. '36' for New York), state name,
                or '*' for all states
            county_fips: 3-digit county FIPS code. If omitted, returns all counties
                in the state (or state-level if state='*')
        """
        return await census_service.get_acs_housing(state_fips, county_fips)

    @mcp.tool()
    async def get_county_business_patterns(
        state_fips: str,
        county_fips: str | None = None,
        naics_code: str | None = None,
    ) -> str:
        """Get County Business Patterns: establishment counts, employment, and payroll by industry.

        Covers ALL businesses with paid employees (public and private), unlike Yahoo Finance
        which covers only publicly traded companies. Returns data for the reference week of
        March 12. Data year: 2022.

        Common NAICS codes:
          '00' = All industries (default)
          '11' = Agriculture
          '21' = Mining
          '22' = Utilities
          '23' = Construction
          '31-33' = Manufacturing
          '42' = Wholesale trade
          '44-45' = Retail trade
          '48-49' = Transportation
          '51' = Information
          '52' = Finance and insurance
          '53' = Real estate
          '54' = Professional services
          '61' = Educational services
          '62' = Health care
          '71' = Arts and entertainment
          '72' = Accommodation and food services

        Args:
            state_fips: 2-digit state FIPS code (e.g. '17' for Illinois), state name,
                or '*' for all states
            county_fips: 3-digit county FIPS code. If omitted, returns all counties
                in the state (or state-level if state='*')
            naics_code: NAICS industry code to filter by (default '00' = all industries)
        """
        return await census_service.get_county_business_patterns(state_fips, county_fips, naics_code)

    @mcp.tool()
    async def get_income_poverty_estimates(
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get median household income and poverty rates from SAIPE (Small Area Income & Poverty Estimates).

        More geographically granular than national poverty statistics — provides county-level
        and even school-district-level poverty rates updated annually. Data year: 2022.

        Args:
            state_fips: 2-digit state FIPS code (e.g. '01' for Alabama), state name,
                or '*' for all states
            county_fips: 3-digit county FIPS code. If omitted, returns all counties
                in the state (or state-level if state='*')
        """
        return await census_service.get_income_poverty_estimates(state_fips, county_fips)

    @mcp.tool()
    async def get_population_estimates(
        state_fips: str | None = None,
    ) -> str:
        """Get current population estimates and density from the Population Estimates Program (PEP).

        Provides annual population estimates between decennial censuses, with
        population density per square mile. Data year: 2023.

        Args:
            state_fips: 2-digit state FIPS code, state name, or '*' / None for all states
        """
        return await census_service.get_population_estimates(state_fips)
