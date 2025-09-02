"""
server.py
ETF Data MCP Server

ETF 데이터 조회 및 포트폴리오 분석을 위한 MCP 서버입니다.
yfinance 라이브러리를 사용하여 실시간 ETF 가격 데이터를 제공합니다.

주요 기능:
- get_available_products: 투자 가능한 ETF 목록 조회
- get_product_data: 특정 ETF의 가격 데이터 조회 (최근 3개월)
"""

import yfinance as yf
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

# MCP 서버 생성 (AgentCore Runtime 호환)
mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# ================================
# ETF 상품 데이터
# ================================

SUPPORTED_PRODUCTS = {
    # 💵 배당주 (안정적 배당) - 4개
    "SCHD": "Schwab US Dividend Equity ETF - 미국 고품질 배당주",
    "VYM": "Vanguard High Dividend Yield ETF - 고배당 ETF",
    "NOBL": "ProShares S&P 500 Dividend Aristocrats ETF - 배당 귀족주",
    "DVY": "iShares Select Dividend ETF - 선별 배당주",
    
    # 🚀 성장주 (기술/바이오) - 6개
    "QQQ": "Invesco QQQ ETF - 나스닥 100 기술주",
    "XLK": "Technology Select Sector SPDR Fund - 기술 섹터",
    "ARKK": "ARK Innovation ETF - 혁신 기술주",
    "XLV": "Health Care Select Sector SPDR Fund - 헬스케어/바이오",
    "ARKG": "ARK Genomic Revolution ETF - 유전체학/바이오",
    "SOXX": "iShares Semiconductor ETF - 반도체 ETF",
    
    # 💎 가치주 (저평가 우량주) - 4개
    "VTV": "Vanguard Value ETF - 대형 가치주",
    "VBR": "Vanguard Small-Cap Value ETF - 소형 가치주",
    "IWD": "iShares Russell 1000 Value ETF - 러셀 1000 가치주",
    "VTEB": "Vanguard Tax-Exempt Bond ETF - 세금 우대 채권",
    
    # 🏢 리츠 (부동산 투자) - 3개
    "VNQ": "Vanguard Real Estate Investment Trust ETF - 미국 리츠",
    "VNQI": "Vanguard Global ex-U.S. Real Estate ETF - 해외 리츠",
    "SCHH": "Schwab US REIT ETF - 미국 부동산 투자신탁",
    
    # 📊 ETF (분산 투자) - 5개
    "SPY": "SPDR S&P 500 ETF - 미국 대형주 500개",
    "VTI": "Vanguard Total Stock Market ETF - 미국 전체 주식시장",
    "VOO": "Vanguard S&P 500 ETF - S&P 500 지수 추종",
    "IVV": "iShares Core S&P 500 ETF - S&P 500 저비용",
    "ITOT": "iShares Core S&P Total US Stock Market ETF - 전체 시장",
    
    # 🌍 해외 주식 - 4개
    "VEA": "Vanguard FTSE Developed Markets ETF - 선진국 주식",
    "VWO": "Vanguard FTSE Emerging Markets ETF - 신흥국 주식",
    "VXUS": "Vanguard Total International Stock ETF - 국제 주식",
    "EFA": "iShares MSCI EAFE ETF - 유럽/아시아/극동",
    
    # 🛡️ 채권 (안전 자산) - 3개
    "BND": "Vanguard Total Bond Market ETF - 미국 전체 채권",
    "AGG": "iShares Core U.S. Aggregate Bond ETF - 종합 채권",
    "TLT": "iShares 20+ Year Treasury Bond ETF - 장기 국채",
    
    # 🥇 원자재/금 - 3개
    "GLD": "SPDR Gold Shares - 금 현물 ETF",
    "SLV": "iShares Silver Trust - 은 현물 ETF",
    "DBC": "Invesco DB Commodity Index Tracking Fund - 종합 원자재"
}

# ================================
# MCP 도구 정의
# ================================

@mcp.tool()
def get_available_products() -> dict:
    """
    투자 가능한 ETF 상품 목록 반환
    
    미국 주요 ETF 30개를 카테고리별로 분류하여 제공합니다.
    포트폴리오 구성 시 다양한 자산군에서 선택할 수 있도록 구성되었습니다.
    
    Returns:
        dict: ETF 티커와 설명이 포함된 딕셔너리
    """
    print(f"📋 ETF 상품 목록 조회: {len(SUPPORTED_PRODUCTS)}개 상품 반환")
    return SUPPORTED_PRODUCTS


@mcp.tool()
def get_product_data(ticker: str) -> dict:
    """
    특정 ETF의 가격 데이터 조회
    
    yfinance 라이브러리를 사용하여 지정된 ETF의 최근 3개월 가격 데이터를 조회합니다.
    포트폴리오 분석 및 트렌드 분석에 사용됩니다.
    
    Args:
        ticker (str): ETF 티커 심볼 (예: 'QQQ', 'SPY', 'ARKK')
        
    Returns:
        dict: 날짜별 종가 데이터 또는 오류 정보
    """
    try:
        # 날짜 범위 설정 (최근 100일, 약 3개월)
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=100)
        
        print(f"📈 {ticker} 가격 데이터 조회: {start_date} ~ {end_date}")
        
        # yfinance를 사용하여 ETF 데이터 조회
        etf = yf.Ticker(ticker)
        hist = etf.history(start=start_date, end=end_date)
        
        # 데이터 유효성 검사
        if hist.empty:
            print(f"⚠️ {ticker}: 데이터가 없습니다")
            return {"error": f"No data available for ticker: {ticker}"}
        
        # 종가 데이터를 날짜별 딕셔너리로 변환
        product_data = {
            ticker: {
                date.strftime('%Y-%m-%d'): round(float(price), 2) 
                for date, price in hist['Close'].items()
            }
        }
        
        data_count = len(product_data[ticker])
        print(f"✅ {ticker}: {data_count}일 데이터 조회 완료")
        
        return product_data

    except Exception as e:
        error_msg = f"Error fetching {ticker} price data: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}


# ================================
# MCP 서버 실행
# ================================

if __name__ == "__main__":
    print("🚀 ETF Data MCP Server 시작")
    mcp.run(transport="streamable-http")
