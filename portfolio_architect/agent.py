"""
portfolio_architect.py
포트폴리오 설계사 + MCP Gateway 연동 버전 (Guide Style)
"""
import json
import os
import sys
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp


app = BedrockAgentCoreApp()

 
def fetch_access_token(client_id, client_secret, token_url):
    response = requests.post(
        token_url,
        data=f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}",
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    return response.json()['access_token']

def create_streamable_http_transport(mcp_url: str, access_token: str):
    return streamablehttp_client(mcp_url, headers={"Authorization": f"Bearer {access_token}"})

def get_full_tools_list(client):
    """List tools w/ support for pagination"""
    more_tools = True
    tools = []
    pagination_token = None
    while more_tools:
        tmp_tools = client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(tmp_tools)
        if tmp_tools.pagination_token is None:
            more_tools = False
        else:
            more_tools = True 
            pagination_token = tmp_tools.pagination_token
    return tools

class PortfolioArchitect:
    def __init__(self, client_id, client_secret, token_url, gateway_url, target_name):
        # 설정값 초기화 (모든 값 필수)
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.gateway_url = gateway_url
        self.target_name = target_name
        
        # 액세스 토큰 획득
        self.access_token = fetch_access_token(self.client_id, self.client_secret, self.token_url)
        
        # MCP 클라이언트 생성
        self.mcp_client = MCPClient(lambda: create_streamable_http_transport(self.gateway_url, self.access_token))
        
        # 도구 목록 가져오기 (임시로 컨텍스트 열고 닫기)
        with self.mcp_client as client:
            # tools = get_full_tools_list(self.mcp_client)
            # tools = get_full_tools_list(self.mcp_client)
            tools = client.list_tools_sync()
            print(f"Found the following tools: {[tool.tool_name for tool in tools]}")

            # 포트폴리오 설계사 에이전트 (MCP 도구들과 함께)
            self.architect_agent = Agent(
                name="portfolio_architect",
                model=BedrockModel(
                    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                    temperature=0.3,
                    max_tokens=3000
                ),
                callback_handler=None,
                system_prompt=self._get_system_prompt(),
                tools=tools
            )
    
    def _get_system_prompt(self) -> str:
        return f"""당신은 전문 투자 설계사입니다. 고객의 재무 분석 결과를 바탕으로 구체적인 투자 포트폴리오를 제안해야 합니다. 

재무 분석 결과가 다음과 같은 JSON 형식으로 제공됩니다:
{{
  "risk_profile": <위험 성향>,
  "risk_profile_reason": <위험 성향 평가 근거>,
  "required_annual_return_rate": <필요 연간 수익률>,
  "return_rate_reason": <필요 수익률 계산 근거 및 설명>
}}

당신의 작업:
1. 재무 분석 결과를 신중히 검토하고 해석하세요.
2. "{self.target_name}___get_available_products" 액션을 호출하여 사용 가능한 투자 상품 목록을 얻으세요.
3. 얻은 투자 상품 목록 중 분산 투자를 고려하여 고객의 재무 분석 결과와 가장 적합한 3개의 상품을 선택하세요.
4. 선택한 각 투자 상품에 대해 "{self.target_name}___get_product_data" 액션을 동시에 호출하여 최근 가격 데이터를 얻으세요.
5. 얻은 가격 데이터를 분석하여 최종 포트폴리오 비율을 결정하세요.
6. 포트폴리오 구성 근거를 상세히 설명하세요.

다음 JSON 형식으로 응답해주세요:
{{
  "portfolio_allocation": {{투자 상품별 배분 비율}} (예: {{"ticker1": 50, "ticker2": 30, "ticker3": 20}}),
  "strategy": "투자 전략 설명",
  "reason": "포트폴리오 구성 근거"
}}

응답 시 다음 사항을 고려하세요:
- 제안한 포트폴리오가 고객의 투자 목표 달성에 어떻게 도움이 될 것인지 논리적으로 설명하세요.
- 각 자산의 배분 비율은 반드시 정수로 표현하고, 총합이 100%가 되어야 합니다.
- 포트폴리오 구성 근거를 작성할때는 반드시 "QQQ(미국 기술주)" 처럼 티커와 설명을 함께 제공하세요.
- JSON 앞뒤에 백틱(```) 또는 따옴표를 붙이지 말고 순수한 JSON 형식만 출력하세요."""
    
    async def design_portfolio_async(self, financial_analysis):
        """실시간 스트리밍 포트폴리오 설계 수행"""
        try:
            # 재무 분석 결과를 프롬프트로 구성
            analysis_str = json.dumps(financial_analysis, ensure_ascii=False, indent=2)
            
            # 🎯 MCP 클라이언트 컨텍스트 내에서 에이전트 실행 (동기 컨텍스트 매니저 사용)
            with self.mcp_client:
                async for event in self.architect_agent.stream_async(analysis_str):
                    # 텍스트 데이터 스트리밍
                    if "data" in event:
                        yield {
                            "type": "text_chunk",
                            "data": event["data"],
                            "complete": event.get("complete", False)
                        }
                    
                    # 🎯 메시지가 추가될 때 완료된 tool_use 정보를 yield
                    if "message" in event:
                        message = event["message"]
                        
                        # assistant 메시지에서 완료된 tool_use 찾기
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
                        
                        # user 메시지에서 tool_result 처리
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
                    
                    # 최종 결과 - 스트리밍 완료 신호
                    if "result" in event:
                        yield {
                            "type": "streaming_complete",
                            "message": "텍스트 스트리밍 완료!"
                        }

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "status": "error"
            }


