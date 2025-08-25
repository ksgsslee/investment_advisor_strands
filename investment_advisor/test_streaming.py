"""
test_streaming.py
Investment Advisor 스트리밍 테스트

리팩토링된 AgentCore Memory 기반 시스템 테스트
"""

import asyncio
from investment_advisor import InvestmentAdvisor

async def main():
    """스트리밍 테스트"""
    print("🚀 Investment Advisor 스트리밍 테스트 (AgentCore Memory)")
    print("=" * 60)
    
    # Investment Advisor 초기화 (메모리 자동 생성)
    advisor = InvestmentAdvisor(user_id="streaming_test_user")
    
    # 테스트 데이터
    user_input = {
        "total_investable_amount": 50000000,    # 5천만원
        "age": 35,                             # 35세
        "stock_investment_experience_years": 8,  # 8년 경험
        "target_amount": 70000000              # 7천만원 목표 (40% 수익)
    }
    
    print(f"📝 테스트 데이터:")
    print(f"   투자금액: {user_input['total_investable_amount']:,}원")
    print(f"   나이: {user_input['age']}세")
    print(f"   경험: {user_input['stock_investment_experience_years']}년")
    print(f"   목표: {user_input['target_amount']:,}원")
    print(f"   사용자 ID: {advisor.user_id}")
    print(f"   세션 ID: {advisor.session_id}")
    print(f"   메모리 ID: {advisor.memory_id}")
    print()
    
    # 스트리밍 상담 실행
    final_response = None
    tool_calls = []
    
    try:
        async for event in advisor.run_consultation_async(user_input):
            session_id = event.get("session_id")
            memory_id = event.get("memory_id")
            
            # 이벤트 타입별 처리
            if event.get("type") == "data":
                # AI 에이전트의 실시간 사고 과정
                data = event.get("data", "")
                if data.strip():
                    print(f"🤖 {data}", end="", flush=True)
            
            elif event.get("type") == "message":
                # 메시지 이벤트 처리
                message = event.get("message", {})
                
                if message.get("role") == "assistant":
                    # Assistant 메시지: 도구 사용 정보
                    for content in message.get("content", []):
                        if "toolUse" in content:
                            tool_use = content["toolUse"]
                            tool_name = tool_use.get("name", "unknown")
                            print(f"\n🛠️ 도구 호출: {tool_name}")
                            tool_calls.append(tool_name)
                        elif "text" in content:
                            final_response = content["text"]
                
                elif message.get("role") == "user":
                    # User 메시지: 도구 실행 결과
                    for content in message.get("content", []):
                        if "toolResult" in content:
                            tool_result = content["toolResult"]
                            status = tool_result.get("status", "unknown")
                            print(f"   ✅ 도구 실행 완료 ({status})")
            
            elif event.get("type") == "result":
                # 최종 결과
                final_response = str(event.get("result", ""))
                print(f"\n📋 최종 결과 수신")
            
            elif event.get("type") == "error":
                print(f"\n❌ 오류: {event.get('error')}")
                return
        
        print("\n" + "=" * 60)
        print("🎉 스트리밍 상담 완료!")
        
        # 결과 요약
        print(f"\n📊 실행 요약:")
        print(f"   ✅ 세션 ID: {session_id}")
        print(f"   ✅ 메모리 ID: {memory_id}")
        print(f"   ✅ 호출된 도구: {', '.join(tool_calls) if tool_calls else '없음'}")
        
        if final_response:
            print(f"\n📋 최종 AI 응답 (처음 300자):")
            print("-" * 40)
            print(final_response[:300] + "..." if len(final_response) > 300 else final_response)
        
        # AgentCore Memory 확인
        print(f"\n💾 AgentCore Memory 상태:")
        try:
            from bedrock_agentcore.memory import MemoryClient
            memory_client = MemoryClient(region_name="us-west-2")
            
            # 최근 대화 내용 조회
            recent_turns = memory_client.get_last_k_turns(
                memory_id=advisor.memory_id,
                actor_id=advisor.user_id,
                session_id=advisor.session_id,
                k=2,
                branch_name="main"
            )
            
            if recent_turns:
                print(f"   ✅ 저장된 대화 턴: {len(recent_turns)}개")
                for i, turn in enumerate(recent_turns):
                    print(f"   📝 턴 {i+1}: {len(turn)}개 메시지")
            else:
                print(f"   ⚠️ 저장된 대화 없음")
                
        except Exception as e:
            print(f"   ❌ 메모리 조회 실패: {e}")
        
    except Exception as e:
        print(f"❌ 스트리밍 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())