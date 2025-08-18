"""
portfolio_architect.py
포트폴리오 설계사 + Tool Use 패턴 구현 (AgentCore Runtime 버전)
"""
import json
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Any, List
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools import tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import sys
import os

# 상위 디렉토리의 config 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AVAILABLE_PRODUCTS

app = BedrockAgentCoreApp()


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
        # 포트폴리오 설계사 에이전트
        self.architect_agent = Agent(
            name="portfolio_architect",
            model=BedrockModel(
                model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                temperature=0.3,
                max_tokens=3000
            ),
            callback_handler=None,
            system_prompt=self._get_system_prompt(),
            tools=[get_available_products, get_product_data]
        )
    
    def _get_system_prompt(self) -> str:
        return """당신은 전문 투자 설계사입니다. 고객의 재무 분석 결과를 바탕으로 구체적인 투자 포트폴리오를 제안해야 합니다. 

재무 분석 결과가 다음과 같은 JSON 형식으로 제공됩니다:
{
  "risk_profile": <위험 성향>,
  "risk_profile_reason": <위험 성향 평가 근거>,
  "required_annual_return_rate": <필요 연간 수익률>,
  "return_rate_reason": <필요 수익률 계산 근거 및 설명>
}

당신의 작업:
1. 재무 분석 결과를 신중히 검토하고 해석하세요.
2. "get_available_products" 액션을 호출하여 사용 가능한 투자 상품 목록을 얻으세요. 각 상품은 "ticker: 설명" 형식으로 제공됩니다.
3. 얻은 투자 상품 목록 중 분산 투자를 고려하여 고객의 재무 분석 결과와 가장 적합한 3개의 상품을 선택하세요.
4. 선택한 각 투자 상품에 대해 "get_product_data" 액션을 동시에 호출하여 최근 가격 데이터를 얻으세요.
5. 얻은 가격 데이터를 분석하여 최종 포트폴리오 비율을 결정하세요. 이때 고객의 재무 분석 결과를 균형있게 고려하세요.
6. 포트폴리오 구성 근거를 상세히 설명하세요.

다음 JSON 형식으로 응답해주세요:
{
  "portfolio_allocation": {투자 상품별 배분 비율} (예: {"ticker1": 50, "ticker2": 30, "ticker3": 20}),
  "strategy": "투자 전략 설명",
  "reason": "포트폴리오 구성 근거"
}

응답 시 다음 사항을 고려하세요:
- 제안한 포트폴리오가 고객의 투자 목표 달성에 어떻게 도움이 될 것인지 논리적으로 설명하세요.
- 각 자산의 배분 비율은 반드시 정수로 표현하고, 총합이 100%가 되어야 합니다.
- 포트폴리오 구성 근거를 작성할때는 반드시 "QQQ(미국 기술주)" 처럼 티커와 설명을 함께 제공하세요.
- JSON 앞뒤에 백틱(```) 또는 따옴표를 붙이지 말고 순수한 JSON 형식만 출력하세요."""
    
    async def design_portfolio_async(self, financial_analysis):
        """실시간 스트리밍 포트폴리오 설계 수행"""
        try:
            # 재무 분석 결과를 프롬프트로 구성
            analysis_str = json.dumps(financial_analysis, ensure_ascii=False, indent=2)
            
            # 🎯 실시간 스트리밍으로 에이전트 실행
            async for event in self.architect_agent.stream_async(analysis_str):
                # 텍스트 데이터 스트리밍
                if "data" in event:
                    yield {
                        "type": "text_chunk",
                        "data": event["data"],
                        "complete": event.get("complete", False)
                    }
                
                # 🎯 메시지가 추가될 때 완료된 tool_use 정보를 yield
                if "message" in event:
                    message = event["message"]
                    
                    # assistant 메시지에서 완료된 tool_use 찾기
                    if message.get("role") == "assistant":
                        for content in message.get("content", []):
                            if "toolUse" in content:
                                tool_use = content["toolUse"]
                                # 🎯 완료된 tool_use를 바로 yield
                                yield {
                                    "type": "tool_use",
                                    "tool_name": tool_use.get("name"),
                                    "tool_use_id": tool_use.get("toolUseId"),
                                    "tool_input": tool_use.get("input", {})
                                }
                    
                    # user 메시지에서 tool_result 처리
                    if message.get("role") == "user":
                        for content in message.get("content", []):
                            if "toolResult" in content:
                                tool_result = content["toolResult"]
                                yield {
                                    "type": "tool_result",
                                    "tool_use_id": tool_result["toolUseId"],
                                    "status": tool_result["status"],
                                    "content": tool_result["content"]
                                }
                
                # 최종 결과 - 스트리밍 완료 신호
                if "result" in event:
                    yield {
                        "type": "streaming_complete",
                        "message": "텍스트 스트리밍 완료!"
                    }

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "status": "error"
            }


