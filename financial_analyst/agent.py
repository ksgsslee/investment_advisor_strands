"""
agent.py
재무 분석가 + Reflection 패턴 구현
"""
import json
from typing import Dict, Any
from strands import Agent
from strands.models.bedrock import BedrockModel
import sys
import os

# 상위 디렉토리의 config 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODELS, ANTHROPIC_API_KEY


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
    
    def analyze(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        재무 분석 수행 (Reflection 패턴 적용)
        """
        try:
            # 1단계: 재무 분석 수행
            user_input_str = json.dumps(user_input, ensure_ascii=False)
            analysis_prompt = f"사용자 정보를 분석해주세요:\n{user_input_str}"
            
            # Swarm을 통해 분석가가 먼저 분석 수행
            analysis_result = self.analyst_agent(analysis_prompt)
            
            # JSON 파싱 시도
            try:
                analysis_data = json.loads(str(analysis_result))
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트에서 JSON 추출 시도
                result_text = str(analysis_result)
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = result_text[start_idx:end_idx]
                    analysis_data = json.loads(json_str)
                else:
                    raise ValueError("JSON 형식을 찾을 수 없습니다.")
            
            # 2단계: Reflection 검증 수행
            reflection_prompt = f"다음 재무 분석 결과를 검증해주세요:\n{json.dumps(analysis_data, ensure_ascii=False)}"
            reflection_result = self.reflection_agent(reflection_prompt)
            
            reflection_text = str(reflection_result).strip().lower()
            is_valid = reflection_text.startswith('yes')
            
            return {
                "analysis": analysis_data,
                "reflection_result": str(reflection_result),
                "is_valid": is_valid,
                "status": "success" if is_valid else "validation_failed"
            }
            
        except Exception as e:
            return {
                "analysis": None,
                "reflection_result": f"Error: {str(e)}",
                "is_valid": False,
                "status": "error",
                "error": str(e)
            }


# 테스트용 함수
def test_financial_analyst():
    """테스트 함수"""
    analyst = FinancialAnalyst()
    
    test_input = {
        "total_investable_amount": 50000000,
        "age": 35,
        "stock_investment_experience_years": 10,
        "target_amount": 70000000
    }
    
    result = analyst.analyze(test_input)
    print("=== Lab 1: Financial Analyst Result ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    test_financial_analyst()