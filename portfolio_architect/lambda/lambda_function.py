"""
lambda_function.py
Portfolio Architect Lambda 함수

ETF 데이터 조회 및 포트폴리오 분석을 위한 AWS Lambda 함수입니다.
yfinance 라이브러리를 사용하여 실시간 ETF 가격 데이터를 제공합니다.

주요 기능:
- get_available_products: 투자 가능한 ETF 목록 조회
- get_product_data: 특정 ETF의 가격 데이터 조회 (최근 3개월)
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


def get_available_products():
    """
    투자 가능한 ETF 상품 목록 반환
    
    미국 주요 ETF 30개를 카테고리별로 분류하여 제공합니다.
    포트폴리오 구성 시 다양한 자산군에서 선택할 수 있도록 구성되었습니다.
    
    Returns:
        dict: ETF 티커와 설명이 포함된 딕셔너리
        
    Categories:
        - 주요 지수 ETF (5개): 미국 대표 지수 추종
        - 국제/신흥국 ETF (5개): 해외 분산투자
        - 채권/안전자산 ETF (5개): 안정성과 인플레이션 헤지
        - 섹터별 ETF (8개): 특정 산업 집중투자
        - 혁신/성장 ETF (5개): 고성장 테마 투자
        - 배당 ETF (2개): 안정적인 배당 수익
    """
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
    
    print(f"📋 ETF 상품 목록 조회: {len(products)}개 상품 반환")
    return products


def get_product_data(ticker):
    """
    특정 ETF의 가격 데이터 조회
    
    yfinance 라이브러리를 사용하여 지정된 ETF의 최근 3개월 가격 데이터를 조회합니다.
    포트폴리오 분석 및 트렌드 분석에 사용됩니다.
    
    Args:
        ticker (str): ETF 티커 심볼 (예: 'QQQ', 'SPY', 'ARKK')
        
    Returns:
        dict: 날짜별 종가 데이터 또는 오류 정보
        
    Example:
        {
            "QQQ": {
                "2024-05-01": 450.25,
                "2024-05-02": 452.10,
                ...
            }
        }
        
    Note:
        - 최근 100일 데이터 조회 (약 3개월)
        - 주말 및 공휴일 제외한 거래일만 포함
        - 가격은 소수점 둘째 자리까지 반올림
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
        - get_available_products: ETF 상품 목록 조회
        - get_product_data: 특정 ETF 가격 데이터 조회
        
    Note:
        - 도구 이름은 context.client_context.custom['bedrockAgentCoreToolName']에서 추출
        - 응답은 JSON 형태로 반환 (한글 지원)
    """
    try:
        # 디버깅을 위한 로그 출력
        print("📥 Lambda 호출 정보:")
        print(f"   Context: {context.client_context}")
        print(f"   Event: {event}")
        
        # AgentCore에서 전달된 도구 이름 추출
        tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        
        # 도구 이름에서 실제 함수명 추출 (target-portfolio-architect___get_available_products -> get_available_products)
        function_name = tool_name.split('___')[-1] if '___' in tool_name else tool_name
        
        print(f"🔧 실행할 함수: {function_name}")
        
        # 함수명에 따른 비즈니스 로직 실행
        if function_name == 'get_available_products':
            # ETF 상품 목록 조회
            output = get_available_products()
            
        elif function_name == 'get_product_data':
            # 특정 ETF 가격 데이터 조회
            ticker = event.get('ticker', "")
            if not ticker:
                output = {"error": "ticker parameter is required"}
                print("❌ ticker 파라미터가 누락되었습니다")
            else:
                output = get_product_data(ticker)
                
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
        error_msg = f"Lambda execution error: {str(e)}"
        print(f"❌ {error_msg}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({"error": error_msg}, ensure_ascii=False)
        }
