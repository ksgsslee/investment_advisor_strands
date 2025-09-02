"""
portfolio_architect.py

Portfolio Architect - AI 포트폴리오 설계사
MCP Server 연동으로 실시간 ETF 데이터 기반 포트폴리오 설계
"""

import json
import os
import requests
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class Config:
    """Portfolio Architect 설정"""
    MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    TEMPERATURE = 0.3
    MAX_TOKENS = 3000

class PortfolioArchitect:
    def __init__(self, mcp_server_info):
        self.mcp_server_info = mcp_server_info
        self._setup_auth()
        self._init_mcp_client()
        self._create_agent()
    
    def _setup_auth(self):
        info = self.mcp_server_info
        self.mcp_url = info['mcp_url']
        
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
                self.mcp_url, 
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
        )
    
    def _create_agent(self):
        with self.mcp_client as client:
            tools = client.list_tools_sync()
            
            self.agent = Agent(
                name="portfolio_architect",
                model=BedrockModel(
                    model_id=Config.MODEL_ID,
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS
                ),
                system_prompt=self._get_prompt(),
                tools=tools
            )
    
    def _get_prompt(self):
        return """당신은 전문 투자 설계사입니다. 고객의 재무 분석 결과를 바탕으로 구체적인 투자 포트폴리오를 제안해야 합니다. 

재무 분석 결과가 다음과 같은 JSON 형식으로 제공됩니다:
{
  "risk_profile": <위험 성향>,
  "risk_profile_reason": <위험 성향 평가 근거>,
  "required_annual_return_rate": <필요 연간 수익률>,
  "return_rate_reason": <필요 수익률 계산 근거 및 설명>,
  "summary": <종합 총평>
}

당신의 작업:
1. 재무 분석 결과를 신중히 검토하고 해석하세요.
2. "get_available_products" 도구를 호출하여 사용 가능한 투자 상품 목록을 얻으세요.
3. 얻은 투자 상품 목록 중 분산 투자를 고려하여 고객의 재무 분석 결과와 가장 적합한 3개의 상품을 선택하세요.
4. 선택한 3개 ETF 각각에 대해 "analyze_etf_performance" 도구를 사용하여 몬테카를로 시뮬레이션 성과를 분석하세요.
5. 각 ETF의 분석 결과(예상 수익률, 손실 확률, 변동성, 과거 수익률)를 바탕으로 최적의 투자 비중을 결정하세요.
6. 고객의 위험 성향과 목표 수익률을 고려하여 최종 포트폴리오를 제안하세요.

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
        analysis_str = json.dumps(financial_analysis, ensure_ascii=False)
        
        with self.mcp_client:
            async for event in self.agent.stream_async(analysis_str):
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
                    yield {"type": "streaming_complete", "portfolio_result": str(event["result"])}

# 전역 인스턴스
architect = None

@app.entrypoint
async def portfolio_architect(payload):
    global architect
    
    if architect is None:
        # 환경변수에서 MCP Server 정보 구성
        region = os.getenv("AWS_REGION", "us-west-2")
        mcp_agent_arn = os.getenv("MCP_AGENT_ARN")
        encoded_arn = mcp_agent_arn.replace(':', '%3A').replace('/', '%2F')
        
        mcp_server_info = {
            "mcp_url": f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT",
            "region": region,
            "client_id": os.getenv("MCP_CLIENT_ID"),
            "client_secret": os.getenv("MCP_CLIENT_SECRET"),
            "user_pool_id": os.getenv("MCP_USER_POOL_ID")
        }
        
        architect = PortfolioArchitect(mcp_server_info)

    financial_analysis = payload.get("financial_analysis")
    async for chunk in architect.design_portfolio_async(financial_analysis):
        yield chunk

if __name__ == "__main__":
    app.run()