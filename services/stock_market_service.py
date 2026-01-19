"""
stock_market_service.py
MCP service for stock market data using yfinance
"""

import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StockMarketService:
    """Service for fetching stock market data"""

    @staticmethod
    def get_quote(symbol: str) -> Dict:
        """
        Get current quote for a stock

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

        Returns:
            Dict with current price, change, volume, etc.
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get real-time price
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose')

            # Calculate change
            if current_price and previous_close:
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100
            else:
                change = None
                change_percent = None

            return {
                "symbol": symbol.upper(),
                "company_name": info.get('longName', 'N/A'),
                "current_price": current_price,
                "previous_close": previous_close,
                "change": change,
                "change_percent": change_percent,
                "day_high": info.get('dayHigh'),
                "day_low": info.get('dayLow'),
                "volume": info.get('volume'),
                "market_cap": info.get('marketCap'),
                "pe_ratio": info.get('trailingPE'),
                "dividend_yield": info.get('dividendYield'),
                "52_week_high": info.get('fiftyTwoWeekHigh'),
                "52_week_low": info.get('fiftyTwoWeekLow'),
            }

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {"error": f"Could not fetch data for {symbol}"}

    @staticmethod
    def get_historical_data(
            symbol: str,
            period: str = "1mo",
            interval: str = "1d"
    ) -> Dict:
        """
        Get historical price data

        Args:
            symbol: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            Dict with historical price data
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return {"error": f"No data found for {symbol}"}

            # Convert to dict format
            data = []
            for date, row in hist.iterrows():
                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(row['Open'], 2),
                    "high": round(row['High'], 2),
                    "low": round(row['Low'], 2),
                    "close": round(row['Close'], 2),
                    "volume": int(row['Volume'])
                })

            return {
                "symbol": symbol.upper(),
                "period": period,
                "interval": interval,
                "data": data
            }

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return {"error": f"Could not fetch historical data for {symbol}"}

    @staticmethod
    def get_dividends(symbol: str) -> Dict:
        """
        Get dividend history

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dict with dividend payment history
        """
        try:
            ticker = yf.Ticker(symbol)
            dividends = ticker.dividends

            if dividends.empty:
                return {
                    "symbol": symbol.upper(),
                    "message": "No dividend history found"
                }

            # Get recent dividends (last 10)
            recent_dividends = []
            for date, amount in dividends.tail(10).items():
                recent_dividends.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "amount": round(amount, 2)
                })

            # Calculate annual dividend
            one_year_ago = datetime.now() - timedelta(days=365)
            recent = dividends[dividends.index >= one_year_ago]
            annual_dividend = recent.sum() if not recent.empty else 0

            return {
                "symbol": symbol.upper(),
                "annual_dividend": round(annual_dividend, 2),
                "recent_dividends": recent_dividends,
                "total_dividends_paid": len(dividends)
            }

        except Exception as e:
            logger.error(f"Error fetching dividends for {symbol}: {e}")
            return {"error": f"Could not fetch dividends for {symbol}"}

    @staticmethod
    def get_company_info(symbol: str) -> Dict:
        """
        Get detailed company information

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dict with company details
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol.upper(),
                "company_name": info.get('longName'),
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "description": info.get('longBusinessSummary'),
                "website": info.get('website'),
                "employees": info.get('fullTimeEmployees'),
                "headquarters": {
                    "city": info.get('city'),
                    "state": info.get('state'),
                    "country": info.get('country')
                },
                "financials": {
                    "market_cap": info.get('marketCap'),
                    "revenue": info.get('totalRevenue'),
                    "profit_margin": info.get('profitMargins'),
                    "operating_margin": info.get('operatingMargins')
                }
            }

        except Exception as e:
            logger.error(f"Error fetching company info for {symbol}: {e}")
            return {"error": f"Could not fetch company info for {symbol}"}

    @staticmethod
    def get_upcoming_earnings(symbol: str) -> Dict:
        """
        Get upcoming earnings date and recent earnings history

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dict with earnings information
        """
        try:
            ticker = yf.Ticker(symbol)

            # Get earnings dates
            earnings_dates = ticker.earnings_dates

            # Get earnings history
            earnings = ticker.earnings

            result = {
                "symbol": symbol.upper(),
                "upcoming_earnings": None,
                "recent_earnings": []
            }

            # Find next earnings date
            if earnings_dates is not None and not earnings_dates.empty:
                future_dates = earnings_dates[earnings_dates.index > datetime.now()]
                if not future_dates.empty:
                    next_date = future_dates.index[0]
                    result["upcoming_earnings"] = next_date.strftime("%Y-%m-%d")

            # Get recent earnings
            if earnings is not None and not earnings.empty:
                for year, row in earnings.tail(4).iterrows():
                    result["recent_earnings"].append({
                        "year": int(year),
                        "revenue": row.get('Revenue'),
                        "earnings": row.get('Earnings')
                    })

            return result

        except Exception as e:
            logger.error(f"Error fetching earnings for {symbol}: {e}")
            return {"error": f"Could not fetch earnings for {symbol}"}

    @staticmethod
    def compare_stocks(symbols: List[str]) -> Dict:
        """
        Compare multiple stocks side-by-side

        Args:
            symbols: List of stock ticker symbols

        Returns:
            Dict with comparison data
        """
        try:
            comparison = {
                "symbols": [],
                "metrics": []
            }

            for symbol in symbols:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                comparison["symbols"].append(symbol.upper())
                comparison["metrics"].append({
                    "symbol": symbol.upper(),
                    "current_price": info.get('currentPrice'),
                    "market_cap": info.get('marketCap'),
                    "pe_ratio": info.get('trailingPE'),
                    "dividend_yield": info.get('dividendYield'),
                    "52w_change": info.get('52WeekChange'),
                    "revenue_growth": info.get('revenueGrowth'),
                    "profit_margin": info.get('profitMargins')
                })

            return comparison

        except Exception as e:
            logger.error(f"Error comparing stocks: {e}")
            return {"error": "Could not compare stocks"}


# Format helpers
def format_quote(quote: Dict) -> str:
    """Format quote data for display"""
    if "error" in quote:
        return quote["error"]

    # Calculate change symbol
    change_symbol = "+" if quote.get("change", 0) >= 0 else ""

    # Format optional values safely
    change_str = f"{change_symbol}${quote['change']:.2f}" if quote.get('change') is not None else "N/A"
    change_pct_str = f"({change_symbol}{quote['change_percent']:.2f}%)" if quote.get(
        'change_percent') is not None else ""

    day_low_str = f"${quote['day_low']:.2f}" if quote.get('day_low') is not None else "N/A"
    day_high_str = f"${quote['day_high']:.2f}" if quote.get('day_high') is not None else "N/A"

    week_52_low_str = f"${quote['52_week_low']:.2f}" if quote.get('52_week_low') is not None else "N/A"
    week_52_high_str = f"${quote['52_week_high']:.2f}" if quote.get('52_week_high') is not None else "N/A"

    volume_str = f"{quote['volume']:,}" if quote.get('volume') is not None else "N/A"
    market_cap_str = f"${quote['market_cap']:,}" if quote.get('market_cap') is not None else "N/A"

    pe_ratio_str = f"{quote['pe_ratio']:.2f}" if quote.get('pe_ratio') is not None else "N/A"

    dividend_yield_str = f"{quote['dividend_yield']:.2%}" if quote.get('dividend_yield') is not None else "N/A"

    return f"""
**{quote['company_name']} ({quote['symbol']})**

Current Price: ${quote['current_price']:.2f}
Change: {change_str} {change_pct_str}
Previous Close: ${quote['previous_close']:.2f}

Day Range: {day_low_str} - {day_high_str}
52-Week Range: {week_52_low_str} - {week_52_high_str}

Volume: {volume_str}
Market Cap: {market_cap_str}
P/E Ratio: {pe_ratio_str}
Dividend Yield: {dividend_yield_str}
"""


def format_dividends(dividends: Dict) -> str:
    """Format dividend data for display"""
    if "error" in dividends:
        return dividends["error"]

    if "message" in dividends:
        return f"{dividends['symbol']}: {dividends['message']}"

    output = f"""
**{dividends['symbol']} Dividend History**

Annual Dividend: ${dividends['annual_dividend']:.2f}
Total Payments: {dividends['total_dividends_paid']}

Recent Dividends:
"""

    for div in dividends['recent_dividends']:
        output += f"  • {div['date']}: ${div['amount']:.2f}\n"

    return output