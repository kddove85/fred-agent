"""
mcp_stock_tools.py
MCP tools for stock market data
"""

from mcp.server.fastmcp import FastMCP
from services.stock_market_service import StockMarketService, format_quote, format_dividends


# mcp = MCPServer()
# stock_service = StockMarketService()

def register_stock_tools(mcp: FastMCP):
    stock_service = StockMarketService()

    @mcp.tool()
    async def get_stock_quote(symbol: str) -> str:
        """
        Get current stock quote with price, change, volume, and key metrics.

        Provides real-time (15-min delayed) stock information including:
        - Current price and daily change
        - Day high/low and 52-week range
        - Volume and market cap
        - P/E ratio and dividend yield

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'TSLA')

        Returns:
            Formatted stock quote information

        Example:
            get_stock_quote('AAPL') -> Current Apple stock data
        """
        quote = stock_service.get_quote(symbol)
        return format_quote(quote)


    @mcp.tool()
    async def get_stock_history(
            symbol: str,
            period: str = "1mo",
            interval: str = "1d"
    ) -> str:
        """
        Get historical stock price data.

        Retrieves historical OHLCV (Open, High, Low, Close, Volume) data
        for technical analysis and trend identification.

        Args:
            symbol: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1d, 1wk, 1mo)

        Returns:
            Historical price data in JSON format

        Example:
            get_stock_history('AAPL', period='6mo', interval='1d')
        """
        data = stock_service.get_historical_data(symbol, period, interval)

        if "error" in data:
            return data["error"]

        # Format for readability
        output = f"**{data['symbol']} Historical Data ({data['period']}, {data['interval']})**\n\n"

        # Show recent data points
        recent_data = data['data'][-10:]  # Last 10 data points

        for point in recent_data:
            output += f"{point['date']}: Open ${point['open']}, Close ${point['close']}, Volume {point['volume']:,}\n"

        return output


    @mcp.tool()
    async def get_stock_dividends(symbol: str) -> str:
        """
        Get dividend payment history and annual dividend amount.

        Useful for income investors to analyze dividend-paying stocks.
        Shows recent dividend payments and calculates annual dividend.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dividend history and annual yield information

        Example:
            get_stock_dividends('MSFT') -> Microsoft dividend data
        """
        dividends = stock_service.get_dividends(symbol)
        return format_dividends(dividends)


    @mcp.tool()
    async def get_company_info(symbol: str) -> str:
        """
        Get detailed company information and fundamentals.

        Provides business overview, sector/industry classification,
        headquarters location, and key financial metrics.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Comprehensive company information

        Example:
            get_company_info('GOOGL') -> Google/Alphabet company details
        """
        info = stock_service.get_company_info(symbol)

        if "error" in info:
            return info["error"]

        # Format optional values safely
        employees_str = f"{info['employees']:,}" if info.get('employees') is not None else 'N/A'

        description_str = info['description'][:500] + "..." if info.get('description') else 'N/A'

        market_cap_str = f"${info['financials']['market_cap']:,}" if info.get('financials', {}).get('market_cap') is not None else 'N/A'
        revenue_str = f"${info['financials']['revenue']:,}" if info.get('financials', {}).get('revenue') is not None else 'N/A'
        profit_margin_str = f"{info['financials']['profit_margin']:.2%}" if info.get('financials', {}).get('profit_margin') is not None else 'N/A'

        return f"""
    **{info['company_name']} ({info['symbol']})**
    
    Sector: {info['sector']}
    Industry: {info['industry']}
    Employees: {employees_str}
    
    Headquarters: {info['headquarters']['city']}, {info['headquarters']['state']}, {info['headquarters']['country']}
    Website: {info['website']}
    
    Description:
    {description_str}
    
    Financials:
      Market Cap: {market_cap_str}
      Revenue: {revenue_str}
      Profit Margin: {profit_margin_str}
    """


    @mcp.tool()
    async def get_upcoming_earnings(symbol: str) -> str:
        """
        Get upcoming earnings date and recent earnings history.

        Earnings reports can significantly impact stock prices.
        Use this to track when companies report quarterly results.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Upcoming earnings date and recent earnings data

        Example:
            get_upcoming_earnings('NVDA') -> NVIDIA earnings schedule
        """
        earnings = stock_service.get_upcoming_earnings(symbol)

        if "error" in earnings:
            return earnings["error"]

        output = f"**{earnings['symbol']} Earnings Information**\n\n"

        if earnings['upcoming_earnings']:
            output += f"Next Earnings Date: {earnings['upcoming_earnings']}\n\n"
        else:
            output += "No upcoming earnings date available\n\n"

        if earnings['recent_earnings']:
            output += "Recent Earnings:\n"
            for e in earnings['recent_earnings']:
                output += f"  • {e['year']}: Revenue ${e['revenue']:,}, Earnings ${e['earnings']:,}\n"

        return output


    @mcp.tool()
    async def compare_stocks(symbols: str) -> str:
        """
        Compare multiple stocks side-by-side.

        Useful for evaluating investment options by comparing
        key metrics across multiple companies.

        Args:
            symbols: Comma-separated stock ticker symbols (e.g., 'AAPL,MSFT,GOOGL')

        Returns:
            Side-by-side comparison of stock metrics

        Example:
            compare_stocks('AAPL,MSFT,GOOGL') -> Compare tech giants
        """
        symbol_list = [s.strip().upper() for s in symbols.split(',')]

        if len(symbol_list) > 5:
            return "Error: Maximum 5 stocks can be compared at once"

        comparison = stock_service.compare_stocks(symbol_list)

        if "error" in comparison:
            return comparison["error"]

        output = "**Stock Comparison**\n\n"
        output += "| Metric | " + " | ".join(comparison['symbols']) + " |\n"
        output += "|--------|" + "|".join(["--------" for _ in comparison['symbols']]) + "|\n"

        metrics = comparison['metrics']

        # Current Price
        output += "| **Current Price** | "
        output += " | ".join([f"${m['current_price']:.2f}" if m['current_price'] else "N/A" for m in metrics])
        output += " |\n"

        # P/E Ratio
        output += "| **P/E Ratio** | "
        output += " | ".join([f"{m['pe_ratio']:.2f}" if m['pe_ratio'] else "N/A" for m in metrics])
        output += " |\n"

        # Dividend Yield
        output += "| **Div Yield** | "
        output += " | ".join([f"{m['dividend_yield']:.2%}" if m['dividend_yield'] else "N/A" for m in metrics])
        output += " |\n"

        # Profit Margin
        output += "| **Profit Margin** | "
        output += " | ".join([f"{m['profit_margin']:.2%}" if m['profit_margin'] else "N/A" for m in metrics])
        output += " |\n"

        return output