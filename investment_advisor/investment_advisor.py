"""
investment_advisor.py
Investment Advisor Orchestrator - AI 투자 자문 오케스트레이터

Agents as Tools 패턴을 활용하여 전문 에이전트들을 조율하는 메인 오케스트레이터입니다.
사용자의 복합적인 투자 자문 요청을 분석하여 적절한 전문 에이전트에게 위임하고,
결과를 종합하여 완전한 투자 자문 서비스를 제공합니다.

전문 에이전트들:
- Financial Analyst: 개인 재무 분석 및 위험 성향 평가 (Reflection 패턴)
- Portfolio Architect: 실시간 데이터 기반 포트폴리오 설계 (Tool Use 패턴)  
- Risk Manager: 뉴스 기반 리스크 분석 및 시나리오 플래닝 (Planning 패턴)
"""

import json
import os
import sys
import boto3
from pathlib import Path
from typing import Dict, Any, Optional
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# ================================
# 전역 설정
# ================================

app = BedrockAgentCoreApp()

class Config:
    """Investment Advisor Orchestrator 설정 상수"""
    MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    TEMPERATURE = 0.2  # 조율 역할에 적합한 균형잡힌 설정
    MAX_TOKENS = 4000  # 종합적인 분석을 위한 충분한 토큰

# ================================
# 전문 에이전트 도구들 (Agents as Tools)
# ================================

@tool
def financial_analyst_tool(user_financial_data: dict) -> str:
    """
    개인 재무 상황을 분석하여 투자 성향과 목표 수익률을 계산하는 전문 에이전트
    
    Reflection 패턴을 활용하여 분석 결과의 정확성과 신뢰성을 보장합니다.
    나이, 투자 경험, 자산 규모, 목표 금액을 종합적으로 분석하여 
    5단계 위험 성향 평가와 필요 연간 수익률을 계산합니다.
    
    Args:
        user_financial_data (dict): 사용자 재무 정보
            - total_investable_amount: 총 투자 가능 금액 (원)
            - age: 나이
            - stock_investment_experience_years: 주식 투자 경험 년수
            - target_amount: 1년 후 목표 금액 (원)
    
    Returns:
        str: JSON 형태의 재무 분석 결과
            - risk_profile: 위험 성향 (매우보수적~매우공격적)
            - risk_profile_reason: 위험 성향 평가 근거
            - required_annual_return_rate: 필요 연간 수익률 (%)
            - return_rate_reason: 수익률 계산 과정 및 해석
    """
    try:
        # 환경변수에서 Financial Analyst Agent ARN 가져오기
        financial_analyst_arn = os.getenv("FINANCIAL_ANALYST_ARN")
        if not financial_analyst_arn:
            return json.dumps({"error": "Financial Analyst Agent ARN이 설정되지 않았습니다."})
        
        # AgentCore 클라이언트 생성
        region = os.getenv("AWS_REGION", "us-west-2")
        agentcore_client = boto3.client('bedrock-agentcore', region_name=region)
        
        print(f"📊 Financial Analyst 호출: {user_financial_data}")
        
        # Financial Analyst Agent 호출
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=financial_analyst_arn,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": user_financial_data})
        )
        
        # 스트리밍 응답에서 분석 결과 추출
        analysis_result = None
        reflection_result = None
        
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    
                    if event_data.get("type") == "data":
                        if "analysis_data" in event_data:
                            analysis_result = event_data["analysis_data"]
                        elif "reflection_result" in event_data:
                            reflection_result = event_data["reflection_result"]
                            
                except json.JSONDecodeError:
                    continue
        
        # 검증된 분석 결과 반환
        if analysis_result and reflection_result and reflection_result.strip().lower().startswith("yes"):
            return analysis_result
        else:
            return json.dumps({
                "error": "재무 분석 검증 실패",
                "analysis_result": analysis_result,
                "reflection_result": reflection_result
            })
            
    except Exception as e:
        return json.dumps({"error": f"Financial Analyst 호출 오류: {str(e)}"})


