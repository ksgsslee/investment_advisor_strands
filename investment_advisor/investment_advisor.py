"""
investment_advisor.py
Multi-Agent Investment Advisor with AgentCore Memory

AWS Bedrock AgentCore Memory를 활용한 투자 자문 시스템
3개의 전문 에이전트가 협업하여 종합적인 투자 분석을 제공합니다.

주요 기능:
- Multi-Agent 패턴: 3개 전문 에이전트 순차 호출
- AgentCore Memory: 상담 히스토리 자동 저장 및 관리
- Agents as Tools: 각 에이전트를 도구로 활용
- 실시간 스트리밍: 분석 과정 실시간 시각화
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import boto3

# ================================
# 전역 설정
# ================================

app = BedrockAgentCoreApp()

class Config:
    """Investment Advisor 설정 상수"""
    MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    TEMPERATURE = 0.2
    MAX_TOKENS = 4000
    REGION = "us-west-2"

# ================================
# 유틸리티 함수들
# ================================

def extract_json_from_streaming(response_stream):
    """
    스트리밍 응답에서 JSON 결과 추출
    
    Args:
        response_stream: AgentCore 스트리밍 응답
        
    Returns:
        dict: 추출된 결과 데이터
    """
    try:
        for line in response_stream.iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    if event_data.get("type") == "streaming_complete":
                        return event_data
                except json.JSONDecodeError:
                    continue
        return None
    except Exception as e:
        print(f"스트리밍 처리 오류: {e}")
        return None


def extract_json_from_text(text):
    """
    텍스트에서 JSON 추출
    
    Args:
        text (str): JSON이 포함된 텍스트
        
    Returns:
        dict: 파싱된 JSON 데이터 또는 None
    """
    if not text:
        return None
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            return json.loads(text[start:end])
    except:
        pass
    return None

# ================================
# AgentCore Memory Hook
# ================================

class InvestmentMemoryHook(HookProvider):
    """투자 상담 메모리 관리 Hook"""
    
    def __init__(self, memory_client: MemoryClient, memory_id: str, actor_id: str, session_id: str):
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.actor_id = actor_id
        self.session_id = session_id

    def on_agent_initialized(self, event: AgentInitializedEvent):
        """에이전트 초기화 시 메모리 설정"""
        try:
            # 현재 세션의 기존 대화가 있는지 확인
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                k=3,
                branch_name="main"
            )
            
            if recent_turns:
                # 현재 세션에 이미 대화가 있다면 컨텍스트 추가
                context_messages = []
                for turn in recent_turns:
                    for message in turn:
                        role = message['role'].lower()
                        content = message['content']['text']
                        context_messages.append(f"{role.title()}: {content}")
                
                context = "\n".join(context_messages)
                event.agent.system_prompt += f"\n\n현재 대화 이력:\n{context}\n\n위 내용을 참고하여 대화를 이어가세요."
                print(f"✅ {len(recent_turns)}개 대화 이력 로드")
            else:
                print("✅ 새로운 상담 세션 시작")
            
        except Exception as e:
            print(f"⚠️ 메모리 로드 실패 (정상 - 새 세션): {e}")

    def on_message_added(self, event: MessageAddedEvent):
        """메시지 추가 시 메모리에 저장"""
        try:
            messages = event.agent.messages
            if messages:
                last_message = messages[-1]
                role = last_message["role"]
                
                # content 각각을 별도로 저장
                for content in last_message["content"]:
                    text_to_save = None
                    
                    if "text" in content:
                        text_to_save = content["text"]
                    elif "toolUse" in content:
                        tool_name = content["toolUse"].get("name", "unknown")
                        text_to_save = f"Tool Use: {tool_name}"
                    elif "toolResult" in content:
                        tool_result = content["toolResult"]
                        result_content = tool_result.get("content", [])
                        if result_content and "text" in result_content[0]:
                            text_to_save = f"Tool Result: {result_content[0]['text']}"
                    
                    if text_to_save:
                        self.memory_client.create_event(
                            memory_id=self.memory_id,
                            actor_id=self.actor_id,
                            session_id=self.session_id,
                            messages=[(text_to_save, role)]
                        )
                    
        except Exception as e:
            print(f"⚠️ 메모리 저장 실패: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)

# ================================
# 전문 에이전트 도구들 (Agents as Tools)
# ================================

# 전역 변수 (지연 초기화)
agentcore_client = None
agent_arns = {}

def initialize_agent_clients():
    """에이전트 클라이언트 초기화 (환경변수 우선, 파일 백업)"""
    global agentcore_client, agent_arns
    
    if agentcore_client is None:
        agentcore_client = boto3.client('bedrock-agentcore', region_name=Config.REGION)
        
        # 환경변수에서 Agent ARN 로드 (Runtime 환경)
        financial_arn = os.getenv("FINANCIAL_ANALYST_ARN")
        portfolio_arn = os.getenv("PORTFOLIO_ARCHITECT_ARN") 
        risk_arn = os.getenv("RISK_MANAGER_ARN")
        
        if financial_arn and portfolio_arn and risk_arn:
            # Runtime 환경: 환경변수 사용
            agent_arns = {
                "financial_analyst": financial_arn,
                "portfolio_architect": portfolio_arn,
                "risk_manager": risk_arn
            }
            print("✅ 환경변수에서 Agent ARN 로드 완료")
        else:
            # 로컬 환경: 파일에서 로드
            try:
                base_path = Path(__file__).parent.parent
                
                with open(base_path / "financial_analyst" / "deployment_info.json") as f:
                    agent_arns["financial_analyst"] = json.load(f)["agent_arn"]
                
                with open(base_path / "portfolio_architect" / "deployment_info.json") as f:
                    agent_arns["portfolio_architect"] = json.load(f)["agent_arn"]
                
                with open(base_path / "risk_manager" / "deployment_info.json") as f:
                    agent_arns["risk_manager"] = json.load(f)["agent_arn"]
                
                print("✅ 파일에서 Agent ARN 로드 완료")
            except Exception as e:
                raise RuntimeError(f"Agent ARN 로드 실패: {e}")

@tool
def financial_analyst_tool(user_input_json: str) -> str:
    """재무 분석 전문가 - 위험 성향과 목표 수익률 계산"""
    try:
        initialize_agent_clients()
        user_input = json.loads(user_input_json)
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arns["financial_analyst"],
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": user_input})
        )
        
        streaming_result = extract_json_from_streaming(response["response"])
        
        if streaming_result:
            return json.dumps(streaming_result, ensure_ascii=False)
        else:
            return json.dumps({"error": "재무 분석 결과를 가져올 수 없습니다"}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@tool
def portfolio_architect_tool(financial_analysis_json: str) -> str:
    """포트폴리오 설계 전문가 - 맞춤형 투자 포트폴리오 설계"""
    try:
        initialize_agent_clients()
        financial_analysis = json.loads(financial_analysis_json)
        
        # analysis_data만 추출해서 전달
        if "analysis_data" in financial_analysis:
            portfolio_input = financial_analysis["analysis_data"]
        else:
            portfolio_input = financial_analysis
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arns["portfolio_architect"],
            qualifier="DEFAULT",
            payload=json.dumps({"financial_analysis": portfolio_input})
        )
        
        streaming_result = extract_json_from_streaming(response["response"])
        
        if streaming_result:
            return json.dumps(streaming_result, ensure_ascii=False)
        else:
            return json.dumps({"error": "포트폴리오 설계 실패"}, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@tool
def risk_manager_tool(portfolio_data_json: str) -> str:
    """리스크 관리 전문가 - 시나리오별 리스크 분석 및 조정 전략"""
    try:
        initialize_agent_clients()
        portfolio_data = json.loads(portfolio_data_json)
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arns["risk_manager"],
            qualifier="DEFAULT",
            payload=json.dumps({"portfolio_data": portfolio_data})
        )
        
        streaming_result = extract_json_from_streaming(response["response"])
        
        if streaming_result:
            return json.dumps(streaming_result, ensure_ascii=False)
        else:
            return json.dumps({"error": "리스크 분석 실패"}, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

# ================================
# 메인 투자 자문 클래스
# ================================

class InvestmentAdvisor:
    """AgentCore Memory 기반 Multi-Agent 투자 자문 시스템"""
    
    def __init__(self, memory_id=None, user_id=None):
        """
        투자 자문 시스템 초기화
        
        Args:
            memory_id (str, optional): 기존 메모리 ID. None이면 새로 생성
            user_id (str, optional): 사용자 ID. None이면 자동 생성
        """
        # 메모리 클라이언트 초기화
        self.memory_client = MemoryClient(region_name=Config.REGION)
        
        # 메모리 설정
        self.memory_id = memory_id or self._create_memory()
        self.user_id = user_id or f"user-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.session_id = f"session-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 메모리 Hook 생성
        self.memory_hook = InvestmentMemoryHook(
            memory_client=self.memory_client,
            memory_id=self.memory_id,
            actor_id=self.user_id,
            session_id=self.session_id
        )
        
        # 투자 자문 에이전트 생성
        self.advisor_agent = Agent(
            name="investment_advisor",
            model=BedrockModel(
                model_id=Config.MODEL_ID,
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS
            ),
            tools=[financial_analyst_tool, portfolio_architect_tool, risk_manager_tool],
            hooks=[self.memory_hook],
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        """
        투자 자문 에이전트용 시스템 프롬프트 생성
        
        Returns:
            str: 투자 자문사 역할과 작업 지침이 포함된 프롬프트
        """
        return """당신은 친근하고 전문적인 투자 상담사입니다.

