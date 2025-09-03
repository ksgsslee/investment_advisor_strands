"""
investment_advisor.py

LangGraph 기반 Investment Advisor
3개 에이전트를 순차 실행하며 AgentCore Memory에 중간 과정 저장
"""

import json
import os
import boto3
from typing import Dict, Any, TypedDict
from pathlib import Path
from datetime import datetime

# LangGraph
from langgraph.graph import StateGraph, END

# AgentCore
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient

app = BedrockAgentCoreApp()

# ================================
# 설정
# ================================

class Config:
    REGION = "us-west-2"
    MEMORY_NAME = "InvestmentAdvisor_LangGraph"

# ================================
# State 정의
# ================================

class InvestmentState(TypedDict):
    user_input: Dict[str, Any]
    session_id: str
    financial_analysis: str
    portfolio_recommendation: str
    risk_analysis: str

# ================================
# 에이전트 호출 클라이언트
# ================================

class AgentClient:
    def __init__(self):
        self.client = boto3.client('bedrock-agentcore', region_name=Config.REGION)
        self.memory_client = MemoryClient(region_name=Config.REGION)
        self.memory_id = None
        self.arns = self._load_agent_arns()
        self._init_memory()
    
    def _load_agent_arns(self):
        """Agent ARN 로드"""
        # 환경변수에서 시도
        financial_arn = os.getenv("FINANCIAL_ANALYST_ARN")
        portfolio_arn = os.getenv("PORTFOLIO_ARCHITECT_ARN") 
        risk_arn = os.getenv("RISK_MANAGER_ARN")
        
        if financial_arn and portfolio_arn and risk_arn:
            return {
                "financial": financial_arn,
                "portfolio": portfolio_arn,
                "risk": risk_arn
            }
        
        # 파일에서 로드
        base_path = Path(__file__).parent.parent
        return {
            "financial": json.load(open(base_path / "financial_analyst" / "deployment_info.json"))["agent_arn"],
            "portfolio": json.load(open(base_path / "portfolio_architect" / "deployment_info.json"))["agent_arn"],
            "risk": json.load(open(base_path / "risk_manager" / "deployment_info.json"))["agent_arn"]
        }
    
    def _init_memory(self):
        """AgentCore Memory 초기화"""
        try:
            memories = self.memory_client.list_memories()
            existing_memory = next((m for m in memories if m['id'].startswith(Config.MEMORY_NAME)), None)
            
            if existing_memory:
                self.memory_id = existing_memory['id']
                print(f"✅ 기존 메모리 사용: {self.memory_id}")
            else:
                memory = self.memory_client.create_memory_and_wait(
                    name=Config.MEMORY_NAME,
                    description="Investment Advisor Thinking Process",
                    strategies=[],
                    event_expiry_days=7,
                    max_wait=300,
                    poll_interval=10
                )
                self.memory_id = memory['id']
                print(f"✅ 새 메모리 생성: {self.memory_id}")
        except Exception as e:
            print(f"❌ 메모리 초기화 실패: {e}")
    
    def call_agent_with_memory(self, agent_type, payload_key, data, session_id):
        """에이전트 호출하며 중간 과정을 Memory에 저장"""
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.arns[agent_type],
            qualifier="DEFAULT",
            payload=json.dumps({payload_key: data})
        )
        
        final_result = None
        thinking_chunks = []  # text_chunk 임시 저장
        memory_events = []    # Memory에 저장할 이벤트들
        
        # 스트리밍 응답 처리
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    event_type = event_data.get("type")
                    print(event_data)
                    if event_type == "text_chunk":
                        # 텍스트 청크는 임시 저장
                        thinking_chunks.append(event_data.get("data", ""))
                    
                    elif event_type == "tool_use":
                        # 도구 사용 시 지금까지의 텍스트 청크를 Memory에 저장
                        if thinking_chunks:
                            memory_events.append({
                                "type": "thinking",
                                "content": "".join(thinking_chunks)
                            })
                            thinking_chunks = []
                        
                        # 도구 사용 정보 저장
                        tool_info = f"🔧 도구 사용: {event_data.get('tool_name', 'Unknown')}"
                        memory_events.append({
                            "type": "tool_use",
                            "content": tool_info
                        })
                    
                    elif event_type == "tool_result":
                        # 도구 결과 저장
                        tool_result = f"✅ 도구 실행 완료: {event_data.get('status', 'Unknown')}"
                        memory_events.append({
                            "type": "tool_result", 
                            "content": tool_result
                        })
                    
                    elif event_type == "streaming_complete":
                        # 완료 시 남은 텍스트 청크 저장
                        if thinking_chunks:
                            memory_events.append({
                                "type": "thinking",
                                "content": "".join(thinking_chunks)
                            })
                        
                        # 최종 결과 캐치
                        if agent_type == "financial":
                            final_result = event_data.get("result")
                        elif agent_type == "portfolio":
                            final_result = event_data.get("portfolio_result")
                        elif agent_type == "risk":
                            final_result = event_data.get("risk_result")
                        
                except json.JSONDecodeError:
                    continue
        
        # Memory에 모든 이벤트 저장
        if self.memory_id and memory_events:
            try:
                # 모든 이벤트를 하나의 문자열로 결합
                full_process = "\n".join([
                    f"[{event['type']}] {event['content']}" 
                    for event in memory_events
                ])
                
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=session_id,
                    session_id=f"{session_id}_{agent_type}",
                    messages=[(f"{agent_type}_process", "user"), (full_process, "assistant")]
                )
                print(f"✅ {agent_type} 전체 과정 Memory 저장 완료 ({len(memory_events)}개 이벤트)")
            except Exception as e:
                print(f"❌ Memory 저장 실패: {e}")
        
        return final_result