@tool  
def portfolio_architect_tool(financial_analysis: dict) -> str:
    """
    실시간 시장 데이터를 분석하여 맞춤형 투자 포트폴리오를 설계하는 전문 에이전트
    
    Tool Use 패턴을 활용하여 MCP Server를 통해 30개 ETF의 실시간 가격 데이터를 조회하고,
    재무 분석 결과를 바탕으로 최적의 3종목 포트폴리오를 구성합니다.
    
    Args:
        financial_analysis (dict): Financial Analyst의 분석 결과
            - risk_profile: 위험 성향
            - risk_profile_reason: 위험 성향 평가 근거  
            - required_annual_return_rate: 필요 연간 수익률
            - return_rate_reason: 수익률 계산 근거
    
    Returns:
        str: JSON 형태의 포트폴리오 설계 결과
            - portfolio_allocation: 자산별 배분 비율 (예: {"QQQ": 50, "SPY": 30, "GLD": 20})
            - strategy: 투자 전략 설명
            - reason: 포트폴리오 구성 근거
    """
    try:
        # 환경변수에서 Portfolio Architect Agent ARN 가져오기
        portfolio_architect_arn = os.getenv("PORTFOLIO_ARCHITECT_ARN")
        if not portfolio_architect_arn:
            return json.dumps({"error": "Portfolio Architect Agent ARN이 설정되지 않았습니다."})
        
        # AgentCore 클라이언트 생성
        region = os.getenv("AWS_REGION", "us-west-2")
        agentcore_client = boto3.client('bedrock-agentcore', region_name=region)
        
        print(f"🤖 Portfolio Architect 호출: {financial_analysis}")
        
        # Portfolio Architect Agent 호출
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=portfolio_architect_arn,
            qualifier="DEFAULT", 
            payload=json.dumps({"financial_analysis": financial_analysis})
        )
        
        # 스트리밍 응답에서 포트폴리오 결과 추출
        portfolio_result = ""
        
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    
                    if event_data.get("type") == "text_chunk":
                        portfolio_result += event_data.get("data", "")
                        
                except json.JSONDecodeError:
                    continue
        
        # JSON 형태의 포트폴리오 결과 추출
        start_idx = portfolio_result.find('{')
        end_idx = portfolio_result.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = portfolio_result[start_idx:end_idx]
            # JSON 유효성 검증
            json.loads(json_str)  # 파싱 테스트
            return json_str
        else:
            return json.dumps({"error": "포트폴리오 JSON 결과를 찾을 수 없습니다.", "raw_result": portfolio_result})
            
    except Exception as e:
        return json.dumps({"error": f"Portfolio Architect 호출 오류: {str(e)}"})


@tool
def risk_manager_tool(portfolio_data: dict) -> str:
    """
    포트폴리오 제안을 바탕으로 뉴스 기반 리스크 분석 및 시나리오 플래닝을 수행하는 전문 에이전트
    
    Planning 패턴을 활용하여 체계적으로 데이터를 수집하고 분석하여,
    2개의 핵심 경제 시나리오를 도출하고 각 시나리오별 포트폴리오 조정 전략을 제시합니다.
    
    Args:
        portfolio_data (dict): Portfolio Architect의 포트폴리오 설계 결과
            - portfolio_allocation: 자산별 배분 비율
            - strategy: 투자 전략 설명
            - reason: 포트폴리오 구성 근거
    
    Returns:
        str: JSON 형태의 리스크 분석 및 시나리오 플래닝 결과
            - scenario1: 첫 번째 경제 시나리오 및 조정 전략
            - scenario2: 두 번째 경제 시나리오 및 조정 전략
            각 시나리오는 name, description, allocation_management, reason 포함
    """
    try:
        # 환경변수에서 Risk Manager Agent ARN 가져오기
        risk_manager_arn = os.getenv("RISK_MANAGER_ARN")
        if not risk_manager_arn:
            return json.dumps({"error": "Risk Manager Agent ARN이 설정되지 않았습니다."})
        
        # AgentCore 클라이언트 생성
        region = os.getenv("AWS_REGION", "us-west-2")
        agentcore_client = boto3.client('bedrock-agentcore', region_name=region)
        
        print(f"⚠️ Risk Manager 호출: {portfolio_data}")
        
        # Risk Manager Agent 호출
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=risk_manager_arn,
            qualifier="DEFAULT",
            payload=json.dumps({"portfolio_data": portfolio_data})
        )
        
        # 스트리밍 응답에서 리스크 분석 결과 추출
        risk_analysis_result = ""
        
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    
                    if event_data.get("type") == "text_chunk":
                        risk_analysis_result += event_data.get("data", "")
                        
                except json.JSONDecodeError:
                    continue
        
        # JSON 형태의 리스크 분석 결과 추출
        start_idx = risk_analysis_result.find('{')
        end_idx = risk_analysis_result.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = risk_analysis_result[start_idx:end_idx]
            # JSON 유효성 검증
            json.loads(json_str)  # 파싱 테스트
            return json_str
        else:
            return json.dumps({"error": "리스크 분석 JSON 결과를 찾을 수 없습니다.", "raw_result": risk_analysis_result})
            
    except Exception as e:
        return json.dumps({"error": f"Risk Manager 호출 오류: {str(e)}"})

