"""
Lab 2: Portfolio Architect with Tool Use Pattern
포트폴리오 설계사 + Tool Use 패턴 구현
"""
import json
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Any, List
from strands import Agent
from strands.models.anthropic import AnthropicModel
from strands.tools import tool
from config import MODELS, AVAILABLE_PRODUCTS, ANTHROPIC_API_KEY


@tool
def get_available_products() -> str:
    """사용 가능한 투자 상품 목록을 조회합니다."""
    return json.dumps(AVAILABLE_PRODUCTS, ensure_ascii=False)


@tool
def get_product_data(ticker: str) -> str:
    """선택한 투자 상품의 최근 가격 데이터를 조회합니다."""
    try:
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=100)
        
        etf = yf.Ticker(ticker)
        hist = etf.history(start=start_date, end=end_date)
        
        if hist.empty:
            return json.dumps({"error": f"No data found for ticker {ticker}"})
        
        # 최근 가격 데이터 구성
        product_data = {
            ticker: {
                date.strftime('%Y-%m-%d'): round(price, 2) 
                for date, price in hist['Close'].items()
            }
        }
        
        return json.dumps(product_data, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


class PortfolioArchitect:
    def __init__(self):
        self.model = AnthropicModel(
            model_id=MODELS["portfolio_architect"]["model"],
            api_key=ANTHROPIC_API_KEY,
            temperature=MODELS["portfolio_architect"]["temperature"],
            max_tokens=MODELS["portfolio_architect"]["max_tokens"]
        )
        
        self.agent = Agent(
            name="portfolio_architect",
            model=self.model,
            system_prompt=self._get_system_prompt(),
            tools=[get_available_products, get_product_data]
        )
    
    def _get_system_prompt(self) -> str:
        return """당신은 전문 투자 설계사입니다. 고객의 재무 분석 결과를 바탕으로 구체적인 투자 포트폴리오를 제안해야 합니다.

당신의 작업:
1. 재무 분석 결과를 신중히 검토하고 해석하세요.
2. "get_available_products" 도구를 호출하여 사용 가능한 투자 상품 목록을 얻으세요.
3. 얻은 투자 상품 목록 중 분산 투자를 고려하여 고객의 재무 분석 결과와 가장 적합한 3개의 상품을 선택하세요.
4. 선택한 각 투자 상품에 대해 "get_product_data" 도구를 호출하여 최근 가격 데이터를 얻으세요.
5. 얻은 가격 데이터를 분석하여 최종 포트폴리오 비율을 결정하세요.
6. 포트폴리오 구성 근거를 상세히 설명하세요.

다음 JSON 형식으로 응답해주세요:
{
  "portfolio_allocation": {"ticker1": 비율1, "ticker2": 비율2, "ticker3": 비율3},
  "strategy": "투자 전략 설명",
  "reason": "포트폴리오 구성 근거"
}

응답 시 다음 사항을 고려하세요:
- 제안한 포트폴리오가 고객의 투자 목표 달성에 어떻게 도움이 될 것인지 논리적으로 설명하세요.
- 각 자산의 배분 비율은 반드시 정수로 표현하고, 총합이 100%가 되어야 합니다.
- 포트폴리오 구성 근거를 작성할때는 반드시 "QQQ(미국 기술주)" 처럼 티커와 설명을 함께 제공하세요."""
    
    def design_portfolio(self, financial_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        포트폴리오 설계 수행 (Tool Use 패턴 적용)
        """
        try:
            # 재무 분석 결과를 프롬프트로 구성
            analysis_str = json.dumps(financial_analysis, ensure_ascii=False, indent=2)
            prompt = f"""다음 재무 분석 결과를 바탕으로 포트폴리오를 설계해주세요:

{analysis_str}

위 분석 결과를 고려하여 최적의 포트폴리오를 제안해주세요."""
            
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
                    portfolio_data = json.loads(json_str)
                    
                    return {
                        "portfolio": portfolio_data,
                        "raw_response": result_text,
                        "status": "success"
                    }
                else:
                    return {
                        "portfolio": None,
                        "raw_response": result_text,
                        "status": "json_parse_error",
                        "error": "JSON 형식을 찾을 수 없습니다."
                    }
                    
            except json.JSONDecodeError as e:
                return {
                    "portfolio": None,
                    "raw_response": str(result),
                    "status": "json_parse_error",
                    "error": f"JSON 파싱 오류: {str(e)}"
                }
                
        except Exception as e:
            return {
                "portfolio": None,
                "raw_response": None,
                "status": "error",
                "error": str(e)
            }


# 테스트용 함수
def test_portfolio_architect():
    """테스트 함수"""
    architect = PortfolioArchitect()
    
    # Lab 1의 예시 결과를 사용
    test_financial_analysis = {
        "risk_profile": "공격적",
        "risk_profile_reason": "나이가 35세로 젊고, 주식 투자 경험이 10년으로 상당히 많으며, 총 투자 가능 금액이 5000만원으로 상당히 높은 편입니다.",
        "required_annual_return_rate": 40.00,
        "return_rate_reason": "필요 연간 수익률은 (70000000 - 50000000) / 50000000 * 100 = 40.00%입니다."
    }
    
    result = architect.design_portfolio(test_financial_analysis)
    print("=== Lab 2: Portfolio Architect Result ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    test_portfolio_architect()