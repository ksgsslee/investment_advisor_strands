"""
risk_manager.py

Risk Manager - AI 리스크 관리사
MCP Gateway 연동으로 실시간 뉴스 및 시장 데이터 기반 리스크 분석
"""

import json
import os
import requests
from pathlib import Path
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class Config:
    """Risk Manager 설정"""
    MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    TEMPERATURE = 0.2
    MAX_TOKENS = 4000


def load_gateway_info():
    """Gateway 배포 정보를 JSON 파일에서 로드"""
    gateway_dir = Path(__file__).parent / "gateway"
    info_file = gateway_dir / "gateway_deployment_info.json"
    
    if not info_file.exists():
        raise FileNotFoundError(
            f"Gateway 배포 정보 파일을 찾을 수 없습니다: {info_file}\n"
            "먼저 'python gateway/deploy_gateway.py'를 실행하세요."
        )
    
    with open(info_file, 'r') as f:
        return json.load(f)


class RiskManager:
    """AI 리스크 관리사 - MCP Gateway 연동"""
    
    def __init__(self, gateway_info=None):
        self.gateway_info = gateway_info or load_gateway_info()
        self._setup_auth()
        self._init_mcp_client()
        self._create_agent()
    
    def _setup_auth(self):
        info = self.gateway_info
        self.gateway_url = info['gateway_url']
        
        # Cognito 토큰 URL 구성
        pool_domain = info['user_pool_id'].replace("_", "").lower()
        token_url = f"https://{pool_domain}.auth.{info['region']}.amazoncognito.com/oauth2/token"
        
        # 액세스 토큰 획득
        response = requests.post(
            token_url,
            data=f"grant_type=client_credentials&client_id={info['client_id']}&client_secret={info['client_secret']}",
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        self.access_token = response.json()['access_token']
    
    def _init_mcp_client(self):
        self.mcp_client = MCPClient(
            lambda: streamablehttp_client(
                self.gateway_url, 
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
        )
    
    def _create_agent(self):
        with self.mcp_client as client:
            tools = client.list_tools_sync()
            
            self.agent = Agent(
                name="risk_manager",
                model=BedrockModel(
                    model_id=Config.MODEL_ID,
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS
                ),
                system_prompt=self._get_prompt(),
                tools=tools
            )
    
    def _get_prompt(self):
        return """당신은 리스크 관리 전문가입니다. 제안된 포트폴리오에 대해 리스크 분석을 수행하고, 주요 경제 시나리오에 따른 포트폴리오 조정 가이드를 제공해야 합니다.

입력 데이터:
제안된 포트폴리오 구성이 다음과 같은 JSON 형식으로 제공됩니다:
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
2. 발생 가능성이 높은 2개의 경제 시나리오를 도출  
3. 각 시나리오에 대한 포트폴리오 조정 방안을 제시

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
1. 포트폴리오 조정 시 입력으로 받은 상품(ticker)만을 사용하세요
2. 새로운 상품을 추가하거나 기존 상품을 제거하지 마세요
3. 각 시나리오별 조정 비율의 총합이 100%가 되도록 하세요
4. 포트폴리오 구성 근거를 상세히 설명하세요
5. JSON 앞뒤에 백틱(```) 또는 따옴표를 붙이지 말고 순수한 JSON 형식만 출력하세요"""
    
    async def analyze_risk_async(self, portfolio_data):
        try:
            portfolio_str = json.dumps(portfolio_data, ensure_ascii=False)
            
            with self.mcp_client:
                async for event in self.agent.stream_async(portfolio_str):
                    if "data" in event:
                        yield {"type": "text_chunk", "data": event["data"]}
                    
                    if "message" in event:
                        message = event["message"]
                        
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
                    
                    if "result" in event:
                        yield {"type": "streaming_complete", "risk_result": str(event["result"])}

        except Exception as e:
            yield {"type": "error", "error": str(e), "status": "error"}

# 전역 인스턴스
manager = None

@app.entrypoint
async def risk_manager(payload):
    """AgentCore Runtime 엔트리포인트"""
    global manager
    
    if manager is None:
        # 환경변수에서 Gateway 정보 구성
        gateway_info = {
            "client_id": os.getenv("MCP_CLIENT_ID"),
            "client_secret": os.getenv("MCP_CLIENT_SECRET"), 
            "gateway_url": os.getenv("MCP_GATEWAY_URL"),
            "user_pool_id": os.getenv("MCP_USER_POOL_ID"),
            "region": os.getenv("AWS_REGION", "us-west-2"),
            "target_id": os.getenv("MCP_TARGET_ID", "target-risk-manager")
        }
        
        manager = RiskManager(gateway_info)

    portfolio_data = payload.get("portfolio_data")
    async for chunk in manager.analyze_risk_async(portfolio_data):
        yield chunk

if __name__ == "__main__":
    app.run()