# ================================
# 메인 오케스트레이터 클래스
# ================================

class InvestmentAdvisorOrchestrator:
    """
    AI 투자 자문 오케스트레이터 - Agents as Tools 패턴 구현
    
    사용자의 투자 자문 요청을 분석하여 적절한 전문 에이전트들에게 순차적으로 위임하고,
    각 에이전트의 결과를 종합하여 완전한 투자 자문 서비스를 제공합니다.
    
    워크플로우:
    1. 사용자 재무 정보 → Financial Analyst (재무 분석)
    2. 재무 분석 결과 → Portfolio Architect (포트폴리오 설계)  
    3. 포트폴리오 결과 → Risk Manager (리스크 분석 및 시나리오 플래닝)
    4. 모든 결과 종합 → 최종 투자 자문 보고서 생성
    """
    
    def __init__(self):
        """투자 자문 오케스트레이터 초기화"""
        self._create_orchestrator_agent()
    
    def _create_orchestrator_agent(self):
        """오케스트레이터 에이전트 생성"""
        self.orchestrator_agent = Agent(
            name="investment_advisor_orchestrator",
            model=BedrockModel(
                model_id=Config.MODEL_ID,
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS
            ),
            system_prompt=self._get_orchestrator_prompt(),
            tools=[financial_analyst_tool, portfolio_architect_tool, risk_manager_tool]
        )
    
    def _get_orchestrator_prompt(self) -> str:
        """
        오케스트레이터 에이전트용 시스템 프롬프트 생성
        
        Returns:
            str: 오케스트레이터 역할과 작업 지침이 포함된 프롬프트
        """
        return """당신은 전문적인 투자 자문 오케스트레이터입니다. 사용자의 투자 자문 요청을 받아 전문 에이전트들을 순차적으로 조율하여 완전한 투자 자문 서비스를 제공해야 합니다.

사용 가능한 전문 에이전트 도구들:

1. **financial_analyst_tool**: 개인 재무 분석 및 위험 성향 평가 전문가
   - 입력: 사용자 재무 정보 (나이, 투자경험, 자산, 목표금액)
   - 출력: 위험 성향 평가 및 필요 연간 수익률 계산
   - 사용 시점: 사용자의 기본 재무 정보가 제공되었을 때

2. **portfolio_architect_tool**: 실시간 데이터 기반 포트폴리오 설계 전문가  
   - 입력: Financial Analyst의 분석 결과
   - 출력: 30개 ETF 중 최적 3종목 포트폴리오 구성
   - 사용 시점: 재무 분석이 완료된 후

3. **risk_manager_tool**: 뉴스 기반 리스크 분석 및 시나리오 플래닝 전문가
   - 입력: Portfolio Architect의 포트폴리오 설계 결과  
   - 출력: 2개 경제 시나리오별 포트폴리오 조정 전략
   - 사용 시점: 포트폴리오 설계가 완료된 후

**작업 순서 (반드시 순차적으로 실행):**

1. 사용자 재무 정보를 받으면 **financial_analyst_tool**을 먼저 호출
2. 재무 분석 결과를 받으면 **portfolio_architect_tool**을 호출  
3. 포트폴리오 설계 결과를 받으면 **risk_manager_tool**을 호출
4. 모든 결과를 종합하여 최종 투자 자문 보고서 작성

**최종 보고서 형식:**
```
# 🎯 종합 투자 자문 보고서

## 📊 재무 분석 요약
- 위험 성향: [결과]
- 목표 수익률: [결과]
- 분석 근거: [요약]

## 🤖 추천 포트폴리오  
- 자산 배분: [결과]
- 투자 전략: [요약]
- 구성 근거: [요약]

## ⚠️ 리스크 관리 전략
### 시나리오 1: [이름]
- 상황: [설명]
- 조정 전략: [배분 변경]
- 근거: [이유]

### 시나리오 2: [이름]  
- 상황: [설명]
- 조정 전략: [배분 변경]
- 근거: [이유]

## 💡 최종 권고사항
[종합적인 투자 조언 및 주의사항]
```

**중요 지침:**
- 반드시 순차적으로 도구를 호출하세요 (financial_analyst → portfolio_architect → risk_manager)
- 각 도구의 결과를 다음 도구의 입력으로 정확히 전달하세요
- 모든 결과를 종합하여 일관성 있는 최종 보고서를 작성하세요
- 사용자가 이해하기 쉽도록 전문 용어는 간단히 설명하세요"""
    
    async def provide_investment_advice_async(self, user_request):
        """
        실시간 스트리밍 투자 자문 서비스 제공
        
        사용자의 투자 자문 요청을 받아 전문 에이전트들을 순차적으로 조율하여
        완전한 투자 자문 서비스를 제공합니다. 전체 과정을 스트리밍으로 실시간 전송합니다.
        
        Args:
            user_request (dict): 사용자 투자 자문 요청
                - user_financial_data: 재무 정보
                - additional_requirements: 추가 요구사항 (선택사항)
            
        Yields:
            dict: 스트리밍 이벤트
                - text_chunk: 오케스트레이터의 실시간 분석 과정
                - tool_use: 전문 에이전트 호출 시작 알림
                - tool_result: 전문 에이전트 실행 결과
                - final_report: 최종 투자 자문 보고서
                - streaming_complete: 자문 완료 신호
                - error: 오류 발생 시
        """
        try:
            # 사용자 요청을 JSON 문자열로 변환
            request_str = json.dumps(user_request, ensure_ascii=False, indent=2)
            
            # 오케스트레이터 에이전트 실행 (스트리밍)
            async for event in self.orchestrator_agent.stream_async(request_str):
                
                # AI 생각 과정 텍스트 스트리밍
                if "data" in event:
                    yield {
                        "type": "text_chunk",
                        "data": event["data"],
                        "complete": event.get("complete", False)
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
                    yield {
                        "type": "streaming_complete",
                        "message": "종합 투자 자문 완료!"
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
advisor = None

@app.entrypoint
async def investment_advisor_orchestrator(payload):
    """
    AgentCore Runtime 엔트리포인트
    
    AWS AgentCore Runtime 환경에서 호출되는 메인 함수입니다.
    사용자의 투자 자문 요청을 받아 전문 에이전트들을 조율하여 완전한 투자 자문 서비스를 제공합니다.
    
    Args:
        payload (dict): 요청 페이로드
            - user_request: 사용자 투자 자문 요청
                - user_financial_data: 재무 정보
                - additional_requirements: 추가 요구사항 (선택사항)
    
    Yields:
        dict: 스트리밍 응답 이벤트들
    
    Environment Variables:
        - FINANCIAL_ANALYST_ARN: Financial Analyst Agent ARN
        - PORTFOLIO_ARCHITECT_ARN: Portfolio Architect Agent ARN  
        - RISK_MANAGER_ARN: Risk Manager Agent ARN
        - AWS_REGION: AWS 리전 (기본값: us-west-2)
    """
    global advisor
    
    # Runtime 환경에서 지연 초기화
    if advisor is None:
        # 필수 환경변수 확인
        required_vars = ["FINANCIAL_ANALYST_ARN", "PORTFOLIO_ARCHITECT_ARN", "RISK_MANAGER_ARN"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            yield {
                "type": "error",
                "error": f"필수 환경변수 누락: {', '.join(missing_vars)}",
                "status": "error"
            }
            return
        
        # InvestmentAdvisorOrchestrator 인스턴스 생성
        advisor = InvestmentAdvisorOrchestrator()

    # 사용자 요청 추출 및 투자 자문 실행
    user_request = payload.get("user_request")
    async for chunk in advisor.provide_investment_advice_async(user_request):
        yield chunk

# ================================
# 직접 실행 시 Runtime 서버 시작
# ================================

if __name__ == "__main__":
    app.run()