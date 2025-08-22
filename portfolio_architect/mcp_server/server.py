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
    # 📈 주요 지수 ETF (5개) - 미국 대표 지수 추종
    "SPY": "SPDR S&P 500 ETF - 미국 대형주 500개 기업",
    "QQQ": "Invesco QQQ ETF - 나스닥 100 기술주",
    "VTI": "Vanguard Total Stock Market ETF - 미국 전체 주식시장",
    "VOO": "Vanguard S&P 500 ETF - S&P 500 지수 추종",
    "IVV": "iShares Core S&P 500 ETF - S&P 500 저비용 ETF",
    
    # 🌍 국제/신흥국 ETF (5개) - 해외 분산투자
    "VEA": "Vanguard FTSE Developed Markets ETF - 선진국 주식",
    "VWO": "Vanguard FTSE Emerging Markets ETF - 신흥국 주식",
    "VXUS": "Vanguard Total International Stock ETF - 국제 주식",
    "EFA": "iShares MSCI EAFE ETF - 유럽/아시아/극동 선진국",
    "EEM": "iShares MSCI Emerging Markets ETF - 신흥국 주식",
    
    # 💰 채권/안전자산 ETF (5개) - 안정성과 인플레이션 헤지
    "BND": "Vanguard Total Bond Market ETF - 미국 전체 채권",
    "AGG": "iShares Core U.S. Aggregate Bond ETF - 미국 종합 채권",
    "TLT": "iShares 20+ Year Treasury Bond ETF - 장기 국채",
    "GLD": "SPDR Gold Shares - 금 현물 ETF",
    "SLV": "iShares Silver Trust - 은 현물 ETF",
    
    # 🏢 섹터별 ETF (8개) - 특정 산업 집중투자
    "XLF": "Financial Select Sector SPDR Fund - 금융 섹터",
    "XLK": "Technology Select Sector SPDR Fund - 기술 섹터",
    "XLE": "Energy Select Sector SPDR Fund - 에너지 섹터",
    "XLV": "Health Care Select Sector SPDR Fund - 헬스케어 섹터",
    "XLI": "Industrial Select Sector SPDR Fund - 산업 섹터",
    "XLP": "Consumer Staples Select Sector SPDR Fund - 필수소비재",
    "XLY": "Consumer Discretionary Select Sector SPDR Fund - 임의소비재",
    "VNQ": "Vanguard Real Estate Investment Trust ETF - 리츠",
    
    # 🚀 혁신/성장 ETF (5개) - 고성장 테마 투자
    "ARKK": "ARK Innovation ETF - 혁신 기술주",
    "ARKQ": "ARK Autonomous Technology & Robotics ETF - 자율주행/로봇",
    "ARKW": "ARK Next Generation Internet ETF - 차세대 인터넷",
    "ARKG": "ARK Genomic Revolution ETF - 유전체학 혁명",
    "ARKF": "ARK Fintech Innovation ETF - 핀테크 혁신",
    
    # 💵 배당 ETF (2개) - 안정적인 배당 수익
    "SCHD": "Schwab US Dividend Equity ETF - 미국 배당주",
    "VYM": "Vanguard High Dividend Yield ETF - 고배당 ETF"
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
    print(f"📋 지원 ETF: {len(SUPPORTED_PRODUCTS)}개")
    print("🔧 사용 가능한 도구:")
    print("   - get_available_products: ETF 상품 목록 조회")
    print("   - get_product_data: 특정 ETF 가격 데이터 조회")
    print("🌐 서버 주소: http://0.0.0.0:8000/mcp")
    
    mcp.run(transport="streamable-http")