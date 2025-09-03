#!/usr/bin/env python3
"""
test_investment_advisor.py

LangGraph 기반 Investment Advisor 테스트
"""

import asyncio
import json
from investment_advisor import InvestmentAdvisor

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
                    thinking = advisor.get_thinking_process(session_id, agent_name)
                    # 처음 200자만 표시
                    preview = thinking[:200] + "..." if len(thinking) > 200 else thinking
                    print(f"   {preview}")
            
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
    print("🎯 테스트 선택:")
    print("1. 전체 테스트 (실제 에이전트 호출)")
    print("2. 구조 테스트만")
    
    choice = input("선택 (1 또는 2): ").strip()
    
    if choice == "2":
        test_graph_structure()
    else:
        asyncio.run(test_investment_advisor())