"""
risk_manager.py
Risk Manager - AI 리스크 관리사

포트폴리오 제안을 바탕으로 뉴스 기반 리스크 분석을 수행하고,
경제 시나리오에 따른 포트폴리오 조정 가이드를 제공하는 AI 에이전트입니다.
Planning 패턴을 활용하여 체계적인 시나리오 플래닝을 수행합니다.

주요 기능:
- 포트폴리오 구성 ETF별 뉴스 분석
- 거시경제 지표 기반 시장 상황 평가
- 2개 경제 시나리오 도출 및 포트폴리오 조정 전략 수립
- MCP를 통한 실시간 데이터 연동
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import requests

# ================================
# 전역 설정
# ================================

app = BedrockAgentCoreApp()

class Config:
    """Risk Manager 설정 상수"""
    MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    TEMPERATURE = 0.2  # 분석적 사고와 창의적 시나리오 도출의 균형
    MAX_TOKENS = 4000  # 상세한 시나리오 분석을 위한 충분한 토큰

# ================================
# 유틸리티 함수들
# ================================

def load_gateway_info():
    """
    Gateway 배포 정보를 JSON 파일에서 로드
    
    Returns:
        dict: Gateway 설정 정보
        
    Raises:
        FileNotFoundError: Gateway 배포 정보 파일이 없을 때
    """
    gateway_dir = Path(__file__).parent / "gateway"
    info_file = gateway_dir / "gateway_deployment_info.json"
    
    if not info_file.exists():
        raise FileNotFoundError(
            f"Gateway 배포 정보 파일을 찾을 수 없습니다: {info_file}\n"
            "먼저 'python gateway/deploy_gateway.py'를 실행하세요."
        )
    
    with open(info_file, 'r') as f:
        gateway_info = json.load(f)
    
    print(f"📋 Gateway 정보 로드: {gateway_info['gateway_url']}")
    return gateway_info

def fetch_access_token(client_id, client_secret, token_url):
    """
    OAuth2 클라이언트 자격 증명으로 액세스 토큰 획득
    
    Args:
        client_id (str): OAuth2 클라이언트 ID
        client_secret (str): OAuth2 클라이언트 시크릿
        token_url (str): 토큰 엔드포인트 URL
        
    Returns:
        str: 액세스 토큰
    """
    response = requests.post(
        token_url,
        data=f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}",
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    response.raise_for_status()
    return response.json()['access_token']

def create_streamable_http_transport(mcp_url: str, access_token: str):
    """
    MCP HTTP 전송 클라이언트 생성
    
    Args:
        mcp_url (str): MCP Gateway URL
        access_token (str): 인증용 액세스 토큰
        
    Returns:
        StreamableHTTPTransport: MCP 클라이언트 전송 객체
    """
    return streamablehttp_client(mcp_url, headers={"Authorization": f"Bearer {access_token}"})

# ================================
# 메인 클래스
# ================================

class RiskManager:
    """
    AI 리스크 관리사 - MCP Gateway 연동
    
    포트폴리오 제안을 바탕으로 뉴스 기반 리스크 분석을 수행하고,
    경제 시나리오에 따른 포트폴리오 조정 가이드를 제공하는 AI 에이전트입니다.
    """
    
    def __init__(self, gateway_info=None):
        """
        리스크 관리사 초기화
        
        Args:
            gateway_info (dict, optional): Gateway 정보. None이면 파일에서 자동 로드
        """
        # Gateway 정보 설정
        self.gateway_info = gateway_info or load_gateway_info()
        self._setup_authentication()
        self._initialize_mcp_client()
        self._create_risk_manager_agent()
    
    def _setup_authentication(self):
        """인증 정보 설정"""
        self.client_id = self.gateway_info['client_id']
        self.client_secret = self.gateway_info['client_secret']
        self.gateway_url = self.gateway_info['gateway_url']
        
        # Cognito 토큰 URL 구성
        user_pool_id = self.gateway_info['user_pool_id']
        region = self.gateway_info['region']
        pool_domain = user_pool_id.replace("_", "").lower()
        self.token_url = f"https://{pool_domain}.auth.{region}.amazoncognito.com/oauth2/token"
        
        print(f"🔐 인증 설정: {self.token_url}")
        print(f"🌐 Gateway URL: {self.gateway_url}")
        
        # 액세스 토큰 획득
        self.access_token = fetch_access_token(
            self.client_id, 
            self.client_secret, 
            self.token_url
        )
    
    def _initialize_mcp_client(self):
        """MCP 클라이언트 초기화"""
        self.mcp_client = MCPClient(
            lambda: create_streamable_http_transport(self.gateway_url, self.access_token)
        )
    
    def _create_risk_manager_agent(self):
        """리스크 관리사 에이전트 생성"""
        with self.mcp_client as client:
            # 사용 가능한 도구 목록 가져오기
            tools = client.list_tools_sync()
            tool_names = [tool.tool_name for tool in tools]
            print(f"🛠️ 사용 가능한 도구: {', '.join(tool_names)}")

            # AI 에이전트 생성
            self.risk_manager_agent = Agent(
                name="risk_manager",
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
            str: 리스크 관리사 역할과 작업 지침이 포함된 프롬프트
        """
        target_name = self.gateway_info.get('target_id', 'target-risk-manager')
        
        return f"""당신은 리스크 관리 전문가입니다. 제안된 포트폴리오에 대해 리스크 분석을 수행하고, 주요 경제 시나리오에 따른 포트폴리오 조정 가이드를 제공해야 합니다.

입력 데이터: 제안된 포트폴리오 구성이 다음과 같은 JSON 형식으로 제공됩니다:
{{
  "portfolio_allocation": {{
    "ticker1": 비율1,
    "ticker2": 비율2,
    "ticker3": 비율3
  }},
  "strategy": "투자 전략 설명",
  "reason": "포트폴리오 구성 근거"
}}

당신의 작업:
주어진 도구(tools)들을 자유롭게 사용하여 아래 목표를 달성하세요

1. 주어진 포트폴리오에 대한 종합적인 리스크 분석
   - 포트폴리오에 포함된 각 투자 상품(ETF)에 대해 "{target_name}___get_product_news" 액션을 호출하여 최신 뉴스 정보를 얻으세요
   - "{target_name}___get_market_data" 액션을 호출하여 주요 시장 지표 데이터를 얻으세요

2. 발생 가능성이 높은 2개의 경제 시나리오를 도출
   - 뉴스 분석과 시장 지표를 바탕으로 향후 발생 가능성이 높은 2개의 경제 시나리오를 도출하세요

3. 각 시나리오에 대한 포트폴리오 조정 방안을 제시
   - 각 시나리오에 대해 포트폴리오 영향을 평가하고 적절한 조정 방안을 제시하세요

반드시 다음 형식으로 응답해주세요:
{{
  "scenario1": {{
    "name": "시나리오 1 이름",
    "description": "시나리오 1 상세 설명",
    "allocation_management": {{
      "ticker1": 새로운_비율1,
      "ticker2": 새로운_비율2,
      "ticker3": 새로운_비율3
    }},
    "reason": "조정 이유 및 전략"
  }},
  "scenario2": {{
    "name": "시나리오 2 이름",
    "description": "시나리오 2 상세 설명",
    "allocation_management": {{
      "ticker1": 새로운_비율1,
      "ticker2": 새로운_비율2,
      "ticker3": 새로운_비율3
    }},
    "reason": "조정 이유 및 전략"
  }}
}}

응답 시 다음 사항을 반드시 준수하세요:
1. 포트폴리오 조정 시 입력으로 받은 상품(ticker)만을 사용하세요.
2. 새로운 상품을 추가하거나 기존 상품을 제거하지 마세요.
3. 각 시나리오별 조정 비율의 총합이 100%가 되도록 하세요.
4. 포트폴리오 구성 근거를 상세히 설명하세요.
5. JSON 앞뒤에 백틱(```) 또는 따옴표를 붙이지 말고 순수한 JSON 형식만 출력하세요."""
    
    async def analyze_portfolio_risk_async(self, portfolio_data):
        """
        실시간 스트리밍 포트폴리오 리스크 분석 수행 (Planning 패턴 포함)
        
        포트폴리오 제안을 바탕으로 AI가 실시간으로 리스크 분석을 수행합니다.
        뉴스 수집, 시장 지표 분석, 시나리오 도출 과정을 스트리밍 이벤트로 실시간 전송합니다.
        
        Args:
            portfolio_data (dict): 포트폴리오 제안 결과
                - portfolio_allocation: 자산 배분 비율
                - strategy: 투자 전략 설명
                - reason: 포트폴리오 구성 근거
            
        Yields:
            dict: 스트리밍 이벤트
                - text_chunk: AI의 실시간 분석 과정
                - tool_use: 도구 사용 시작 알림
                - tool_result: 도구 실행 결과
                - risk_analysis_result: 추출된 리스크 분석 JSON
                - streaming_complete: 분석 완료 신호
                - error: 오류 발생 시
        """
        try:
            # 포트폴리오 데이터를 JSON 문자열로 변환
            portfolio_str = json.dumps(portfolio_data, ensure_ascii=False, indent=2)
            
            # MCP 클라이언트 컨텍스트 내에서 에이전트 실행
            with self.mcp_client:
                async for event in self.risk_manager_agent.stream_async(portfolio_str):
                    
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
                            "message": "리스크 분석 및 시나리오 플래닝 완료!"
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
risk_manager = None

