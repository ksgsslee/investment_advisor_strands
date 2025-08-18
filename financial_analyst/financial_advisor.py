"""
financial_advisor.py
재무 분석가 + Reflection 패턴 구현 (AgentCore Runtime 버전)
"""
import json
from typing import Dict, Any
from strands import Agent
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class FinancialAnalyst:
    def __init__(self):
        # 재무 분석가 에이전트
        self.analyst_agent = Agent(
            name="financial_analyst",
            model=BedrockModel(
                model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                temperature=0.1,
                max_tokens=2000
            ),
            system_prompt=self._get_analyst_prompt()
        )
        
        # Reflection 에이전트
        self.reflection_agent = Agent(
            name="reflection_validator",
            model=BedrockModel(
                model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                temperature=0.1,
                max_tokens=2000
            ),
            system_prompt=self._get_reflection_prompt()
        )
        
    def _get_analyst_prompt(self) -> str:
        return """당신은 재무분석 전문가입니다. 주어진 사용자 정보를 바탕으로 위험 성향을 평가하고 필요 연간 수익률을 계산하여 재무 분석 결과를 출력해야 합니다.

사용자 정보는 다음과 같은 JSON 형식으로 제공됩니다:
{
"total_investable_amount": <총 투자 가능 금액>,
"age": <나이>,
"stock_investment_experience_years": <주식 투자 경험 연수>,
"target_amount": <1년 후 목표 금액>
}

분석 시 다음 사항을 고려하세요:
1. 위험 성향 평가:
- 나이, 투자 경험, 재무 상태, 목표 금액 들을 종합적으로 고려하여 위험 성향 평가
2. 필요 연간 수익률 계산:
- 계산 과정을 단계별로 명확히 보여주고, 각 단계를 설명하세요
- 계산된 수익률의 의미를 간단히 해석하세요

이 정보를 바탕으로 다음 형식에 맞춰 분석 결과를 JSON으로 출력하세요:
{
"risk_profile": "위험 성향 평가 (매우 보수적, 보수적, 중립적, 공격적, 매우 공격적 중 하나)",
"risk_profile_reason": "위험 성향 평가에 대한 상세한 설명",
"required_annual_return_rate": 필요 연간 수익률 (소수점 둘째 자리까지의 백분율),
"return_rate_reason": "필요 연간 수익률 계산 과정과 그 의미에 대한 상세한 설명"
}

출력시 다음 사항을 주의하세요
- 추가적인 설명이나 텍스트는 포함하지 마세요.
- JSON 앞뒤에 백틱(```) 또는 따옴표를 붙이지 말고 순수한 JSON 형식만 출력하세요."""
    
    def _get_reflection_prompt(self) -> str:
        return """당신은 재무 분석 결과를 검토하는 전문가입니다. 주어진 재무 분석 결과를 바탕으로 분석의 적절성을 평가해야 합니다.

재무 분석 결과는 다음과 같은 JSON 형식으로 제공됩니다:
{
"risk_profile": <위험 성향 평가>,
"risk_profile_reason": <위험 성향 평가에 대한 상세한 설명>,
"required_annual_return_rate": <필요 연간 수익률>,
"return_rate_reason": <필요 연간 수익률 계산 과정과 그 의미에 대한 상세한 설명>
}

다음 기준을 바탕으로 재무 분석 결과를 검토하여 적절성을 평가하세요:
1. 필요 연간 수익률 계산 과정을 다시 반복하여 리뷰
2. 계산된 수익률이 0%~50% 범위 내 여부 확인

출력 형식:
- 모든 기준이 충족되면 반드시 "yes"만 출력하고 추가 설명을 하지 마세요.
- 하나라도 미충족 시 "no"를 출력하고, 그 다음 줄에 미충족 이유를 간단히 설명하세요."""
    
    async def analyze_async(self, user_input):
        """비동기 재무 분석 수행"""
        try:
            user_input_str = json.dumps(user_input, ensure_ascii=False)

            # 분석 수행 및 스트리밍
            analyst_response = self.analyst_agent(user_input_str)
            analysis_data = analyst_response.message['content'][0]['text']

            yield {
                "type": "data", 
                "analysis_data": analysis_data
            }

            # Reflection 검증
            reflection_response = self.reflection_agent(analysis_data)
            reflection_result = reflection_response.message['content'][0]['text']
            yield {
                "type": "data", 
                "reflection_result": reflection_result
            }

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "status": "error"
            }

# AgentCore Runtime 엔트리포인트
analyst = FinancialAnalyst()

@app.entrypoint
async def financial_advisor(payload):
    """AgentCore Runtime 엔트리포인트"""
    user_input = payload.get("input_data")
    async for chunk in analyst.analyze_async(user_input):
        yield chunk

if __name__ == "__main__":
    app.run()