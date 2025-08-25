"""
test_streaming.py
Investment Advisor 스트리밍 테스트

async yield를 사용한 실시간 진행 상황 확인
"""

import asyncio
from investment_advisor import InvestmentAdvisor

async def main():
    """스트리밍 테스트"""
    print("🚀 Investment Advisor 스트리밍 테스트")
    print("=" * 50)
    
    # Investment Advisor 초기화
    advisor = InvestmentAdvisor()
    
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
    print()
    
    # 스트리밍 상담 실행
    session_id = None
    final_response = None
    
    try:
        async for event in advisor.run_consultation_async(user_input, "streaming_test_user"):
            session_id = event.get("session_id")
            
            # 이벤트 타입별 처리
            if event.get("type") == "data":
                # 도구에서 yield한 진행 상황 메시지
                data = event.get("data", "")
                if data.strip():
                    print(f"📡 {data}")
            
            elif event.get("type") == "message":
                # AI 에이전트의 메시지
                message = event.get("message", {})
                if message.get("role") == "assistant":
                    for content in message.get("content", []):
                        if "text" in content:
                            final_response = content["text"]
            
            elif event.get("type") == "result":
                # 최종 결과
                final_response = str(event.get("result", ""))
            
            elif event.get("type") == "error":
                print(f"❌ 오류: {event.get('error')}")
                return
        
        print("\n" + "=" * 50)
        print("🎉 스트리밍 상담 완료!")
        
        if session_id:
            print(f"✅ 세션 ID: {session_id}")
            
            # 메모리 데이터 확인
            from investment_advisor import memory_storage
            memory_data = memory_storage.get(session_id, {})
            
            if memory_data:
                print(f"\n💾 저장된 데이터:")
                for step in memory_data.keys():
                    print(f"   ✅ {step}")
            
            if final_response:
                print(f"\n📋 최종 AI 응답:")
                print("-" * 30)
                print(final_response[:500] + "..." if len(final_response) > 500 else final_response)
        
    except Exception as e:
        print(f"❌ 스트리밍 테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())