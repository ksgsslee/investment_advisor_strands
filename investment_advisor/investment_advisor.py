"""
investment_advisor.py
Multi-Agent Investment Advisor with AgentCore Memory

AWS Bedrock AgentCore Memory를 활용한 투자 자문 시스템
3개의 전문 에이전트가 협업하여 종합적인 투자 분석을 제공합니다.
"""

import json
import boto3
from datetime import datetime
from pathlib import Path
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# ================================
# 설정
# ================================

app = BedrockAgentCoreApp()
REGION = "us-west-2"

# 전역 변수 (지연 초기화)
agentcore_client = None
memory_client = None
agent_arns = {}

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
        """에이전트 초기화 시 메모리 설정 (간단 버전)"""
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
            # 새로운 세션이므로 실패는 정상적임

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
# 유틸리티 함수
# ================================

def initialize_system():
    """시스템 초기화"""
    global agentcore_client, memory_client, agent_arns
    
    if agentcore_client is None:
        agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)
        memory_client = MemoryClient(region_name=REGION)
        
        # 에이전트 ARN 로드
        base_path = Path(__file__).parent.parent
        
        with open(base_path / "financial_analyst" / "deployment_info.json") as f:
            agent_arns["financial_analyst"] = json.load(f)["agent_arn"]
        
        with open(base_path / "portfolio_architect" / "deployment_info.json") as f:
            agent_arns["portfolio_architect"] = json.load(f)["agent_arn"]
        
        with open(base_path / "risk_manager" / "deployment_info.json") as f:
            agent_arns["risk_manager"] = json.load(f)["agent_arn"]
        
        print("✅ 시스템 초기화 완료")

def extract_json_from_streaming(response_stream):
    """스트리밍 응답에서 JSON 결과 추출 (단순화)"""
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
    """텍스트에서 JSON 추출"""
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
# 전문 에이전트 도구들
# ================================

@tool
def financial_analyst_tool(user_input_json: str) -> str:
    """재무 분석 전문가 - 위험 성향과 목표 수익률 계산"""
    try:
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
        initialize_system()
        
        # 메모리 설정
        self.memory_id = memory_id or self._create_memory()
        self.user_id = user_id or f"user-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.session_id = f"session-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 메모리 Hook 생성
        self.memory_hook = InvestmentMemoryHook(
            memory_client=memory_client,
            memory_id=self.memory_id,
            actor_id=self.user_id,
            session_id=self.session_id
        )
        
        # 투자 자문 에이전트 생성
        self.advisor_agent = Agent(
            name="investment_advisor",
            model=BedrockModel(
                model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                temperature=0.2,
                max_tokens=4000
            ),
            tools=[financial_analyst_tool, portfolio_architect_tool, risk_manager_tool],
            hooks=[self.memory_hook],
            system_prompt="""당신은 종합 투자 자문 전문가입니다.

사용자의 투자 상담 요청을 받으면 다음 순서로 진행하세요:

1. financial_analyst_tool 호출 - 재무 분석 및 위험 성향 평가
2. portfolio_architect_tool 호출 - 포트폴리오 설계 (1단계 결과 사용)
3. risk_manager_tool 호출 - 리스크 분석 (2단계 결과 사용)
4. 모든 결과를 종합하여 실행 가능한 투자 가이드 제공

각 단계의 결과를 명확히 설명하고, 최종적으로 고객이 바로 실행할 수 있는 구체적인 투자 계획을 제시하세요."""
        )
    
    def _create_memory(self):
        """새로운 메모리 생성"""
        try:
            memory_name = f"InvestmentAdvisor_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            memory = memory_client.create_memory_and_wait(
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
        """투자 상담 실행 (스트리밍)"""
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

@app.entrypoint
async def investment_advisor_entrypoint(payload):
    """AgentCore Runtime 엔트리포인트"""
    try:
        user_input = payload.get("input_data")
        user_id = payload.get("user_id")
        memory_id = payload.get("memory_id")
        
        advisor = InvestmentAdvisor(memory_id=memory_id, user_id=user_id)
        
        async for event in advisor.run_consultation_async(user_input):
            yield event
            
    except Exception as e:
        yield {
            "type": "error",
            "error": str(e)
        }

# ================================
# 직접 실행
# ================================

if __name__ == "__main__":
    app.run()