"""
Lab 2: Gateway 기반 Portfolio Architect Agent
Tool Use Pattern + AgentCore Gateway + Identity 구현
"""
import json
import asyncio
from typing import Dict, Any, List
from strands import Agent
from strands.models.bedrock import BedrockModel
import boto3
import os

class GatewayMCPClient:
    """AgentCore Gateway MCP 클라이언트"""
    
    def __init__(self, gateway_id: str, region: str = "us-west-2"):
        self.gateway_id = gateway_id
        self.region = region
        self.agentcore_client = boto3.client('bedrock-agentcore', region_name=region)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Gateway에서 사용 가능한 도구 목록 조회"""
        try:
            response = self.agentcore_client.list_tools(gatewayId=self.gateway_id)
            return response.get('tools', [])
        except Exception as e:
            print(f"도구 목록 조회 실패: {str(e)}")
            return []
    
    async def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Gateway 도구 호출"""
        try:
            response = self.agentcore_client.invoke_tool(
                gatewayId=self.gateway_id,
                toolName=tool_name,
                input=parameters
            )
            return response
        except Exception as e:
            print(f"도구 호출 실패 ({tool_name}): {str(e)}")
            return {"error": str(e)}

class GatewayPortfolioArchitect:
    """Gateway 기반 포트폴리오 설계사"""
    
    def __init__(self, gateway_id: str = None):
        # Gateway 설정 로드
        self.gateway_config = self._load_gateway_config()
        self.gateway_id = gateway_id or self.gateway_config.get('gateway_id')
        
        if not self.gateway_id:
            raise ValueError("Gateway ID가 필요합니다. gateway_config.json을 확인하거나 gateway_id를 직접 제공하세요.")
        
        # Gateway MCP 클라이언트
        self.gateway_client = GatewayMCPClient(self.gateway_id)
        
        # Strands Agent 초기화
        self.agent = Agent(
            name="gateway_portfolio_architect",
            model=BedrockModel(
                model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                temperature=0.3,
                max_tokens=3000
            ),
            system_prompt=self._get_system_prompt(),
            tools=[]  # 동적으로 Gateway에서 로드
        )
        
        # 초기화 플래그
        self._tools_initialized = False
    
    def _load_gateway_config(self) -> Dict[str, Any]:
        """Gateway 설정 파일 로드"""
        config_file = "gateway_config.json"
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                return json.load(f)
        return {}
    
    def _get_system_prompt(self) -> str:
        return """당신은 전문 포트폴리오 설계사입니다. AgentCore Gateway를 통해 다양한 금융 데이터 소스에 접근할 수 있습니다.

사용 가능한 데이터 소스:
1. **Yahoo Finance Lambda**: ETF 가격 데이터, 뉴스, 기본 정보
2. **FRED Economic API**: 연방준비제도 경제 지표 (금리, 인플레이션, 실업률 등)

작업 순서:
1. **경제 상황 분석**: FRED API로 현재 경제 지표 조회
   - 연방기준금리 (FEDFUNDS)
   - 인플레이션 (CPIAUCSL) 
   - 실업률 (UNRATE)
   - 10년 국채수익률 (DGS10)

2. **ETF 선택**: 경제 상황에 적합한 ETF 3개 선택
   - 금리 상승기: 금융주(XLF), 단기채(SHY), 기술주(QQQ) 축소
   - 인플레이션 상승: 원자재(DBC), 금(GLD), 리츠(VNQ)
   - 경기침체 우려: 장기채(TLT), 방어주(SPY), 금(GLD)
   - 정상 성장: 균형 포트폴리오 (SPY, QQQ, AGG)

3. **데이터 수집**: 선택한 ETF들의 상세 정보 수집
   - 가격 데이터 및 변동성
   - 최신 뉴스 및 시장 감정
   - 기본 정보 (비용, 자산규모 등)

4. **포트폴리오 구성**: 수집한 데이터를 바탕으로 최적 배분 결정

응답 형식:
{
  "economic_analysis": {
    "fed_rate": "현재 금리",
    "inflation": "인플레이션율", 
    "unemployment": "실업률",
    "market_regime": "시장 상황 판단"
  },
  "selected_etfs": ["ETF1", "ETF2", "ETF3"],
  "etf_analysis": {
    "ETF1": {"price": 가격, "volatility": 변동성, "news_sentiment": "뉴스 요약"},
    "ETF2": {...},
    "ETF3": {...}
  },
  "portfolio_allocation": {
    "ETF1": 비율,
    "ETF2": 비율, 
    "ETF3": 비율
  },
  "strategy": "투자 전략 설명",
  "reason": "포트폴리오 구성 근거 (경제 지표와 ETF 데이터 기반)"
}

중요사항:
- 반드시 경제 지표를 먼저 조회하여 시장 상황을 파악하세요
- 각 ETF의 실제 데이터를 조회하여 근거 있는 배분을 결정하세요
- 뉴스 정보를 활용하여 시장 감정을 반영하세요
- 총 배분 비율은 반드시 100%가 되어야 합니다"""
    
    async def initialize_gateway_tools(self):
        """Gateway에서 도구들을 동적으로 로드"""
        if self._tools_initialized:
            return
        
        print("🔍 Gateway에서 사용 가능한 도구 조회 중...")
        
        available_tools = await self.gateway_client.list_tools()
        
        if not available_tools:
            print("⚠️ Gateway에서 도구를 찾을 수 없습니다.")
            return
        
        print(f"✅ {len(available_tools)}개 도구 발견:")
        
        for tool_info in available_tools:
            tool_name = tool_info.get('name', 'unknown')
            tool_description = tool_info.get('description', '')
            
            print(f"  - {tool_name}: {tool_description}")
            
            # Gateway 도구를 Strands Agent 도구로 래핑
            wrapped_tool = self._create_gateway_tool_wrapper(tool_info)
            self.agent.add_tool(wrapped_tool)
        
        self._tools_initialized = True
        print("✅ 모든 도구가 Agent에 등록되었습니다.")
    
    def _create_gateway_tool_wrapper(self, tool_info: Dict[str, Any]):
        """Gateway 도구를 Strands Agent 도구로 래핑"""
        tool_name = tool_info.get('name')
        tool_description = tool_info.get('description', '')
        
        async def gateway_tool_func(**kwargs):
            """Gateway 도구 호출 함수"""
            print(f"🔧 도구 호출: {tool_name} with {kwargs}")
            
            result = await self.gateway_client.invoke_tool(tool_name, kwargs)
            
            if 'error' in result:
                return f"도구 호출 실패: {result['error']}"
            
            # 결과를 JSON 문자열로 반환
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        # 함수 메타데이터 설정
        gateway_tool_func.__name__ = tool_name
        gateway_tool_func.__doc__ = tool_description
        
        # Strands tool 데코레이터 적용
        from strands.tools import tool
        return tool(gateway_tool_func)
    
    async def design_portfolio(self, financial_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """포트폴리오 설계 실행"""
        try:
            # Gateway 도구 초기화
            await self.initialize_gateway_tools()
            
            if not self._tools_initialized:
                return {
                    "status": "error",
                    "error": "Gateway 도구 초기화 실패"
                }
            
            # 재무 분석을 바탕으로 포트폴리오 설계 요청
            prompt = f"""
            사용자 재무 분석 결과:
            {json.dumps(financial_analysis, ensure_ascii=False, indent=2)}
            
            위 정보를 바탕으로 다음 단계를 수행하여 최적의 포트폴리오를 설계해주세요:
            
            1. 먼저 FRED API로 현재 경제 지표들을 조회하세요
            2. 경제 상황을 분석하여 적합한 ETF 3개를 선택하세요
            3. 선택한 ETF들의 가격 데이터와 뉴스를 수집하세요
            4. 수집한 데이터를 바탕으로 최종 포트폴리오 배분을 결정하세요
            
            모든 단계에서 실제 데이터를 조회하고 근거를 제시해주세요.
            """
            
            print("🤖 포트폴리오 설계 시작...")
            print("📊 경제 지표 조회 → ETF 선택 → 데이터 수집 → 포트폴리오 구성")
            
            # Agent 실행
            result = await self.agent.run_async(prompt)
            
            return {
                "status": "success",
                "portfolio": self._parse_agent_result(result),
                "raw_response": str(result),
                "gateway_id": self.gateway_id
            }
            
        except Exception as e:
            print(f"❌ 포트폴리오 설계 실패: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "gateway_id": self.gateway_id
            }
    
    def _parse_agent_result(self, result: Any) -> Dict[str, Any]:
        """Agent 결과 파싱"""
        try:
            result_str = str(result)
            
            # JSON 부분 추출 시도
            start_idx = result_str.find('{')
            end_idx = result_str.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result_str[start_idx:end_idx]
                return json.loads(json_str)
            
            # JSON 파싱 실패 시 기본 구조 반환
            return {
                "portfolio_allocation": {"SPY": 60, "AGG": 30, "GLD": 10},
                "strategy": "기본 균형 포트폴리오",
                "reason": "Agent 결과 파싱 실패로 기본 포트폴리오 제공"
            }
            
        except Exception as e:
            print(f"결과 파싱 실패: {str(e)}")
            return {
                "portfolio_allocation": {"SPY": 60, "AGG": 30, "GLD": 10},
                "strategy": "기본 균형 포트폴리오", 
                "reason": f"결과 파싱 오류: {str(e)}"
            }

# 테스트 함수
async def test_gateway_portfolio_architect():
    """Gateway 포트폴리오 설계사 테스트"""
    print("🧪 Gateway Portfolio Architect 테스트 시작")
    
    # 테스트 재무 분석 데이터
    test_financial_analysis = {
        "age": 35,
        "risk_tolerance": "aggressive",
        "investment_amount": 50000000,
        "target_return": 40.0,
        "risk_profile": "공격적",
        "risk_profile_reason": "나이가 젊고 투자 경험이 많음",
        "required_annual_return_rate": 40.0,
        "return_rate_reason": "목표 달성을 위한 높은 수익률 필요"
    }
    
    try:
        # Gateway 설정 확인
        if not os.path.exists("gateway_config.json"):
            print("❌ gateway_config.json 파일이 없습니다.")
            print("먼저 gateway_deploy.py를 실행하여 Gateway를 배포하세요.")
            return
        
        architect = GatewayPortfolioArchitect()
        
        print("📊 입력 데이터:")
        print(json.dumps(test_financial_analysis, ensure_ascii=False, indent=2))
        
        print("\n🚀 포트폴리오 설계 실행...")
        result = await architect.design_portfolio(test_financial_analysis)
        
        print("\n✅ 결과:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result['status'] == 'success':
            print("\n🎉 Gateway 기반 포트폴리오 설계 성공!")
        else:
            print(f"\n❌ 설계 실패: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")

def main():
    """메인 함수"""
    print("🤖 Lab 2: Gateway 기반 Portfolio Architect")
    
    # 비동기 테스트 실행
    asyncio.run(test_gateway_portfolio_architect())

if __name__ == "__main__":
    main()