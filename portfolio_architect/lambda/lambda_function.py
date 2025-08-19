import os
import json
import yfinance as yf
from datetime import datetime, timedelta


def get_named_parameter(event, name):
    # Get the value of a specific parameter from the Lambda event
    for param in event['parameters']:
        if param['name'] == name:
            return param['value']
    return None


def get_available_products():
    """미국 유명 ETF 30개 목록 반환"""
    products = {
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
    return products


def get_product_data(ticker):
    try:
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=100)

        product_data = {}
        etf = yf.Ticker(ticker)
        hist = etf.history(start=start_date, end=end_date)

        # Store closing prices for each asset
        product_data[ticker] = {
            date.strftime('%Y-%m-%d'): round(price, 2) for date, price in hist['Close'].items()
        }

        return product_data

    except Exception as e:
        print(f"Error fetching asset prices: {e}")
        return {"error": str(e)}


def lambda_handler(event, context):
    print(context.client_context)
    print(event)
    tool_name = context.client_context.custom['bedrockAgentCoreToolName']
    
    # delimeter
    function_name = tool_name.split('___')[-1] if '___' in tool_name else tool_name

    if 'get_available_products' == function_name:
        output = get_available_products()
    elif 'get_product_data' == function_name:
        ticker = event.get('ticker', "")
        output = get_product_data(ticker)
    else:
        output = 'Invalid function'

    return {'statusCode': 200, 'body': json.dumps(output, ensure_ascii=False)}
