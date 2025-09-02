"""
server.py

ETF Data MCP Server - 실시간 ETF 데이터 조회
"""

import yfinance as yf
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# 30개 ETF 상품 목록
PRODUCTS = {
    # 배당주 (4개)
    "SCHD": "Schwab US Dividend Equity ETF - 미국 고품질 배당주",
    "VYM": "Vanguard High Dividend Yield ETF - 고배당 ETF",
    "NOBL": "ProShares S&P 500 Dividend Aristocrats ETF - 배당 귀족주",
    "DVY": "iShares Select Dividend ETF - 선별 배당주",
    
    # 성장주 (6개)
    "QQQ": "Invesco QQQ ETF - 나스닥 100 기술주",
    "XLK": "Technology Select Sector SPDR Fund - 기술 섹터",
    "ARKK": "ARK Innovation ETF - 혁신 기술주",
    "XLV": "Health Care Select Sector SPDR Fund - 헬스케어/바이오",
    "ARKG": "ARK Genomic Revolution ETF - 유전체학/바이오",
    "SOXX": "iShares Semiconductor ETF - 반도체 ETF",
    
    # 가치주 (4개)
    "VTV": "Vanguard Value ETF - 대형 가치주",
    "VBR": "Vanguard Small-Cap Value ETF - 소형 가치주",
    "IWD": "iShares Russell 1000 Value ETF - 러셀 1000 가치주",
    "VTEB": "Vanguard Tax-Exempt Bond ETF - 세금 우대 채권",
    
    # 리츠 (3개)
    "VNQ": "Vanguard Real Estate Investment Trust ETF - 미국 리츠",
    "VNQI": "Vanguard Global ex-U.S. Real Estate ETF - 해외 리츠",
    "SCHH": "Schwab US REIT ETF - 미국 부동산 투자신탁",
    
    # ETF (5개)
    "SPY": "SPDR S&P 500 ETF - 미국 대형주 500개",
    "VTI": "Vanguard Total Stock Market ETF - 미국 전체 주식시장",
    "VOO": "Vanguard S&P 500 ETF - S&P 500 지수 추종",
    "IVV": "iShares Core S&P 500 ETF - S&P 500 저비용",
    "ITOT": "iShares Core S&P Total US Stock Market ETF - 전체 시장",
    
    # 해외 주식 (4개)
    "VEA": "Vanguard FTSE Developed Markets ETF - 선진국 주식",
    "VWO": "Vanguard FTSE Emerging Markets ETF - 신흥국 주식",
    "VXUS": "Vanguard Total International Stock ETF - 국제 주식",
    "EFA": "iShares MSCI EAFE ETF - 유럽/아시아/극동",
    
    # 채권 (3개)
    "BND": "Vanguard Total Bond Market ETF - 미국 전체 채권",
    "AGG": "iShares Core U.S. Aggregate Bond ETF - 종합 채권",
    "TLT": "iShares 20+ Year Treasury Bond ETF - 장기 국채",
    
    # 원자재 (3개)
    "GLD": "SPDR Gold Shares - 금 현물 ETF",
    "SLV": "iShares Silver Trust - 은 현물 ETF",
    "DBC": "Invesco DB Commodity Index Tracking Fund - 종합 원자재"
}

@mcp.tool()
def get_available_products() -> dict:
    """투자 가능한 ETF 상품 목록 반환"""
    return PRODUCTS

@mcp.tool()
def get_product_data(ticker: str) -> dict:
    """특정 ETF의 최근 3개월 가격 데이터 조회"""
    try:
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=100)
        
        etf = yf.Ticker(ticker)
        hist = etf.history(start=start_date, end=end_date)
        
        if hist.empty:
            return {"error": f"No data available for ticker: {ticker}"}
        
        return {
            ticker: {
                date.strftime('%Y-%m-%d'): round(float(price), 2) 
                for date, price in hist['Close'].items()
            }
        }
    except Exception as e:
        return {"error": f"Error fetching {ticker} price data: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
