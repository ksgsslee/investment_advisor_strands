#!/usr/bin/env python3
"""
test_investment_advisor.py

LangGraph 기반 Investment Advisor 테스트
"""

import asyncio
import json
import os
from pathlib import Path
from investment_advisor import InvestmentAdvisor
from bedrock_agentcore.memory import MemoryClient

def get_thinking_process(session_id, agent_name):
    """특정 에이전트의 중간 과정 조회 (테스트용)"""
    try:
        # Memory ID 로드
        memory_info_file = Path(__file__).parent / "agentcore_memory" / "deployment_info.json"
        memory_info = json.load(open(memory_info_file))
        memory_id = memory_info["memory_id"]
        
        # Memory Client로 이벤트 조회
        memory_client = MemoryClient(region_name="us-west-2")
        agent_session_id = f"{session_id}_{agent_name}"
        events = memory_client.get_last_k_turns(
            memory_id=memory_id,
            actor_id=session_id,
            session_id=agent_session_id,
            k=1  # 마지막 턴만 (모든 이벤트가 포함됨)
        )
        
        return events
        
    except Exception as e:
        print(f"중간 과정 조회 실패: {str(e)}")
        return []

async def test_investment_advisor():
    """Investment Advisor 테스트"""
    print("🧪 LangGraph Investment Advisor 테스트")
    print("=" * 60)
    
    # 테스트 데이터
    test_input = {
        "total_investable_amount": 50000000,  # 5천만원
        "age": 35,
        "stock_investment_experience_years": 5,
        "target_amount": 70000000  # 7천만원
    }
    
    print("📋 테스트 입력:")
    print(json.dumps(test_input, indent=2, ensure_ascii=False))
    print("\n" + "=" * 60)
    
    try:
        advisor = InvestmentAdvisor()
        print("✅ InvestmentAdvisor 생성 완료")
        print(f"✅ LangGraph 노드: {list(advisor.graph.nodes.keys())}")
        
        print("\n🚀 투자 상담 시작...")
        print("-" * 60)
        
        session_id = None
        
        async for event in advisor.run_consultation(test_input):
            event_type = event.get("type")
            agent_name = event.get("agent_name", "")
            
            if event_type == "node_start":
                print(f"\n🤖 {agent_name.upper()} 에이전트 시작...")
                session_id = event.get("session_id")
            
            elif event_type == "node_complete":
                print(f"✅ {agent_name.upper()} 에이전트 완료")
                
                # Memory에서 중간 과정 조회
                if session_id:
                    print(f"📝 {agent_name} 중간 과정:")
                    events = get_thinking_process(session_id, agent_name)
                    print(f"   이벤트 수: {len(events)}개")
                    if events:
                        # 첫 번째 이벤트 미리보기
                        first_event = str(events[0])[:200] + "..." if len(str(events[0])) > 200 else str(events[0])
                        print(f"   첫 이벤트: {first_event}")
            
            elif event_type == "final_complete":
                print("\n" + "=" * 60)
                print("🎉 투자 상담 완료!")
                print("=" * 60)
                
                # 최종 결과 요약
                print("\n📊 최종 결과:")
                results = [
                    ("재무 분석", event.get('financial_analysis')),
                    ("포트폴리오 추천", event.get('portfolio_recommendation')),
                    ("리스크 분석", event.get('risk_analysis'))
                ]
                
                for name, result in results:
                    status = "✅" if result else "❌"
                    print(f"- {name}: {status}")
                    if result:
                        # 처음 100자만 미리보기
                        preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                        print(f"  {preview}")
                
                print(f"\n🔗 세션 ID: {session_id}")
                print("   (이 ID로 나중에 중간 과정을 다시 조회할 수 있습니다)")
        
        print("\n✨ 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()

def test_graph_structure():
    """그래프 구조만 테스트"""
    print("🧪 그래프 구조 테스트")
    
    try:
        advisor = InvestmentAdvisor()
        print("✅ InvestmentAdvisor 생성 성공")
        print(f"✅ 노드: {list(advisor.graph.nodes.keys())}")
        print(f"✅ 엣지: {list(advisor.graph.edges)}")
        
        # Memory 상태 확인
        from investment_advisor import agent_client
        if agent_client.memory_id:
            print(f"✅ Memory ID: {agent_client.memory_id}")
        else:
            print("❌ Memory 초기화 실패")
        
    except Exception as e:
        print(f"❌ 구조 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_investment_advisor())