투자 상담을 3단계로 대화형으로 진행하세요:

**1단계: 재무 분석 🔍**
- "안녕하세요! 투자 상담을 시작하겠습니다. 먼저 재무 상황을 분석해보겠습니다."
- financial_analyst_tool 호출
- 결과를 간단하게 설명
- "이 분석 결과가 맞는지 확인해주세요. 다음 단계로 진행할까요?"

**2단계: 포트폴리오 설계 📊**  
- "이제 맞춤형 포트폴리오를 설계해보겠습니다"
- portfolio_architect_tool 호출 (1단계 결과 사용)
- 결과를 간단하게 설명
- "이 포트폴리오 구성이 어떠신가요? 리스크 분석으로 넘어갈까요?"

**3단계: 리스크 분석 ⚠️**
- "마지막으로 리스크를 분석해보겠습니다"  
- risk_manager_tool 호출 (2단계 결과 사용)
- 결과를 간단하게 설명
- "이 리스크 수준이 괜찮으신가요?"

**최종 정리**
- 3단계 결과를 종합해서 실행 가능한 투자 가이드 제공
- "추가 질문이나 조정 요청이 있으시면 언제든 말씀하세요!"

각 단계마다 사용자와 소통하며 친근하게 진행하세요."""
    
    def _create_memory(self):
        """새로운 메모리 생성"""
        try:
            memory_name = f"InvestmentAdvisor_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            memory = self.memory_client.create_memory_and_wait(
                name=memory_name,
                description="Investment Advisor Consultation History",
                strategies=[],
                event_expiry_days=30,
                max_wait=300,
                poll_interval=10
            )
            print(f"✅ 새로운 메모리 생성: {memory['id']}")
            return memory['id']
        except Exception as e:
            print(f"⚠️ 메모리 생성 실패: {e}")
            return None

    async def run_consultation_async(self, user_input):
        """
        실시간 스트리밍 투자 상담 수행 (Multi-Agent 패턴)
        
        3개의 전문 에이전트가 순차적으로 협업하여 종합적인 투자 분석을 제공합니다.
        분석 과정과 결과를 스트리밍 이벤트로 실시간 전송합니다.
        
        Args:
            user_input (dict): 고객 투자 정보
                - total_investable_amount: 총 투자 가능 금액
                - age: 나이
                - stock_investment_experience_years: 주식 투자 경험 년수
                - target_amount: 1년 후 목표 금액
            
        Yields:
            dict: 스트리밍 이벤트
                - type: 이벤트 타입 (data, message, result, error)
                - data: AI 대화 텍스트 (실시간)
                - message: 도구 사용 및 결과 메시지
                - result: 최종 상담 결과
                - session_id: 세션 ID
                - memory_id: 메모리 ID
        """
        try:
            print(f"🚀 투자 상담 시작 (세션: {self.session_id})")
            
            # 사용자 입력을 JSON 문자열로 변환
            input_str = json.dumps(user_input, ensure_ascii=False)
            
            # 에이전트 스트리밍 실행
            async for event in self.advisor_agent.stream_async(input_str):
                yield {
                    "session_id": self.session_id,
                    "memory_id": self.memory_id,
                    **event
                }
            
            print("🎉 투자 상담 완료!")
            
        except Exception as e:
            print(f"❌ 상담 실패: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "session_id": self.session_id
            }

# ================================
# AgentCore Runtime 엔트리포인트
# ================================

# 전역 인스턴스 (지연 초기화)
advisor = None

@app.entrypoint
async def investment_advisor_entrypoint(payload):
    """
    AgentCore Runtime 엔트리포인트
    
    AWS AgentCore Runtime 환경에서 호출되는 메인 함수입니다.
    환경변수에서 다른 에이전트 ARN을 로드하여 Multi-Agent 상담을 수행합니다.
    
    Args:
        payload (dict): 요청 페이로드
            - input_data: 고객 투자 정보
            - user_id: 사용자 ID (선택적)
            - memory_id: 메모리 ID (선택적)
    
    Yields:
        dict: 스트리밍 응답 이벤트들
    
    Environment Variables:
        - FINANCIAL_ANALYST_ARN: Financial Analyst Agent ARN
        - PORTFOLIO_ARCHITECT_ARN: Portfolio Architect Agent ARN
        - RISK_MANAGER_ARN: Risk Manager Agent ARN
        - AWS_REGION: AWS 리전 (기본값: us-west-2)
    
    Note:
        - 지연 초기화로 첫 호출 시에만 InvestmentAdvisor 인스턴스 생성
        - 실시간 스트리밍으로 상담 과정 전송
        - Multi-Agent 패턴으로 3개 에이전트 순차 협업
        - AgentCore Memory에 상담 히스토리 자동 저장
    """
    global advisor
    
    # Runtime 환경에서 지연 초기화
    if advisor is None:
        user_id = payload.get("user_id")
        memory_id = payload.get("memory_id")
        advisor = InvestmentAdvisor(memory_id=memory_id, user_id=user_id)

    # 고객 정보 추출 및 투자 상담 실행
    user_input = payload.get("input_data")
    async for chunk in advisor.run_consultation_async(user_input):
        yield chunk

# ================================
# 직접 실행
# ================================

if __name__ == "__main__":
    app.run()