# AgentCore Runtime 엔트리포인트
architect = None

@app.entrypoint
async def portfolio_architect(payload):
    """AgentCore Runtime 엔트리포인트"""
    global architect
    if architect is None:
        # 런타임에서는 환경변수에서 설정값 로드
        config = {
            "client_id": os.getenv("MCP_CLIENT_ID", "ovm4qu7tbjbn5hp8hvfecidvb"),
            "client_secret": os.getenv("MCP_CLIENT_SECRET", "<YOUR_CLIENT_SECRET>"),
            "token_url": os.getenv("MCP_TOKEN_URL", "https://us-west-2pgtmzk6id.auth.us-west-2.amazoncognito.com/oauth2/token"),
            "gateway_url": os.getenv("MCP_GATEWAY_URL", "https://your-gateway-url/mcp"),
            "target_name": os.getenv("MCP_TARGET_NAME", "sample-gateway-target")
        }
        architect = PortfolioArchitect(**config)
    
    financial_analysis = payload.get("financial_analysis")
    async for chunk in architect.design_portfolio_async(financial_analysis):
        yield chunk

# 테스트용 함수
def test_portfolio_architect(config):
    """테스트 함수"""
    import asyncio
    
    async def run_test():
        # config는 필수
        architect = PortfolioArchitect(**config)
        
        # Lab 1의 예시 결과를 사용
        test_financial_analysis = {
            "risk_profile": "공격적",
            "risk_profile_reason": "나이가 35세로 젊고, 주식 투자 경험이 10년으로 상당히 많으며, 총 투자 가능 금액이 5000만원으로 상당히 높은 편입니다.",
            "required_annual_return_rate": 40.00,
            "return_rate_reason": "필요 연간 수익률은 (70000000 - 50000000) / 50000000 * 100 = 40.00%입니다."
        }
        
        print("=== Lab 2: Portfolio Architect Test (MCP Version) ===")
        print("📥 입력 데이터:")
        print(json.dumps(test_financial_analysis, ensure_ascii=False, indent=2))
        print("\n🤖 포트폴리오 설계 시작...")
        
        try:
            full_text = ""
            async for chunk in architect.design_portfolio_async(test_financial_analysis):
                if chunk["type"] == "text_chunk":
                    data = chunk["data"]
                    full_text += data
                    print(data, end="", flush=True)
                    
                elif chunk["type"] == "streaming_complete":
                    print(f"\n\n✅ {chunk['message']}")
                    
                elif chunk["type"] == "tool_use":
                    print(f"\n\n🛠️ Tool Use: {chunk['tool_name']}")
                    print(f"   Tool Use ID: {chunk['tool_use_id']}")
                    print(f"   Input: {chunk['tool_input']}")
                    print("-" * 40)
                    
                elif chunk["type"] == "tool_result":
                    print(f"\n📊 Tool Result:")
                    print(f"   Tool Use ID: {chunk['tool_use_id']}")
                    print(f"   Status: {chunk['status']}")
                    for content_item in chunk['content']:
                        if 'text' in content_item:
                            result_text = content_item['text']
                            print(f"   Result: {result_text}")
                    print("-" * 40)
                    
                elif chunk["type"] == "error":
                    print(f"\n❌ 오류 발생: {chunk['error']}")
                    
        except Exception as e:
            print(f"\n❌테스트 실행 중 오류: {str(e)}")
    
    # 비동기 함수 실행
    asyncio.run(run_test())

if __name__ == "__main__":
    # 설정값 정의 (deploy_gateway.py 실행 결과로 업데이트 필요)
    config = {
        "client_id": "ovm4qu7tbjbn5hp8hvfecidvb",  # deploy_gateway.py 결과에서 가져온 값
        "client_secret": "1mhgbekbhk27c4vfoghsr1dtph7l595ohpg816l04raekfbmmker",    # deploy_gateway.py 결과에서 가져온 값
        "token_url": "https://us-west-2pgtmzk6id.auth.us-west-2.amazoncognito.com/oauth2/token",
        "gateway_url": "https://sample-gateway-jdhc1sux2q.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",  # deploy_gateway.py 결과에서 가져온 값 + /mcp
        "target_name": "sample-gateway-target"
    }
    
    print("🔧 설정값을 사용합니다.")
    print("   deploy_gateway.py 실행 결과로 config 값들을 업데이트하세요.")
    
    # 테스트 실행
    test_portfolio_architect(config)
    
    # AgentCore 앱 실행
    app.run()