@app.entrypoint
async def risk_manager_entrypoint(payload):
    """
    AgentCore Runtime 엔트리포인트
    
    AWS AgentCore Runtime 환경에서 호출되는 메인 함수입니다.
    환경변수에서 Gateway 정보를 로드하여 리스크 분석을 수행합니다.
    
    Args:
        payload (dict): 요청 페이로드
            - portfolio_data: 포트폴리오 제안 결과
    
    Yields:
        dict: 스트리밍 응답 이벤트들
    
    Environment Variables:
        - MCP_CLIENT_ID: OAuth2 클라이언트 ID
        - MCP_CLIENT_SECRET: OAuth2 클라이언트 시크릿
        - MCP_GATEWAY_URL: MCP Gateway URL
        - MCP_USER_POOL_ID: Cognito User Pool ID
        - AWS_REGION: AWS 리전 (기본값: us-west-2)
        - MCP_TARGET_ID: MCP 타겟 ID (기본값: target-risk-manager)
    """
    global risk_manager
    
    # Runtime 환경에서 지연 초기화
    if risk_manager is None:
        # 필수 환경변수 확인
        required_vars = ["MCP_CLIENT_ID", "MCP_CLIENT_SECRET", "MCP_GATEWAY_URL", "MCP_USER_POOL_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise RuntimeError(f"필수 환경변수 누락: {', '.join(missing_vars)}")

        # 환경변수에서 Gateway 정보 구성
        gateway_info = {
            "client_id": os.getenv("MCP_CLIENT_ID"),
            "client_secret": os.getenv("MCP_CLIENT_SECRET"), 
            "gateway_url": os.getenv("MCP_GATEWAY_URL"),
            "user_pool_id": os.getenv("MCP_USER_POOL_ID"),
            "region": os.getenv("AWS_REGION", "us-west-2"),
            "target_id": os.getenv("MCP_TARGET_ID", "target-risk-manager")
        }
        
        # RiskManager 인스턴스 생성
        risk_manager = RiskManager(gateway_info)

    # 포트폴리오 데이터 추출 및 리스크 분석 실행
    portfolio_data = payload.get("portfolio_data")
    async for chunk in risk_manager.analyze_portfolio_risk_async(portfolio_data):
        yield chunk

# ================================
# 직접 실행 시 Runtime 서버 시작
# ================================

if __name__ == "__main__":
    app.run()