# AgentCore Runtime 엔트리포인트
architect = PortfolioArchitect()

@app.entrypoint
async def portfolio_architect(payload):
    """AgentCore Runtime 엔트리포인트"""
    financial_analysis = payload.get("financial_analysis")
    async for chunk in architect.design_portfolio_async(financial_analysis):
        yield chunk

# 테스트용 함수
def test_portfolio_architect():
    """테스트 함수"""
    import asyncio
    
    async def run_test():
        architect = PortfolioArchitect()
        
        # Lab 1의 예시 결과를 사용
        test_financial_analysis = {
            "risk_profile": "공격적",
            "risk_profile_reason": "나이가 35세로 젊고, 주식 투자 경험이 10년으로 상당히 많으며, 총 투자 가능 금액이 5000만원으로 상당히 높은 편입니다.",
            "required_annual_return_rate": 40.00,
            "return_rate_reason": "필요 연간 수익률은 (70000000 - 50000000) / 50000000 * 100 = 40.00%입니다."
        }
        
        print("=== Lab 2: Portfolio Architect Test ===")
        print("📥 입력 데이터:")
        print(json.dumps(test_financial_analysis, ensure_ascii=False, indent=2))
        print("\n🤖 포트폴리오 설계 시작...")
        
        try:
            full_text = ""
            async for chunk in architect.design_portfolio_async(test_financial_analysis):
                if chunk["type"] == "text_chunk":
                    # 실시간 텍스트 출력
                    data = chunk["data"]
                    full_text += data
                    print(data, end="", flush=True)
                    
                elif chunk["type"] == "streaming_complete":
                    # 🎯 스트리밍 완료 시점 표시
                    print(f"\n\n✅ {chunk['message']}")
                    
                elif chunk["type"] == "tool_use":
                    # 🎯 tool input이 완료된 후에만 출력
                    print(f"\n\n🛠️ Tool Use: {chunk['tool_name']}")
                    print(f"   Tool Use ID: {chunk['tool_use_id']}")
                    print(f"   Input: {chunk['tool_input']}")
                    print("-" * 40)
                    
                elif chunk["type"] == "tool_result":
                    # 🎯 tool 결과 출력
                    print(f"\n📊 Tool Result:")
                    print(f"   Tool Use ID: {chunk['tool_use_id']}")
                    print(f"   Status: {chunk['status']}")
                    for content_item in chunk['content']:
                        if 'text' in content_item:
                            result_text = content_item['text']
                            print(f"   Result: {result_text}")
                    print("-" * 40)
                    
                
                elif chunk["type"] == "error":
                    print(f"\n❌ 오류 발생: {chunk['error']}")
                    
        except Exception as e:
            print(f"\n❌테스트 실행 중 오류: {str(e)}")
    
    # 비동기 함수 실행
    asyncio.run(run_test())

if __name__ == "__main__":
    # 기본 테스트
    test_portfolio_architect()
    # AgentCore 앱 실행
    app.run()