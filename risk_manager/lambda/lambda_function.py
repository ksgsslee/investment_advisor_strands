"""
lambda_function.py
Risk Manager Lambda 함수

뉴스 기반 리스크 분석 및 시장 지표 조회를 위한 AWS Lambda 함수입니다.
yfinance 라이브러리를 사용하여 실시간 뉴스 및 거시경제 데이터를 제공합니다.

주요 기능:
- get_product_news: ETF별 최신 뉴스 조회 (상위 5개)
- get_market_data: 주요 거시경제 지표 조회 (달러지수, 국채수익률, VIX, 원유)
"""

import os
import json
import yfinance as yf
from datetime import datetime, timedelta

# ================================
# 비즈니스 로직 함수들
# ================================

def get_product_news(ticker, top_n=5):
    """
    특정 ETF의 최신 뉴스 조회
    
    yfinance 라이브러리를 사용하여 지정된 ETF의 최신 뉴스를 조회합니다.
    리스크 분석 및 시장 센티먼트 분석에 사용됩니다.
    
    Args:
        ticker (str): ETF 티커 심볼 (예: 'QQQ', 'SPY', 'GLD')
        top_n (int): 조회할 뉴스 개수 (기본값: 5개)
        
    Returns:
        dict: 뉴스 데이터 또는 오류 정보
        
    Example:
        {
            "ticker": "QQQ",
            "news": [
                {
                    "title": "Nasdaq 100 ETF Sees Strong Inflows",
                    "summary": "Technology sector momentum continues...",
                    "publish_date": "2024-08-20"
                }
            ]
        }
        
    Note:
        - 상위 5개 최신 뉴스 조회
        - 제목, 요약, 발행일 정보 포함
        - 뉴스가 없거나 오류 시 적절한 에러 메시지 반환
    """
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
    """
    주요 거시경제 지표 데이터 조회
    
    리스크 분석에 필요한 핵심 거시경제 지표들을 실시간으로 조회합니다.
    시나리오 플래닝 및 포트폴리오 조정 전략 수립에 활용됩니다.
    
    Returns:
        dict: 거시경제 지표 데이터 또는 오류 정보
        
    Example:
        {
            "us_dollar_index": {
                "description": "미국 달러 강세를 나타내는 지수",
                "value": 103.45,
                "ticker": "DX-Y.NYB"
            },
            "vix_volatility_index": {
                "description": "시장의 변동성을 나타내는 VIX 지수",
                "value": 18.75,
                "ticker": "^VIX"
            }
        }
        
    Note:
        - 5개 핵심 지표: 달러지수, 10년/2년 국채수익률, VIX, 원유가격
        - 실시간 시장 가격 데이터 제공
        - 각 지표별 설명과 티커 정보 포함
    """
    try:
        # 주요 거시경제 지표 정의
        market_indicators = {
            "us_dollar_index": {"ticker": "DX-Y.NYB", "description": "미국 달러 강세 지수"},
            "us_10y_treasury_yield": {"ticker": "^TNX", "description": "미국 10년 국채 수익률 (%)"},
            "us_2y_treasury_yield": {"ticker": "^IRX", "description": "미국 3개월 국채 수익률 (%)"},
            "vix_volatility_index": {"ticker": "^VIX", "description": "VIX 변동성 지수"},
            "crude_oil_price": {"ticker": "CL=F", "description": "WTI 원유 선물 가격 (USD/배럴)"}
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

# ================================
# Lambda 핸들러 함수
# ================================

def lambda_handler(event, context):
    """
    AWS Lambda 메인 핸들러 함수
    
    AgentCore Gateway에서 호출되는 Lambda 함수의 진입점입니다.
    도구 이름에 따라 적절한 비즈니스 로직 함수를 호출합니다.
    
    Args:
        event (dict): Lambda 이벤트 객체 (도구 파라미터 포함)
        context (object): Lambda 컨텍스트 객체 (도구 이름 포함)
        
    Returns:
        dict: HTTP 응답 형태의 결과
        
    Supported Tools:
        - get_product_news: ETF별 최신 뉴스 조회
        - get_market_data: 주요 거시경제 지표 조회
    """
    try:
        # 디버깅을 위한 로그 출력
        print("📥 Risk Manager Lambda 호출 정보:")
        print(f"   Context: {context.client_context}")
        print(f"   Event: {event}")
        
        # AgentCore에서 전달된 도구 이름 추출
        tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        
        # 도구 이름에서 실제 함수명 추출
        function_name = tool_name.split('___')[-1] if '___' in tool_name else tool_name
        
        print(f"🔧 실행할 함수: {function_name}")
        
        # 함수명에 따른 비즈니스 로직 실행
        if function_name == 'get_product_news':
            # ETF 뉴스 조회
            ticker = event.get('ticker', "")
            if not ticker:
                output = {"error": "ticker parameter is required"}
                print("❌ ticker 파라미터가 누락되었습니다")
            else:
                output = get_product_news(ticker)
                
        elif function_name == 'get_market_data':
            # 거시경제 지표 조회
            output = get_market_data()
                
        else:
            # 지원하지 않는 함수명
            output = {"error": f"Invalid function: {function_name}"}
            print(f"❌ 지원하지 않는 함수: {function_name}")
        
        # 성공 응답 반환
        response = {
            'statusCode': 200, 
            'body': json.dumps(output, ensure_ascii=False)
        }
        
        print(f"✅ 응답 생성 완료: {len(str(output))} 문자")
        return response
        
    except Exception as e:
        # 오류 발생 시 에러 응답 반환
        error_msg = f"Risk Manager Lambda execution error: {str(e)}"
        print(f"❌ {error_msg}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({"error": error_msg}, ensure_ascii=False)
        }