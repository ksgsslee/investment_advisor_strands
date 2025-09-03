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
        """에이전트 호출하며 중간 과정을 효율적으로 Memory에 저장"""
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.arns[agent_type],
            qualifier="DEFAULT",
            payload=json.dumps({payload_key: data})
        )
        
        final_result = None
        thinking_chunks = []  # text_chunk 임시 저장
        
        # 스트리밍 응답 처리
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    event_type = event_data.get("type")
                    
                    if event_type == "text_chunk":
                        # 텍스트 청크는 임시 저장만 (메모리에 저장하지 않음)
                        thinking_chunks.append(event_data.get("data", ""))
                    
                    elif event_type == "tool_use":
                        # tool_use 전에 쌓인 텍스트 청크들 저장
                        if thinking_chunks:
                            combined_text_event = {
                                "type": "text",
                                "data": "".join(thinking_chunks)
                            }
                            self._save_event_to_memory(session_id, agent_type, combined_text_event)
                            thinking_chunks = []  # 저장 후 초기화
                        
                        # 도구 사용 이벤트 저장
                        self._save_event_to_memory(session_id, agent_type, event_data)
                    
                    elif event_type == "tool_result":
                        # 도구 결과 이벤트는 즉시 저장
                        self._save_event_to_memory(session_id, agent_type, event_data)
                    
                    elif event_type == "streaming_complete":
                        # 스트리밍 완료 시점에 남은 텍스트 청크들 저장
                        if thinking_chunks:
                            combined_text_event = {
                                "type": "text",
                                "data": "".join(thinking_chunks)
                            }
                            self._save_event_to_memory(session_id, agent_type, combined_text_event)
                        
                        # streaming_complete 이벤트도 저장
                        self._save_event_to_memory(session_id, agent_type, event_data)
                        
                        # 최종 결과 캐치 (모든 에이전트 통일)
                        final_result = event_data.get("result")
                    
                    else:
                        # 기타 이벤트들은 즉시 저장
                        self._save_event_to_memory(session_id, agent_type, event_data)
                        
                except json.JSONDecodeError:
                    continue
        
        return final_result    

    def _save_event_to_memory(self, session_id, agent_type, event_data):
        """원본 이벤트 데이터를 JSON 형태로 Memory에 저장"""
        if not self.memory_id:
            return
        
        try:
            # 에이전트 타입 추가
            event_data["agent_type"] = agent_type
            
            # JSON 형태로 저장
            event_json = json.dumps(event_data, ensure_ascii=False, indent=2)
            
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=session_id,
                session_id=session_id,
                messages=[
                    (event_json, "OTHER")
                ]
            )
            print(f"💾 {agent_type} [{event_data.get('type')}] JSON 저장")
        except Exception as e:
            print(f"❌ Memory 저장 실패 ({agent_type}): {e}")

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

    def get_thinking_process(self, session_id, agent_name=None, format_type="text"):
        """Memory에서 중간 과정 조회 (JSON 데이터 지원)"""
        if not agent_client.memory_id:
            return "메모리가 초기화되지 않았습니다."
        
        try:
            # 해당 세션의 모든 대화 조회
            recent_turns = agent_client.memory_client.get_last_k_turns(
                memory_id=agent_client.memory_id,
                actor_id=session_id,
                session_id=session_id,
                k=100,  # 충분히 많은 턴 조회
                branch_name="main"
            )
            
            if not recent_turns:
                return "중간 과정을 찾을 수 없습니다."
            
            # 에이전트별 필터링 및 포맷팅
            filtered_events = []
            for turn in recent_turns:
                if len(turn) >= 2:
                    user_msg = turn[0]['content']['text']
                    assistant_msg = turn[1]['content']['text']
                    
                    # 특정 에이전트만 조회하는 경우
                    if agent_name and f"[{agent_name}]" in user_msg:
                        filtered_events.append(assistant_msg)
                    # 모든 에이전트 조회하는 경우
                    elif agent_name is None:
                        filtered_events.append(assistant_msg)
            
            if not filtered_events:
                return f"{agent_name or '전체'} 중간 과정을 찾을 수 없습니다."
            
            # 포맷 타입에 따른 반환
            if format_type == "json":
                # JSON 형태로 파싱해서 반환
                parsed_events = []
                for event_str in filtered_events:
                    try:
                        event_json = json.loads(event_str)
                        parsed_events.append(event_json)
                    except json.JSONDecodeError:
                        # JSON이 아닌 경우 텍스트로 처리
                        parsed_events.append({"type": "text", "content": event_str})
                return parsed_events
            else:
                # 텍스트 형태로 반환 (기존 방식)
                formatted_events = []
                for event_str in filtered_events:
                    try:
                        event_json = json.loads(event_str)
                        # JSON을 읽기 쉬운 텍스트로 변환
                        event_type = event_json.get("type", "unknown")
                        agent_type = event_json.get("agent_type", "")
                        
                        if event_type == "text":
                            # 합쳐진 텍스트 표시
                            data = event_json.get("data", "")[:500]  # 처음 500자만
                            formatted_events.append(f"[{agent_type}] 💭 사고과정: {data}...")
                        elif event_type == "tool_use":
                            tool_name = event_json.get("tool_name", "Unknown")
                            formatted_events.append(f"[{agent_type}] 🔧 도구 사용: {tool_name}")
                        elif event_type == "tool_result":
                            status = event_json.get("status", "Unknown")
                            formatted_events.append(f"[{agent_type}] ✅ 도구 완료: {status}")
                        elif event_type == "streaming_complete":
                            formatted_events.append(f"[{agent_type}] 🏁 스트리밍 완료")
                        else:
                            formatted_events.append(f"[{agent_type}] [{event_type}] {str(event_json)[:200]}...")
                    except json.JSONDecodeError:
                        # JSON이 아닌 경우 그대로 추가
                        formatted_events.append(event_str)
                return "\n".join(formatted_events)
                
        except Exception as e:
            return f"중간 과정 조회 실패: {str(e)}"
    
    def get_agent_events_by_type(self, session_id, agent_name, event_type):
        """특정 에이전트의 특정 이벤트 타입만 조회"""
        if not agent_client.memory_id:
            return []
        
        try:
            recent_turns = agent_client.memory_client.get_last_k_turns(
                memory_id=agent_client.memory_id,
                actor_id=f"{session_id}_{agent_name}",
                session_id=f"{session_id}_{agent_name}_{event_type}",
                k=5,
                branch_name="main"
            )
            
            events = []
            for turn in recent_turns:
                if len(turn) >= 2:
                    events.append(turn[1]['content']['text'])
            
            return events
            
        except Exception as e:
            return [f"조회 실패: {str(e)}"]

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