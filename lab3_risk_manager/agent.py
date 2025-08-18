"""
Lab 3: Risk Manager with Planning Pattern
리스크 관리사 + Planning 패턴 구현
"""
import json
import yfinance as yf
from typing import Dict, Any, List
from strands import Agent
from strands.models.anthropic import AnthropicModel
from strands.tools import tool
from strands_tools import workflow
import sys
import os

# 상위 디렉토리의 config 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODELS, ANTHROPIC_API_KEY


@tool
def get_product_news(ticker: str, top_n: int = 5) -> str:
    """선택한 투자 상품의 최근 뉴스 정보를 조회합니다."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news[:top_n]
        
        formatted_news = []
        for item in news:
            # yfinance 뉴스 구조에 맞게 조정
            if hasattr(item, 'get'):
                title = item.get('title', '')
                summary = item.get('summary', '')
                publish_date = item.get('providerPublishTime', '')
            else:
                # 다른 구조일 경우 대비
                title = getattr(item, 'title', '')
                summary = getattr(item, 'summary', '')
                publish_date = getattr(item, 'providerPublishTime', '')
            
            if isinstance(publish_date, (int, float)):
                from datetime import datetime
                publish_date = datetime.fromtimestamp(publish_date).strftime('%Y-%m-%d')
            
            news_item = {
                "title": title,
                "summary": summary,
                "publish_date": str(publish_date)[:10] if publish_date else ""
            }
            formatted_news.append(news_item)
        
        result = {
            "ticker": ticker,
            "news": formatted_news,
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"Error fetching news for {ticker}: {str(e)}"})


@tool
def get_market_data() -> str:
    """주요 시장 지표 데이터를 조회합니다."""
    try:
        market_info = {
            "us_dollar_index": {"ticker": "DX-Y.NYB", "description": "미국 달러 강세를 나타내는 지수"},
            "us_10y_treasury_yield": {"ticker": "^TNX", "description": "미국 10년 국채 수익률 (%)"},
            "vix_volatility_index": {"ticker": "^VIX", "description": "시장의 변동성을 나타내는 VIX 지수"},
            "crude_oil_price": {"ticker": "CL=F", "description": "WTI 원유 선물 가격 (USD/배럴)"}
        }
        
        data = {}
        for key, info in market_info.items():
            try:
                ticker = yf.Ticker(info["ticker"])
                # 최근 데이터 가져오기
                hist = ticker.history(period="5d")
                if not hist.empty:
                    market_price = round(hist['Close'].iloc[-1], 2)
                else:
                    market_price = 0
                
                data[key] = {
                    "description": info["description"],
                    "value": market_price
                }
            except:
                data[key] = {
                    "description": info["description"],
                    "value": 0
                }
        
        return json.dumps(data, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"Error fetching market data: {str(e)}"})


class RiskManager:
    def __init__(self):
        self.model = AnthropicModel(
            model_id=MODELS["risk_manager"]["model"],
            api_key=ANTHROPIC_API_KEY,
            temperature=MODELS["risk_manager"]["temperature"],
            max_tokens=MODELS["risk_manager"]["max_tokens"]
        )
        
        self.agent = Agent(
            name="risk_manager",
            model=self.model,
            system_prompt=self._get_system_prompt(),
            tools=[get_product_news, get_market_data, workflow]
        )
    
    def _get_system_prompt(self) -> str:
        return """당신은 리스크 관리 전문가입니다. 제안된 포트폴리오에 대해 리스크 분석을 수행하고, 주요 경제 시나리오에 따른 포트폴리오 조정 가이드를 제공해야 합니다.

당신의 작업:
주어진 도구(tools)들을 자유롭게 사용하여 아래 목표를 달성하세요
1. 주어진 포트폴리오에 대한 종합적인 리스크 분석
2. 발생 가능성이 높은 2개의 경제 시나리오를 도출
3. 각 시나리오에 대한 포트폴리오 조정 방안을 제시

반드시 다음 형식으로 응답해주세요:
{
"scenario1": {
"name": "시나리오 1 이름",
"description": "시나리오 1 상세 설명",
"allocation_management": {
"ticker1": 새로운_비율1,
"ticker2": 새로운_비율2,
"ticker3": 새로운_비율3
},
"reason": "조정 이유 및 전략"
},
"scenario2": {
"name": "시나리오 2 이름",
"description": "시나리오 2 상세 설명",
"allocation_management": {
"ticker1": 새로운_비율1,
"ticker2": 새로운_비율2,
"ticker3": 새로운_비율3
},
"reason": "조정 이유 및 전략"
}
}

응답 시 다음 사항을 반드시 준수하세요:
1. 포트폴리오 조정 시 입력으로 받은 상품(ticker)만을 사용하세요.
2. 새로운 상품을 추가하거나 기존 상품을 제거하지 마세요.
3. 포트폴리오 구성 근거를 상세히 설명하세요."""
    
    def analyze_risk(self, portfolio_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        리스크 분석 수행 (Planning 패턴 적용)
        """
        try:
            # 포트폴리오 결과를 프롬프트로 구성
            portfolio_str = json.dumps(portfolio_result, ensure_ascii=False, indent=2)
            prompt = f"""다음 포트폴리오 제안 결과를 바탕으로 리스크 분석을 수행해주세요:

{portfolio_str}

위 포트폴리오에 대해 뉴스 분석과 시장 데이터를 활용하여 리스크 분석 및 시나리오 플래닝을 수행해주세요."""
            
            # 에이전트 실행 (도구 사용 포함)
            result = self.agent(prompt)
            
            # JSON 파싱 시도
            try:
                result_text = str(result)
                # JSON 부분 추출
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = result_text[start_idx:end_idx]
                    risk_data = json.loads(json_str)
                    
                    return {
                        "risk_analysis": risk_data,
                        "raw_response": result_text,
                        "status": "success"
                    }
                else:
                    return {
                        "risk_analysis": None,
                        "raw_response": result_text,
                        "status": "json_parse_error",
                        "error": "JSON 형식을 찾을 수 없습니다."
                    }
                    
            except json.JSONDecodeError as e:
                return {
                    "risk_analysis": None,
                    "raw_response": str(result),
                    "status": "json_parse_error",
                    "error": f"JSON 파싱 오류: {str(e)}"
                }
                
        except Exception as e:
            return {
                "risk_analysis": None,
                "raw_response": None,
                "status": "error",
                "error": str(e)
            }


# 테스트용 함수
def test_risk_manager():
    """테스트 함수"""
    risk_manager = RiskManager()
    
    # Lab 2의 예시 결과를 사용
    test_portfolio_result = {
        "portfolio": {
            "portfolio_allocation": {
                "QQQ": 40,
                "MCHI": 30,
                "ICLN": 30
            },
            "strategy": "공격적인 투자 전략을 채택하여 높은 수익률을 목표로 합니다.",
            "reason": "QQQ (미국 기술주)는 기술 분야의 선도 기업들로 구성되어 있어 높은 성장 잠재력을 가지고 있습니다."
        }
    }
    
    result = risk_manager.analyze_risk(test_portfolio_result)
    print("=== Lab 3: Risk Manager Result ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    test_risk_manager()