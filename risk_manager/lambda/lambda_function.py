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
# 유틸리티 함수들
# ================================

def get_named_parameter(event, name):
    """
    Lambda 이벤트에서 특정 파라미터 값 추출
    
    Args:
        event (dict): Lambda 이벤트 객체
        name (str): 추출할 파라미터 이름
        
    Returns:
        str: 파라미터 값 또는 None
    """
    for param in event.get('parameters', []):
        if param['name'] == name:
            return param['value']
    return None

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
        print(f"📰 {ticker} 뉴스 데이터 조회 시작...")
        
        # yfinance를 사용하여 ETF 뉴스 조회
        stock = yf.Ticker(ticker)
        news = stock.news[:top_n]
        
        # 뉴스 데이터 유효성 검사
        if not news:
            print(f"⚠️ {ticker}: 뉴스 데이터가 없습니다")
            return {
                "ticker": ticker,
                "news": [],
                "message": f"No news available for {ticker}"
            }
        
        # 뉴스 데이터 포맷팅
        formatted_news = []
        for item in news:
            try:
                # yfinance 뉴스 구조에 따른 데이터 추출
                title = item.get("title", "")
                summary = item.get("summary", "")
                
                # 발행일 처리 (다양한 형식 지원)
                publish_date = ""
                if "providerPublishTime" in item:
                    # Unix timestamp를 날짜로 변환
                    timestamp = item["providerPublishTime"]
                    publish_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                elif "pubDate" in item:
                    # 문자열 날짜 처리
                    pub_date = item["pubDate"]
                    if isinstance(pub_date, str) and len(pub_date) >= 10:
                        publish_date = pub_date[:10]
                
                news_item = {
                    "title": title,
                    "summary": summary,
                    "publish_date": publish_date,
                    "link": item.get("link", "")
                }
                formatted_news.append(news_item)
                
            except Exception as e:
                print(f"⚠️ 뉴스 항목 처리 오류: {str(e)}")
                continue
        
        result = {
            "ticker": ticker,
            "news": formatted_news,
            "count": len(formatted_news)
        }
        
        print(f"✅ {ticker}: {len(formatted_news)}개 뉴스 조회 완료")
        return result
        
    except Exception as e:
        error_msg = f"Error fetching news for {ticker}: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "ticker": ticker,
            "error": error_msg,
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
        print("📊 거시경제 지표 데이터 조회 시작...")
        
        # 주요 거시경제 지표 정의
        market_indicators = {
            "us_dollar_index": {
                "ticker": "DX-Y.NYB", 
                "description": "미국 달러 강세를 나타내는 지수"
            },
            "us_10y_treasury_yield": {
                "ticker": "^TNX", 
                "description": "미국 10년 국채 수익률 (%)"
            },
            "us_2y_treasury_yield": {
                "ticker": "^IRX", 
                "description": "미국 3개월 국채 수익률 (%)"
            },
            "vix_volatility_index": {
                "ticker": "^VIX", 
                "description": "시장의 변동성을 나타내는 VIX 지수"
            },
            "crude_oil_price": {
                "ticker": "CL=F", 
                "description": "WTI 원유 선물 가격 (USD/배럴)"
            }
        }
        
        market_data = {}
        successful_queries = 0
        
        # 각 지표별 데이터 조회
        for key, info in market_indicators.items():
            try:
                ticker_symbol = info["ticker"]
                print(f"📈 {key} ({ticker_symbol}) 조회 중...")
                
                # yfinance를 사용하여 지표 데이터 조회
                ticker = yf.Ticker(ticker_symbol)
                
                # 다양한 가격 정보 시도 (지표별로 사용 가능한 필드가 다름)
                market_price = None
                
                # 1. 기본 정보에서 가격 추출 시도
                info_data = ticker.info
                price_fields = [
                    'regularMarketPrice',
                    'regularMarketPreviousClose', 
                    'previousClose',
                    'ask',
                    'bid',
                    'open'
                ]
                
                for field in price_fields:
                    if field in info_data and info_data[field] is not None:
                        market_price = float(info_data[field])
                        break
                
                # 2. 최근 히스토리 데이터에서 추출 시도
                if market_price is None:
                    try:
                        hist = ticker.history(period="5d")
                        if not hist.empty:
                            market_price = float(hist['Close'].iloc[-1])
                    except:
                        pass
                
                # 3. 기본값 설정 (데이터를 가져올 수 없는 경우)
                if market_price is None:
                    market_price = 0.0
                    print(f"⚠️ {key}: 가격 데이터를 가져올 수 없음, 기본값 사용")
                
                market_data[key] = {
                    "description": info["description"],
                    "value": round(market_price, 2),
                    "ticker": ticker_symbol,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                successful_queries += 1
                print(f"✅ {key}: {market_price}")
                
            except Exception as e:
                print(f"⚠️ {key} 조회 실패: {str(e)}")
                # 실패한 지표도 기본 구조로 포함
                market_data[key] = {
                    "description": info["description"],
                    "value": 0.0,
                    "ticker": info["ticker"],
                    "error": str(e),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        
        print(f"✅ 거시경제 지표 조회 완료: {successful_queries}/{len(market_indicators)}개 성공")
        
        # 메타데이터 추가
        market_data["_metadata"] = {
            "total_indicators": len(market_indicators),
            "successful_queries": successful_queries,
            "query_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": "Yahoo Finance via yfinance"
        }
        
        return market_data
        
    except Exception as e:
        error_msg = f"Error fetching market data: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "error": error_msg,
            "_metadata": {
                "query_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "failed"
            }
        }

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