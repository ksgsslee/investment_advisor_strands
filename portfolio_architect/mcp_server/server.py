"""
server.py

ETF Data MCP Server - 실시간 ETF 데이터 조회
"""

import yfinance as yf
import numpy as np
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
def analyze_etf_performance(ticker: str) -> dict:
    """개별 ETF 성과 분석 (몬테카를로 시뮬레이션 포함)"""
    try:
        # 2년치 데이터 수집
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=504)  # 약 2년
        
        etf = yf.Ticker(ticker)
        hist = etf.history(start=start_date, end=end_date)
        
        if hist.empty:
            return {"error": f"No data available for ticker: {ticker}"}
        
        # 일일 수익률 계산
        daily_returns = hist['Close'].pct_change().dropna()
        
        # 연간 수익률과 변동성 계산
        annual_return = np.mean(daily_returns) * 252
        annual_volatility = np.std(daily_returns) * np.sqrt(252)
        
        # 몬테카를로 시뮬레이션 (500회로 간소화)
        n_simulations = 500
        n_days = 252  # 1년
        
        # 1년 후 수익률 분포 계산 (100만원 기준)
        base_amount = 1000000
        final_values = []
        
        for _ in range(n_simulations):
            # 정규분포에서 일일 수익률 샘플링
            simulated_returns = np.random.normal(
                annual_return / 252, 
                annual_volatility / np.sqrt(252), 
                n_days
            )
            
            # 복리 계산
            final_value = base_amount * np.prod(1 + simulated_returns)
            final_values.append(final_value)
        
        final_values = np.array(final_values)
        
        # 간단한 지표들만 계산
        expected_return_pct = (np.mean(final_values) / base_amount - 1) * 100
        loss_probability = np.sum(final_values < base_amount) / n_simulations * 100
        
        # 수익률 구간별 분포 계산
        return_percentages = (final_values / base_amount - 1) * 100
        
        distribution = {
            "-20% 이하": int(np.sum(return_percentages <= -20)),
            "-20% ~ -10%": int(np.sum((return_percentages > -20) & (return_percentages <= -10))),
            "-10% ~ 0%": int(np.sum((return_percentages > -10) & (return_percentages <= 0))),
            "0% ~ 10%": int(np.sum((return_percentages > 0) & (return_percentages <= 10))),
            "10% ~ 20%": int(np.sum((return_percentages > 10) & (return_percentages <= 20))),
            "20% ~ 30%": int(np.sum((return_percentages > 20) & (return_percentages <= 30))),
            "30% 이상": int(np.sum(return_percentages > 30))
        }
        
        return {
            "ticker": ticker,
            "expected_annual_return": round(expected_return_pct, 1),
            "loss_probability": round(loss_probability, 1),
            "historical_annual_return": round(annual_return * 100, 1),
            "volatility": round(annual_volatility * 100, 1),
            "return_distribution": distribution
        }
        
    except Exception as e:
        return {"error": f"ETF analysis failed for {ticker}: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
