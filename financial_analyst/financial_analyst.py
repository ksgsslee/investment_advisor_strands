"""
financial_analyst.py
Financial Analyst - AI 재무 분석사

개인의 재무 상황을 분석하여 투자 성향과 목표 수익률을 계산하는 AI 에이전트입니다.
Strands Agent의 calculator 도구를 활용하여 정확한 수치 계산을 수행합니다.

주요 기능:
- 개인 재무 상황 종합 분석
- 위험 성향 평가 및 근거 제시
- Calculator 도구를 활용한 정확한 목표 수익률 계산
- 달성 가능성 분석
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
    """Financial Analyst 설정 상수"""
    # 재무 분석사 모델 설정
    ANALYST_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    ANALYST_TEMPERATURE = 0.1
    ANALYST_MAX_TOKENS = 3000

# ================================
# 유틸리티 함수들
# ================================

def extract_json_from_text(text_content):
    """
    텍스트에서 JSON 데이터를 추출하는 함수
    
    Args:
        text_content (str): JSON이 포함된 텍스트
        
    Returns:
        dict: 파싱된 JSON 데이터
    """
    # JSON 블록 찾기
    start_idx = text_content.find('{')
    end_idx = text_content.rfind('}') + 1
    return text_content[start_idx:end_idx]


# ================================
# 메인 클래스
# ================================

class FinancialAnalyst:
    """
    AI 재무 분석사 - Calculator 도구 활용
    
    개인의 재무 상황을 종합적으로 분석하여 투자 성향과 목표 수익률을 계산합니다.
    Strands Agent의 calculator 도구를 활용하여 정확한 수치 계산을 수행합니다.
    """
    
    def __init__(self):
        """
        재무 분석사 초기화
        
        Calculator 도구가 포함된 AI 에이전트를 생성하고 재무 분석을 위한 시스템 프롬프트를 설정합니다.
        """
        self._create_analyst_agent()
    
    def _create_analyst_agent(self):
        """재무 분석사 AI 에이전트 생성 (Calculator 도구 포함)"""
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
        """
        재무 분석사 AI 에이전트용 시스템 프롬프트 생성
        
        Returns:
            str: 재무 분석사 역할과 작업 지침이 포함된 프롬프트
        """
        return """당신은 재무분석 전문가입니다. 사용자 정보를 분석하여 위험 성향과 필요 수익률을 계산하세요.

입력 데이터:
{
"total_investable_amount": 총 투자 가능 금액,
"age": 나이,
"stock_investment_experience_years": 주식 투자 경험 연수,
"target_amount": 1년 후 목표 금액
}

작업:
1. calculator 도구로 필요 연간 수익률 계산: ((목표금액 / 투자금액) - 1) * 100
2. 나이, 경험, 목표 등을 종합적으로 고려하여 위험 성향 평가
3. 계산된 수익률이 0~50% 범위 내인지 확인하여 합리성 판단

출력 형식 (순수 JSON만):
{
"risk_profile": "매우 보수적|보수적|중립적|공격적|매우 공격적",
"risk_profile_reason": "위험 성향 평가 근거",
"required_annual_return_rate": 수익률(백분율, 소수점 2자리),
"return_rate_reason": "수익률 계산 과정 설명",
"is_reasonable": "yes|no (수익률이 0~50% 범위 내이고 현실적으로 달성 가능하면 yes, 아니면 no)"
}"""


    
    async def analyze_financial_situation_async(self, user_input):
        """
        실시간 스트리밍 재무 분석 수행 (Calculator 도구 활용)
        
        고객의 재무 정보를 바탕으로 AI가 실시간으로 분석을 수행합니다.
        Calculator 도구를 사용하여 정확한 수익률 계산을 수행하고,
        분석 과정과 결과를 스트리밍 이벤트로 실시간 전송합니다.
        
        Args:
            user_input (dict): 고객 재무 정보
                - total_investable_amount: 총 투자 가능 금액
                - age: 나이
                - stock_investment_experience_years: 주식 투자 경험 년수
                - target_amount: 1년 후 목표 금액
            
        Yields:
            dict: 스트리밍 이벤트
                - text_chunk: AI의 실시간 분석 과정
                - tool_use: 도구 사용 시작 알림
                - tool_result: 도구 실행 결과
                - analysis_data: 재무 분석 결과 JSON
                - streaming_complete: 분석 완료 신호
                - error: 오류 발생 시
        """
        try:
            # 고객 정보를 JSON 문자열로 변환
            user_input_str = json.dumps(user_input, ensure_ascii=False)

            # 재무 분석 수행 (Calculator 도구 사용)
            async for event in self.analyst_agent.stream_async(user_input_str):
                
                # AI 생각 과정 텍스트 스트리밍
                if "data" in event:
                    yield {
                        "type": "text_chunk",
                        "data": event["data"]
                    }
                
                # 메시지 이벤트 처리 (도구 사용 및 결과)
                if "message" in event:
                    message = event["message"]
                    
                    # Assistant 메시지: 도구 사용 정보 추출
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
                    
                    # User 메시지: 도구 실행 결과 추출
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
                    # 결과에서 순수 JSON만 추출
                    raw_result = str(event["result"])
                    clean_json = extract_json_from_text(raw_result)
                    
                    yield {
                        "type": "streaming_complete",
                        "analysis_data": json.dumps(clean_json, ensure_ascii=False) if clean_json else raw_result
                    }

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
    
    AWS AgentCore Runtime 환경에서 호출되는 메인 함수입니다.
    고객의 재무 정보를 분석하여 투자 성향과 목표 수익률을 계산합니다.
    Calculator 도구를 활용하여 정확한 수치 계산을 수행합니다.
    
    Args:
        payload (dict): 요청 페이로드
            - input_data: 고객 재무 정보
    
    Yields:
        dict: 스트리밍 응답 이벤트들
    
    Note:
        - 지연 초기화로 첫 호출 시에만 FinancialAnalyst 인스턴스 생성
        - 실시간 스트리밍으로 분석 과정 전송
        - Calculator 도구를 통한 정확한 수익률 계산
        - JSON 형태의 구조화된 분석 결과 제공
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