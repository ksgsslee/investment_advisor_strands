"""
portfolio_architect.py
Portfolio Architect - AI 포트폴리오 설계사

MCP Server와 연동하여 실시간 시장 데이터를 분석하고
맞춤형 투자 포트폴리오를 제안하는 AI 에이전트입니다.
"""

import json
import os
import sys
import boto3
import time
from pathlib import Path
from typing import Dict, Any
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# ================================
# 전역 설정
# ================================

app = BedrockAgentCoreApp()

class Config:
    """Portfolio Architect 설정 상수"""
    MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    TEMPERATURE = 0.3
    MAX_TOKENS = 3000

# ================================
# 유틸리티 함수들
# ================================

def load_mcp_server_info():
    """
    MCP Server 배포 정보 로드 (로컬 JSON 우선)
    
    Returns:
        dict: MCP Server 설정 정보 (agent_arn, bearer_token 등)
        
    Raises:
        Exception: 배포 정보 로드 실패 시
    """
    region = os.getenv("AWS_REGION", "us-west-2")
    
    try:
        # 로컬 배포 정보에서 먼저 로드 시도
        print("📋 로컬 MCP Server 정보 로드 중...")
        current_dir = Path(__file__).parent
        info_file = current_dir / "mcp" / "mcp_deployment_info.json"
        
        if info_file.exists():
            with open(info_file, 'r') as f:
                local_info = json.load(f)
            
            agent_arn = local_info['agent_arn']
            bearer_token = local_info['bearer_token']
            
            # MCP URL 구성
            encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
            mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
            
            print(f"✅ 로컬 MCP Server 정보 로드 완료")
            print(f"🔗 Agent ARN: {agent_arn}")
            print(f"🌐 MCP URL: {mcp_url}")
            
            return {
                "agent_arn": agent_arn,
                "bearer_token": bearer_token,
                "mcp_url": mcp_url,
                "region": region
            }
        else:
            raise FileNotFoundError("로컬 MCP Server 배포 정보 파일 없음")
            
    except Exception as e:
        print(f"❌ 로컬 정보 로드 실패: {str(e)}")
        raise Exception(f"MCP Server 정보 로드 실패: {str(e)}")

def create_streamable_http_transport(mcp_url: str, bearer_token: str):
    """
    MCP HTTP 전송 클라이언트 생성
    
    Args:
        mcp_url (str): MCP Server URL
        bearer_token (str): JWT Bearer 토큰
        
    Returns:
        StreamableHTTPTransport: MCP 클라이언트 전송 객체
    """
    headers = {
        "authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    return streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False)

# ================================
# 메인 클래스
# ================================

class PortfolioArchitect:
    """
    AI 포트폴리오 설계사 - MCP Server 연동
    
    실시간 시장 데이터를 분석하여 고객의 재무 상황에 맞는
    맞춤형 투자 포트폴리오를 설계하는 AI 에이전트입니다.
    """
    
    def __init__(self, mcp_server_info=None):
        """
        포트폴리오 설계사 초기화
        
        Args:
            mcp_server_info (dict, optional): MCP Server 정보. None이면 AWS에서 자동 로드
        """
        # MCP Server 정보 설정
        self.mcp_server_info = mcp_server_info or load_mcp_server_info()
        self._initialize_mcp_client()
        self._create_architect_agent()
    
    def _initialize_mcp_client(self):
        """MCP 클라이언트 초기화"""
        self.mcp_client = MCPClient(
            lambda: create_streamable_http_transport(
                self.mcp_server_info["mcp_url"], 
                self.mcp_server_info["bearer_token"]
            )
        )
    
    def _create_architect_agent(self):
        """포트폴리오 설계사 에이전트 생성"""
        with self.mcp_client as client:
            # 사용 가능한 도구 목록 가져오기
            tools = client.list_tools_sync()
            tool_names = [tool.tool_name for tool in tools]
            print(f"🛠️ 사용 가능한 도구: {', '.join(tool_names)}")

            # AI 에이전트 생성
            self.architect_agent = Agent(
                name="portfolio_architect",
                model=BedrockModel(
                    model_id=Config.MODEL_ID,
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS
                ),
                callback_handler=None,
                system_prompt=self._get_system_prompt(),
                tools=tools
            )
    
    def _get_system_prompt(self) -> str:
        """
        AI 에이전트용 시스템 프롬프트 생성
        
        Returns:
            str: 포트폴리오 설계사 역할과 작업 지침이 포함된 프롬프트
        """
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
2. "get_available_products" 도구를 호출하여 사용 가능한 투자 상품 목록을 얻으세요.
3. 얻은 투자 상품 목록 중 분산 투자를 고려하여 고객의 재무 분석 결과와 가장 적합한 3개의 상품을 선택하세요.
4. 선택한 각 투자 상품에 대해 "get_product_data" 도구를 동시에 호출하여 최근 가격 데이터를 얻으세요.
5. 얻은 가격 데이터를 분석하여 최종 포트폴리오 비율을 결정하세요.
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
        """
        실시간 스트리밍 포트폴리오 설계 수행
        
        재무 분석 결과를 바탕으로 AI가 실시간으로 포트폴리오를 설계합니다.
        도구 사용과 분석 과정을 스트리밍 이벤트로 실시간 전송합니다.
        
        Args:
            financial_analysis (dict): 재무 분석 결과
                - risk_profile: 위험 성향
                - risk_profile_reason: 위험 성향 평가 근거
                - required_annual_return_rate: 필요 연간 수익률
                - return_rate_reason: 수익률 계산 근거
            
        Yields:
            dict: 스트리밍 이벤트
                - text_chunk: AI의 실시간 분석 과정
                - tool_use: 도구 사용 시작 알림
                - tool_result: 도구 실행 결과
                - portfolio_result: 추출된 포트폴리오 JSON
                - streaming_complete: 분석 완료 신호
                - error: 오류 발생 시
        """
        try:
            # 재무 분석 결과를 JSON 문자열로 변환
            analysis_str = json.dumps(financial_analysis, ensure_ascii=False, indent=2)
            
            # MCP 클라이언트 컨텍스트 내에서 에이전트 실행
            with self.mcp_client:
                async for event in self.architect_agent.stream_async(analysis_str):
                    
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
                            "message": "포트폴리오 설계 완료!"
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
architect = None

@app.entrypoint
async def portfolio_architect(payload):
    """
    AgentCore Runtime 엔트리포인트
    
    AWS AgentCore Runtime 환경에서 호출되는 메인 함수입니다.
    AWS에서 MCP Server 정보를 로드하여 포트폴리오 설계를 수행합니다.
    
    Args:
        payload (dict): 요청 페이로드
            - financial_analysis: 재무 분석 결과
    
    Yields:
        dict: 스트리밍 응답 이벤트들
    """
    global architect
    
    # Runtime 환경에서 지연 초기화
    if architect is None:
        # PortfolioArchitect 인스턴스 생성 (AWS에서 MCP Server 정보 자동 로드)
        architect = PortfolioArchitect()

    # 재무 분석 결과 추출 및 포트폴리오 설계 실행
    financial_analysis = payload.get("financial_analysis")
    async for chunk in architect.design_portfolio_async(financial_analysis):
        yield chunk

# ================================
# 직접 실행 시 Runtime 서버 시작
# ================================

if __name__ == "__main__":
    app.run()
