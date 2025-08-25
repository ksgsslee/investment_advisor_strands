"""
financial_analyst.py
Financial Analyst - AI 재무 분석사

개인의 재무 상황을 분석하여 투자 성향과 목표 수익률을 계산하는 AI 에이전트입니다.
Reflection 패턴을 활용하여 분석 결과의 품질을 보장합니다.

주요 기능:
- 개인 재무 상황 종합 분석
- 위험 성향 평가 및 근거 제시
- 목표 수익률 계산 및 달성 가능성 분석
- Reflection을 통한 분석 결과 검증
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any
from strands import Agent
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# ================================
# 전역 설정
# ================================

app = BedrockAgentCoreApp()

class Config:
    """Financial Analyst 설정 상수"""
    # 재무 분석사 모델 설정
    ANALYST_MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    ANALYST_TEMPERATURE = 0.1
    ANALYST_MAX_TOKENS = 2000
    
    # Reflection 검증 모델 설정 (다른 모델 사용 가능)
    REFLECTION_MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    REFLECTION_TEMPERATURE = 0.1
    REFLECTION_MAX_TOKENS = 2000

# ================================
# 메인 클래스
# ================================

class FinancialAnalyst:
    """
    AI 재무 분석사 - Reflection 패턴 구현
    
    개인의 재무 상황을 종합적으로 분석하여 투자 성향과 목표 수익률을 계산합니다.
    Reflection 패턴을 통해 분석 결과의 정확성과 신뢰성을 검증합니다.
    """
    
    def __init__(self):
        """
        재무 분석사 초기화
        
        AI 에이전트들을 생성하고 재무 분석을 위한 시스템 프롬프트를 설정합니다.
        """
        self._create_analyst_agent()
        self._create_reflection_agent()
    
    def _create_analyst_agent(self):
        """재무 분석사 AI 에이전트 생성"""
        self.analyst_agent = Agent(
            name="financial_analyst",
            model=BedrockModel(
                model_id=Config.ANALYST_MODEL_ID,
                temperature=Config.ANALYST_TEMPERATURE,
                max_tokens=Config.ANALYST_MAX_TOKENS
            ),
            system_prompt=self._get_analyst_prompt()
        )
    
    def _create_reflection_agent(self):
        """Reflection 검증 AI 에이전트 생성"""
        self.reflection_agent = Agent(
            name="reflection_validator",
            model=BedrockModel(
                model_id=Config.REFLECTION_MODEL_ID,
                temperature=Config.REFLECTION_TEMPERATURE,
                max_tokens=Config.REFLECTION_MAX_TOKENS
            ),
            system_prompt=self._get_reflection_prompt()
        )
        
    def _get_analyst_prompt(self) -> str:
        """
        재무 분석사 AI 에이전트용 시스템 프롬프트 생성
        
        Returns:
            str: 재무 분석사 역할과 작업 지침이 포함된 프롬프트
        """
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
        """
        Reflection 검증 AI 에이전트용 시스템 프롬프트 생성
        
        Returns:
            str: Reflection 검증 역할과 작업 지침이 포함된 프롬프트
        """
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
    
    async def analyze_financial_situation_async(self, user_input):
        """
        실시간 스트리밍 재무 분석 수행 (Reflection 패턴 포함)
        
        고객의 재무 정보를 바탕으로 AI가 실시간으로 분석을 수행합니다.
        분석 과정과 결과를 스트리밍 이벤트로 실시간 전송하며,
        Reflection 패턴을 통해 분석 결과의 품질을 검증합니다.
        
        Args:
            user_input (dict): 고객 재무 정보
                - total_investable_amount: 총 투자 가능 금액
                - age: 나이
                - stock_investment_experience_years: 주식 투자 경험 년수
                - target_amount: 1년 후 목표 금액
            
        Yields:
            dict: 스트리밍 이벤트
                - analysis_data: 재무 분석 결과 JSON
                - reflection_result: Reflection 검증 결과
                - streaming_complete: 분석 완료 신호
                - error: 오류 발생 시
        """
        try:
            # 고객 정보를 JSON 문자열로 변환
            user_input_str = json.dumps(user_input, ensure_ascii=False)

            # 1단계: 재무 분석 수행
            analyst_response = self.analyst_agent(user_input_str)
            analysis_data = analyst_response.message['content'][0]['text']

            # 재무 분석 결과 전송
            yield {
                "type": "data", 
                "analysis_data": analysis_data
            }

            # 2단계: Reflection 검증 수행
            reflection_response = self.reflection_agent(analysis_data)
            reflection_result = reflection_response.message['content'][0]['text']
            
            # Reflection 검증 결과 전송
            yield {
                "type": "data", 
                "reflection_result": reflection_result
            }
            
            # 분석 완료 신호 (최종 결과 포함)
            yield {
                "type": "streaming_complete",
                "analysis_data": analysis_data,
                "reflection_result": reflection_result
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
    고객의 재무 정보를 분석하여 투자 성향과 목표 수익률을 계산하고,
    Reflection 패턴을 통해 분석 결과의 품질을 검증합니다.
    
    Args:
        payload (dict): 요청 페이로드
            - input_data: 고객 재무 정보
    
    Yields:
        dict: 스트리밍 응답 이벤트들
    
    Note:
        - 지연 초기화로 첫 호출 시에만 FinancialAnalyst 인스턴스 생성
        - 실시간 스트리밍으로 분석 과정 전송
        - Reflection을 통한 분석 결과 검증
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