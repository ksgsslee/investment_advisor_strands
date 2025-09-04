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
from langgraph.config import get_stream_writer

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
        """환경변수 또는 JSON 파일에서 Agent ARN 로드"""
        # 1. 환경변수에서 시도
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
        
        # 2. JSON 파일에서 fallback
        try:
            current_dir = Path(__file__).parent
            base_dir = current_dir.parent
            
            # 각 에이전트의 deployment_info.json 파일 읽기
            arns = {}
            agent_dirs = {
                "financial": "financial_analyst",
                "portfolio": "portfolio_architect", 
                "risk": "risk_manager"
            }
            
            for agent_key, agent_dir in agent_dirs.items():
                info_file = base_dir / agent_dir / "deployment_info.json"
                if info_file.exists():
                    with open(info_file, 'r') as f:
                        deployment_info = json.load(f)
                        arns[agent_key] = deployment_info.get("agent_arn")
                else:
                    raise FileNotFoundError(f"{agent_dir}/deployment_info.json 파일이 없습니다.")
            
            if len(arns) == 3 and all(arns.values()):
                print("✅ JSON 파일에서 Agent ARN 로드")
                return arns
            else:
                raise ValueError("일부 Agent ARN을 찾을 수 없습니다.")
                
        except Exception as e:
            raise ValueError(
                f"Agent ARN 로드 실패: {str(e)}\n"
                "환경변수 또는 각 에이전트의 deployment_info.json 파일을 확인하세요."
            )
  
    def _load_memory_id(self):
        """환경변수 또는 JSON 파일에서 Memory ID 로드"""
        # 1. 환경변수에서 시도
        memory_id = os.getenv("INVESTMENT_MEMORY_ID")
        if memory_id:
            print("✅ 환경변수에서 Memory ID 로드")
            return memory_id
        
        # 2. JSON 파일에서 fallback
        try:
            current_dir = Path(__file__).parent
            memory_info_file = current_dir / "agentcore_memory" / "deployment_info.json"
            
            if memory_info_file.exists():
                with open(memory_info_file, 'r') as f:
                    memory_info = json.load(f)
                    memory_id = memory_info.get("memory_id")
                    if memory_id:
                        print("✅ JSON 파일에서 Memory ID 로드")
                        return memory_id
                    else:
                        raise ValueError("Memory ID가 JSON 파일에 없습니다.")
            else:
                raise FileNotFoundError("agentcore_memory/deployment_info.json 파일이 없습니다.")
                
        except Exception as e:
            raise ValueError(
                f"Memory ID 로드 실패: {str(e)}\n"
                "환경변수 INVESTMENT_MEMORY_ID 또는 agentcore_memory/deployment_info.json 파일을 확인하세요."
            )
    
    def call_agent_with_streaming(self, agent_type, data, writer):
        """에이전트 호출하며 실시간 스트리밍 + Memory 저장 (동기 버전)"""
        
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.arns[agent_type],
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": data})
        )
        
        final_result = None
        
        # 스트리밍 응답 처리
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    
                    # 각 에이전트의 스트리밍 이벤트를 그대로 전달
                    writer(event_data)

                    event_type = event_data.get("type")
                    if event_type == "streaming_complete":
                        final_result = event_data.get("result")
                
                except json.JSONDecodeError:
                    continue
        
        return final_result    

    def _save_events_batch(self, session_id, agent_type, events_list):
        """이벤트들을 한 번에 배치로 Memory에 저장"""
        if not self.memory_id or not events_list:
            return
        
        try:
            # 각 이벤트를 개별 메시지로 변환
            messages = []
            for event_data in events_list:
                # 에이전트 타입 추가
                event_data["agent_type"] = agent_type
                
                # JSON 형태로 변환
                event_json = json.dumps(event_data, ensure_ascii=False, indent=2)
                messages.append((event_json, "OTHER"))
            
            # 에이전트별 세션에 저장
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=session_id,
                session_id=session_id,
                messages=messages
            )
            print(f"💾 {agent_type} 배치 저장 완료 ({len(events_list)}개 이벤트)")
            
        except Exception as e:
            print(f"❌ Memory 배치 저장 실패 ({agent_type}): {e}")

agent_client = AgentClient()

# ================================
# LangGraph 노드들
# ================================

def financial_node(state: InvestmentState):
    """재무 분석 노드 - 커스텀 스트리밍 지원"""
    writer = get_stream_writer()
    
    # 노드 시작 이벤트 전송
    writer({
        "type": "node_start",
        "agent_name": "financial",
        "session_id": state["session_id"]
    })

    # 에이전트 호출하며 실시간 스트리밍
    final_result = agent_client.call_agent_with_streaming(
        "financial", state["user_input"], writer
    )
    
    # 노드 완료 이벤트 전송
    writer({
        "type": "node_complete",
        "agent_name": "financial",
        "session_id": state["session_id"],
        "result": final_result
    })
    
    state["financial_analysis"] = final_result
    return state

def portfolio_node(state: InvestmentState):
    """포트폴리오 노드 - 커스텀 스트리밍 지원"""
    writer = get_stream_writer()
    
    # 노드 시작 이벤트 전송
    writer({
        "type": "node_start",
        "agent_name": "portfolio",
        "session_id": state["session_id"]
    })
  
    # 에이전트 호출하며 실시간 스트리밍
    final_result = agent_client.call_agent_with_streaming(
        "portfolio", state["financial_analysis"], writer
    )
    
    # 노드 완료 이벤트 전송
    writer({
        "type": "node_complete",
        "agent_name": "portfolio",
        "session_id": state["session_id"],
        "result": final_result
    })
    
    state["portfolio_recommendation"] = final_result
    return state

def risk_node(state: InvestmentState):
    """리스크 노드 - 커스텀 스트리밍 지원"""
    writer = get_stream_writer()
    
    # 노드 시작 이벤트 전송
    writer({
        "type": "node_start",
        "agent_name": "risk",
        "session_id": state["session_id"]
    })

    # 에이전트 호출하며 실시간 스트리밍
    final_result = agent_client.call_agent_with_streaming(
        "risk", state["portfolio_recommendation"], writer
    )
    
    # 노드 완료 이벤트 전송
    writer({
        "type": "node_complete",
        "agent_name": "risk",
        "session_id": state["session_id"],
        "result": final_result
    })
    
    state["risk_analysis"] = final_result
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
        """투자 상담 실행 - 커스텀 스트리밍 지원"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        initial_state = {
            "user_input": user_input,
            "session_id": session_id,
            "financial_analysis": "",
            "portfolio_recommendation": "",
            "risk_analysis": ""
        }
        
        config = {"configurable": {"thread_id": session_id}}
        
        # 커스텀 스트리밍 모드로 실행 (동기 노드이므로 stream 사용)
        for chunk in self.graph.stream(
            initial_state, 
            config=config,
            stream_mode="custom"  # 커스텀 데이터만 받기
        ):
            # print(chunk)
            yield chunk


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