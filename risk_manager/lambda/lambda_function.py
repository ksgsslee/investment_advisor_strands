"""
lambda_function.py

Risk Manager Lambda 함수
yfinance 라이브러리를 사용하여 실시간 뉴스 및 거시경제 데이터를 제공합니다.
"""

import os
import json
import yfinance as yf
from datetime import datetime, timedelta

def get_product_news(ticker, top_n=5):
    """특정 ETF의 최신 뉴스 조회"""
    try:
        # yfinance를 사용하여 ETF 뉴스 조회
        stock = yf.Ticker(ticker)
        news = stock.news[:top_n]
        
        # 뉴스 데이터 포맷팅
        formatted_news = []
        for item in news:
            # content 객체에서 데이터 추출
            content = item.get("content", item)
            
            title = content.get("title", "")
            summary = content.get("summary", "")
            
            # 날짜 처리
            pub_date = content.get("pubDate", "")
            publish_date = pub_date.split("T")[0] if "T" in pub_date else pub_date[:10] if len(pub_date) >= 10 else ""
            
            # 링크 처리
            link = ""
            if "canonicalUrl" in content:
                link = content["canonicalUrl"].get("url", "")
            
            news_item = {
                "title": title,
                "summary": summary,
                "publish_date": publish_date,
                "link": link
            }
            formatted_news.append(news_item)
        
        return {
            "ticker": ticker,
            "news": formatted_news,
            "count": len(formatted_news)
        }
        
    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "news": []
        }

def get_market_data():
    """주요 거시경제 지표 데이터 조회"""
    try:
        # 주요 거시경제 지표 정의 (7개)
        market_indicators = {
            # 금리 지표 (3개)
            "us_2y_treasury_yield": {"ticker": "^IRX", "description": "미국 2년 국채 수익률 (%)"},
            "us_10y_treasury_yield": {"ticker": "^TNX", "description": "미국 10년 국채 수익률 (%)"},
            "us_dollar_index": {"ticker": "DX-Y.NYB", "description": "미국 달러 강세 지수"},
            
            # 변동성 및 원자재 (3개)
            "vix_volatility_index": {"ticker": "^VIX", "description": "VIX 변동성 지수 (공포 지수)"},
            "crude_oil_price": {"ticker": "CL=F", "description": "WTI 원유 선물 가격 (USD/배럴)"},
            "gold_price": {"ticker": "GC=F", "description": "금 선물 가격 (USD/온스)"},
            
            # 주식 지수 (1개)
            "sp500_index": {"ticker": "^GSPC", "description": "S&P 500 지수"}
        }
        
        market_data = {}
        
        # 각 지표별 데이터 조회
        for key, info in market_indicators.items():
            ticker_symbol = info["ticker"]
            
            try:
                ticker = yf.Ticker(ticker_symbol)
                info_data = ticker.info
                
                # 가격 정보 추출
                market_price = (info_data.get('regularMarketPrice') or 
                              info_data.get('regularMarketPreviousClose') or 
                              info_data.get('previousClose') or 0.0)
                
                market_data[key] = {
                    "description": info["description"],
                    "value": round(float(market_price), 2),
                    "ticker": ticker_symbol
                }
                
            except:
                market_data[key] = {
                    "description": info["description"],
                    "value": 0.0,
                    "ticker": ticker_symbol
                }
        
        return market_data
        
    except Exception as e:
        return {"error": f"Error fetching market data: {str(e)}"}

def get_geopolitical_indicators():
    """지정학적 리스크 지표 데이터 조회"""
    try:
        # 지정학적 리스크 지표 정의 (주요 지역 ETF 5개)
        geopolitical_indicators = {
            "china_market": {"ticker": "ASHR", "description": "중국 A주 ETF"},
            "emerging_markets": {"ticker": "EEM", "description": "신흥국 ETF"},
            "europe_market": {"ticker": "VGK", "description": "유럽 ETF"},
            "japan_market": {"ticker": "EWJ", "description": "일본 ETF"},
            "korea_market": {"ticker": "EWY", "description": "한국 ETF"}
        }
        
        geopolitical_data = {}
        
        # 각 지표별 데이터 조회
        for key, info in geopolitical_indicators.items():
            ticker_symbol = info["ticker"]
            
            try:
                ticker = yf.Ticker(ticker_symbol)
                info_data = ticker.info
                
                # 가격 정보 추출
                market_price = (info_data.get('regularMarketPrice') or 
                              info_data.get('regularMarketPreviousClose') or 
                              info_data.get('previousClose') or 0.0)
                
                geopolitical_data[key] = {
                    "description": info["description"],
                    "value": round(float(market_price), 2),
                    "ticker": ticker_symbol
                }
                
            except:
                geopolitical_data[key] = {
                    "description": info["description"],
                    "value": 0.0,
                    "ticker": ticker_symbol
                }
        
        return geopolitical_data
        
    except Exception as e:
        return {"error": f"Error fetching geopolitical data: {str(e)}"}

def lambda_handler(event, context):
    """AWS Lambda 메인 핸들러 함수"""
    try:
        tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        function_name = tool_name.split('___')[-1] if '___' in tool_name else tool_name
        
        if function_name == 'get_product_news':
            ticker = event.get('ticker', "")
            if not ticker:
                output = {"error": "ticker parameter is required"}
            else:
                output = get_product_news(ticker)
                
        elif function_name == 'get_market_data':
            output = get_market_data()
            
        elif function_name == 'get_geopolitical_indicators':
            output = get_geopolitical_indicators()
                
        else:
            output = {"error": f"Invalid function: {function_name}"}
        
        return {
            'statusCode': 200, 
            'body': json.dumps(output, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)}, ensure_ascii=False)
        }