agent_client = AgentClient()

# ================================
# LangGraph 노드들
# ================================

def financial_node(state: InvestmentState):
    """재무 분석 노드"""
    print("🤖 재무 분석가 시작...")
    result = agent_client.call_agent_with_memory(
        "financial", "input_data", state["user_input"], state["session_id"]
    )
    state["financial_analysis"] = result
    print("✅ 재무 분석가 완료")
    return state

def portfolio_node(state: InvestmentState):
    """포트폴리오 노드"""
    print("🤖 포트폴리오 아키텍트 시작...")
    result = agent_client.call_agent_with_memory(
        "portfolio", "financial_analysis", state["financial_analysis"], state["session_id"]
    )
    state["portfolio_recommendation"] = result
    print("✅ 포트폴리오 아키텍트 완료")
    return state

def risk_node(state: InvestmentState):
    """리스크 노드"""
    print("🤖 리스크 매니저 시작...")
    result = agent_client.call_agent_with_memory(
        "risk", "portfolio_data", state["portfolio_recommendation"], state["session_id"]
    )
    state["risk_analysis"] = result
    print("✅ 리스크 매니저 완료")
    return state

# ================================
# LangGraph 구성
# ================================

def create_graph():
    workflow = StateGraph(InvestmentState)
    
    workflow.add_node("financial", financial_node)
    workflow.add_node("portfolio", portfolio_node)
    workflow.add_node("risk", risk_node)
    
    workflow.set_entry_point("financial")
    workflow.add_edge("financial", "portfolio")
    workflow.add_edge("portfolio", "risk")
    workflow.add_edge("risk", END)
    
    return workflow.compile()

# ================================
# 메인 클래스
# ================================

class InvestmentAdvisor:
    def __init__(self):
        self.graph = create_graph()
    
    async def run_consultation(self, user_input):
        """투자 상담 실행"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        initial_state = {
            "user_input": user_input,
            "session_id": session_id,
            "financial_analysis": "",
            "portfolio_recommendation": "",
            "risk_analysis": ""
        }
        
        config = {"configurable": {"thread_id": session_id}}
        
        # LangGraph astream_events로 실시간 진행 상황 전달
        async for event in self.graph.astream_events(initial_state, config=config, version="v2"):
            event_type = event.get("event")
            
            # 노드 시작
            if event_type == "on_chain_start":
                node_name = event.get("name", "")
                if node_name in ["financial", "portfolio", "risk"]:
                    yield {
                        "type": "node_start",
                        "agent_name": node_name,
                        "session_id": session_id
                    }
            
            # 노드 완료
            elif event_type == "on_chain_end":
                node_name = event.get("name", "")
                if node_name in ["financial", "portfolio", "risk"]:
                    yield {
                        "type": "node_complete",
                        "agent_name": node_name,
                        "session_id": session_id
                    }
        
        # 최종 상태 가져오기
        final_state = await self.graph.ainvoke(initial_state, config=config)
        
        # 최종 완료
        yield {
            "type": "final_complete",
            "session_id": session_id,
            "financial_analysis": final_state["financial_analysis"],
            "portfolio_recommendation": final_state["portfolio_recommendation"],
            "risk_analysis": final_state["risk_analysis"]
        }
    
    def get_thinking_process(self, session_id, agent_name):
        """Memory에서 중간 과정 조회"""
        if not agent_client.memory_id:
            return "메모리가 초기화되지 않았습니다."
        
        try:
            recent_turns = agent_client.memory_client.get_last_k_turns(
                memory_id=agent_client.memory_id,
                actor_id=session_id,
                session_id=f"{session_id}_{agent_name}",
                k=5,
                branch_name="main"
            )
            
            if recent_turns and len(recent_turns[0]) >= 2:
                return recent_turns[0][1]['content']['text']
            else:
                return f"{agent_name} 중간 과정을 찾을 수 없습니다."
                
        except Exception as e:
            return f"중간 과정 조회 실패: {str(e)}"

# ================================
# Runtime 엔트리포인트
# ================================

advisor = None

@app.entrypoint
async def investment_advisor_entrypoint(payload):
    global advisor
    if advisor is None:
        advisor = InvestmentAdvisor()
    
    user_input = payload.get("input_data")
    async for chunk in advisor.run_consultation(user_input):
        yield chunk

if __name__ == "__main__":
    app.run()