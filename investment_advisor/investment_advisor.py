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
        self.arns = self._load_agent_arns()
        self.memory_id = self._load_memory_id()
    
    def _load_agent_arns(self):
        """Agent ARN 로드 (환경변수 우선, 없으면 파일에서 로드)"""
        # 환경변수에서 시도
        financial_arn = os.getenv("FINANCIAL_ANALYST_ARN")
        portfolio_arn = os.getenv("PORTFOLIO_ARCHITECT_ARN") 
        risk_arn = os.getenv("RISK_MANAGER_ARN")
        
        if financial_arn and portfolio_arn and risk_arn:
            print("✅ 환경변수에서 Agent ARN 로드")
            return {
                "financial": financial_arn,
                "portfolio": portfolio_arn,
                "risk": risk_arn
            }
        
        # 파일에서 로드
        print("📁 파일에서 Agent ARN 로드")
        base_path = Path(__file__).parent.parent
        return {
            "financial": json.load(open(base_path / "financial_analyst" / "deployment_info.json"))["agent_arn"],
            "portfolio": json.load(open(base_path / "portfolio_architect" / "deployment_info.json"))["agent_arn"],
            "risk": json.load(open(base_path / "risk_manager" / "deployment_info.json"))["agent_arn"]
        }  
  
    def _load_memory_id(self):
        """Memory ID 로드 (환경변수 우선, 없으면 파일에서 로드)"""
        # 환경변수에서 시도
        memory_id = os.getenv("INVESTMENT_MEMORY_ID")
        if memory_id:
            print("✅ 환경변수에서 Memory ID 로드")
            return memory_id
        
        # 파일에서 로드
        print("📁 파일에서 Memory ID 로드")
        memory_info_file = Path(__file__).parent / "agentcore_memory" / "deployment_info.json"
        memory_info = json.load(open(memory_info_file))
        return memory_info["memory_id"]
    
    def call_agent_with_memory(self, agent_type, data, session_id):
        """에이전트 호출하며 중간 과정을 효율적으로 Memory에 저장"""
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.arns[agent_type],
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": data})
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
        """원본 이벤트 데이터를 에이전트별 세션에 저장"""
        if not self.memory_id:
            return
        
        try:
            # 에이전트 타입 추가
            event_data["agent_type"] = agent_type
            
            # JSON 형태로 저장
            event_json = json.dumps(event_data, ensure_ascii=False, indent=2)
            
            # 에이전트별 세션에 저장
            agent_session_id = f"{session_id}_{agent_type}"
            
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=session_id,  # 같은 actor
                session_id=agent_session_id,  # 에이전트별 세션
                messages=[
                    (event_json, "OTHER")
                ]
            )
            print(f"💾 {agent_type} [{event_data.get('type')}] 세션 저장")
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
        "financial", state["user_input"], state["session_id"]
    )
    state["financial_analysis"] = result
    print("✅ 재무 분석가 완료")
    return state

def portfolio_node(state: InvestmentState):
    """포트폴리오 노드"""
    print("🤖 포트폴리오 아키텍트 시작...")
    result = agent_client.call_agent_with_memory(
        "portfolio", state["financial_analysis"], state["session_id"]
    )
    state["portfolio_recommendation"] = result
    print("✅ 포트폴리오 아키텍트 완료")
    return state

def risk_node(state: InvestmentState):
    """리스크 노드"""
    print("🤖 리스크 매니저 시작...")
    result = agent_client.call_agent_with_memory(
        "risk", state["portfolio_recommendation"], state["session_id"]
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

    def get_agent_events(self, session_id, agent_name):
        """특정 에이전트의 모든 이벤트 조회"""
        if not agent_client.memory_id:
            return []
        
        try:
            agent_session_id = f"{session_id}_{agent_name}"
            events = agent_client.memory_client.list_events(
                memory_id=agent_client.memory_id,
                actor_id=session_id,
                session_id=agent_session_id,
                max_results=100
            )
            return events
            
        except Exception as e:
            print(f"이벤트 조회 실패: {str(e)}")
            return []

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