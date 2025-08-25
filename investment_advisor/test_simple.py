"""
test_simple.py
Investment Advisor 간단 테스트

최대한 간단하게 테스트하는 스크립트
"""

from investment_advisor import InvestmentAdvisor

def main():
    """간단한 테스트"""
    print("🚀 Investment Advisor 간단 테스트")
    print("=" * 40)
    
    # Investment Advisor 초기화
    advisor = InvestmentAdvisor()
    
    # 테스트 데이터
    user_input = {
        "total_investable_amount": 30000000,    # 3천만원
        "age": 40,                             # 40세
        "stock_investment_experience_years": 5,  # 5년 경험
        "target_amount": 36000000              # 3천6백만원 목표 (20% 수익)
    }
    
    print(f"📝 테스트 데이터:")
    print(f"   투자금액: {user_input['total_investable_amount']:,}원")
    print(f"   나이: {user_input['age']}세")
    print(f"   경험: {user_input['stock_investment_experience_years']}년")
    print(f"   목표: {user_input['target_amount']:,}원")
    print()
    
    # 상담 실행
    result = advisor.run_consultation(user_input, "test_user")
    
    # 결과 출력
    if result["status"] == "success":
        print(f"✅ 테스트 성공!")
        print(f"세션 ID: {result['session_id']}")
        
        print(f"\n📋 AI 응답:")
        print("-" * 30)
        print(result["response"])
        
        # 메모리 데이터 확인
        memory_data = result.get("memory_data", {})
        if memory_data:
            print(f"\n💾 저장된 데이터:")
            for step in memory_data.keys():
                print(f"   ✅ {step}")
        
        print(f"\n💾 상세 결과가 consultation_result_{result['session_id']}.json에 저장되었습니다.")
        
    else:
        print(f"❌ 테스트 실패: {result.get('error')}")

if __name__ == "__main__":
    main()