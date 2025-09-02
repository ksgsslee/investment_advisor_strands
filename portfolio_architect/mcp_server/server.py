"""
server.py

ETF Data MCP Server - 실시간 ETF 데이터 조회
"""

import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

@mcp.tool()
def calculate_correlation(tickers: list) -> dict:
    """선택된 ETF들 간 상관관계 매트릭스 계산"""
    try:
        import numpy as np
        from datetime import datetime, timedelta
        
        # 2년치 데이터로 상관관계 계산
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=504)
        
        # 모든 ETF 데이터 수집
        etf_data = {}
        for ticker in tickers:
            etf = yf.Ticker(ticker)
            hist = etf.history(start=start_date, end=end_date)
            if not hist.empty:
                etf_data[ticker] = hist['Close'].pct_change().dropna()
        
        # 상관관계 매트릭스 생성
        correlation_matrix = {}
        for ticker1 in tickers:
            correlation_matrix[ticker1] = {}
            for ticker2 in tickers:
                if ticker1 == ticker2:
                    correlation_matrix[ticker1][ticker2] = 1.0
                elif ticker1 in etf_data and ticker2 in etf_data:
                    # 공통 날짜 찾기
                    common_dates = etf_data[ticker1].index.intersection(etf_data[ticker2].index)
                    if len(common_dates) > 100:  # 충분한 데이터가 있을 때만
                        returns1 = etf_data[ticker1][common_dates]
                        returns2 = etf_data[ticker2][common_dates]
                        
                        correlation = np.corrcoef(returns1, returns2)[0, 1]
                        correlation_matrix[ticker1][ticker2] = round(correlation, 3)
                    else:
                        correlation_matrix[ticker1][ticker2] = 0.0
                else:
                    correlation_matrix[ticker1][ticker2] = 0.0
        
        return {
            "correlation_matrix": correlation_matrix
        }
        
    except Exception as e:
        return {"error": f"Correlation calculation failed: {str(e)}"}

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
        
        # 몬테카를로 시뮬레이션 (1000회로 간소화)
        n_simulations = 1000
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
