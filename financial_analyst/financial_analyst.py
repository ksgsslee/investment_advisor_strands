"""
financial_analyst.py
Financial Analyst - Tool Use Pattern

Calculator 도구를 활용하여 개인 재무 분석 및 투자 성향 평가를 수행합니다.
실시간 스트리밍으로 분석 과정을 시각화하고 0~50% 범위 내 합리성을 검증합니다.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import calculator
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# ================================
# 전역 설정
# ================================

app = BedrockAgentCoreApp()

class Config:
    """Financial Analyst 설정"""
    ANALYST_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    ANALYST_TEMPERATURE = 0.1
    ANALYST_MAX_TOKENS = 3000

# ================================
# 유틸리티 함수들
# ================================

def extract_json_from_text(text_content):
    """AI 응답에서 JSON 부분만 추출"""
    if not isinstance(text_content, str):
        return text_content
    
    start_idx = text_content.find('{')
    end_idx = text_content.rfind('}') + 1
    
    if start_idx != -1 and end_idx > start_idx:
        return text_content[start_idx:end_idx]
    
    return text_content

# ================================
# 메인 클래스
# ================================

class FinancialAnalyst:
    """
    Calculator 도구를 활용한 AI 재무 분석사
    - 수익률 계산, 위험 성향 평가, 합리성 검증 수행
    - 실시간 스트리밍으로 분석 과정 시각화
    """
    
    def __init__(self):
        """Calculator 도구가 포함된 AI 에이전트 초기화"""
        self.analyst_agent = Agent(
            name="financial_analyst",
            model=BedrockModel(
                model_id=Config.ANALYST_MODEL_ID,
                temperature=Config.ANALYST_TEMPERATURE,
                max_tokens=Config.ANALYST_MAX_TOKENS
            ),
            tools=[calculator],
            system_prompt=self._get_analyst_prompt()
        )
        
    def _get_analyst_prompt(self) -> str:
        """Calculator 도구 사용 지침이 포함된 시스템 프롬프트"""
        return """재무분석 전문가로서 개인 맞춤형 투자 분석을 수행합니다.

입력 데이터:
- total_investable_amount: 투자 가능 금액
- target_amount: 1년 후 목표 금액
- age: 나이  
- stock_investment_experience_years: 투자 경험 연수
- investment_purpose: 투자 목적
- preferred_sectors: 관심 투자 분야

분석 과정:
1. calculator로 필요 수익률 계산: ((목표금액/투자금액)-1)*100
2. 나이, 경험, 목적, 관심분야를 종합한 위험성향 평가
3. 수익률 합리성 검증 (0~50% 범위)

출력:
{
"risk_profile": "매우 보수적|보수적|중립적|공격적|매우 공격적",
"risk_profile_reason": "위험성향 평가 근거 (2-3문장)",
"required_annual_return_rate": 수익률(소수점2자리),
"is_reasonable": "yes|no",
"summary": "투자목적과 관심분야를 고려한 종합 총평 (3-4문장)"
}"""

    async def analyze_financial_situation_async(self, user_input):
        """
        Calculator 도구를 활용한 실시간 스트리밍 재무 분석
        
        Args:
            user_input (dict): 고객 재무 정보
            
        Yields:
            dict: 스트리밍 이벤트 (text_chunk, tool_use, tool_result, streaming_complete, error)
        """
        try:
            # 고객 정보를 JSON 문자열로 변환
            user_input_str = json.dumps(user_input, ensure_ascii=False)

            # Calculator 도구를 활용한 재무 분석 수행
            async for event in self.analyst_agent.stream_async(user_input_str):
                
                # AI 생각 과정 스트리밍
                if "data" in event:
                    yield {"type": "text_chunk", "data": event["data"]}
                
                # 도구 사용 과정 추적
                if "message" in event:
                    message = event["message"]
                    
                    # 도구 사용 시작
                    if message.get("role") == "assistant":
                        for content in message.get("content", []):
                            if "toolUse" in content:
                                tool_use = content["toolUse"]
                                yield {
                                    "type": "tool_use",
                                    "tool_name": tool_use.get("name"),
                                    "tool_use_id": tool_use.get("toolUseId"),
                                    "tool_input": tool_use.get("input", {})
                                }
                    
                    # 도구 실행 결과
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
                
                # 최종 결과 처리
                if "result" in event:
                    raw_result = str(event["result"])
                    clean_json = extract_json_from_text(raw_result)
                    yield {"type": "streaming_complete", "analysis_data": clean_json}

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "status": "error"
            }

# ================================
# AgentCore Runtime 엔트리포인트
# ================================

# 전역 인스턴스 (지연 초기화)
analyst = None

@app.entrypoint
async def financial_analyst(payload):
    """
    AgentCore Runtime 엔트리포인트
    Calculator 도구를 활용한 재무 분석을 실시간 스트리밍으로 수행
    """
    global analyst
    
    # Runtime 환경에서 지연 초기화
    if analyst is None:
        analyst = FinancialAnalyst()

    # 고객 정보 추출 및 재무 분석 실행
    user_input = payload.get("input_data")
    async for chunk in analyst.analyze_financial_situation_async(user_input):
        yield chunk

# ================================
# 직접 실행 시 Runtime 서버 시작
# ================================

if __name__ == "__main__":
    app.run()