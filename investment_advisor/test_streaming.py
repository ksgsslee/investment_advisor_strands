"""
test_streaming.py
Investment Advisor 대화형 스트리밍 테스트

3단계 대화형 투자 상담 시스템 테스트
"""

import asyncio
from investment_advisor import InvestmentAdvisor

async def main():
    """대화형 스트리밍 테스트"""
    print("🚀 Investment Advisor 대화형 스트리밍 테스트")
    print("=" * 60)
    
    # Investment Advisor 초기화
    advisor = InvestmentAdvisor(user_id="conversational_test_user")
    
    # 테스트 데이터
    user_input = {
        "total_investable_amount": 50000000,    # 5천만원
        "age": 35,                             # 35세
        "stock_investment_experience_years": 8,  # 8년 경험
        "target_amount": 70000000              # 7천만원 목표 (40% 수익)
    }
    
    print(f"📝 테스트 시나리오:")
    print(f"   💰 투자금액: {user_input['total_investable_amount']:,}원")
    print(f"   👤 나이: {user_input['age']}세")
    print(f"   📈 경험: {user_input['stock_investment_experience_years']}년")
    print(f"   🎯 목표: {user_input['target_amount']:,}원")
    print(f"   🆔 사용자: {advisor.user_id}")
    print(f"   📱 세션: {advisor.session_id}")
    print()
    
    # 단계별 진행 상황 추적
    current_step = 0
    step_names = ["시작", "재무분석", "포트폴리오설계", "리스크분석", "완료"]
    tool_results = {}
    
    try:
        print("🎬 대화형 상담 시작!")
        print("-" * 40)
        
        async for event in advisor.run_consultation_async(user_input):
            
            # AI 대화 텍스트 스트리밍
            if event.get("type") == "data":
                data = event.get("data", "")
                if data.strip():
                    print(f"{data}", end="", flush=True)
            
            # 도구 사용 이벤트
            elif event.get("type") == "message":
                message = event.get("message", {})
                
                if message.get("role") == "assistant":
                    for content in message.get("content", []):
                        if "toolUse" in content:
                            tool_use = content["toolUse"]
                            tool_name = tool_use.get("name", "unknown")
                            
                            # 단계 진행 표시
                            if "financial_analyst" in tool_name:
                                current_step = 1
                                print(f"\n\n🔍 1단계: 재무 분석 실행 중...")
                            elif "portfolio_architect" in tool_name:
                                current_step = 2
                                print(f"\n\n📊 2단계: 포트폴리오 설계 실행 중...")
                            elif "risk_manager" in tool_name:
                                current_step = 3
                                print(f"\n\n⚠️ 3단계: 리스크 분석 실행 중...")
                
                elif message.get("role") == "user":
                    for content in message.get("content", []):
                        if "toolResult" in content:
                            tool_result = content["toolResult"]
                            status = tool_result.get("status", "unknown")
                            
                            # 도구 결과 저장
                            if current_step == 1:
                                tool_results["financial_analysis"] = tool_result.get("content", [{}])[0].get("text", "")
                                print(f"   ✅ 재무 분석 완료!")
                            elif current_step == 2:
                                tool_results["portfolio_design"] = tool_result.get("content", [{}])[0].get("text", "")
                                print(f"   ✅ 포트폴리오 설계 완료!")
                            elif current_step == 3:
                                tool_results["risk_analysis"] = tool_result.get("content", [{}])[0].get("text", "")
                                print(f"   ✅ 리스크 분석 완료!")
            
            # 최종 결과
            elif event.get("type") == "result":
                print(f"\n\n🎉 투자 상담 완료!")
                break
            
            # 오류 처리
            elif event.get("type") == "error":
                print(f"\n❌ 오류 발생: {event.get('error')}")
                return
        
        # 결과 요약 출력
        print("\n" + "=" * 60)
        print("📋 상담 결과 요약")
        print("=" * 60)
        
        # 각 단계별 결과 파싱 및 표시
        if "financial_analysis" in tool_results:
            print("\n🔍 1단계: 재무 분석 결과")
            print("-" * 30)
            try:
                import json
                fa_result = json.loads(tool_results["financial_analysis"])
                if "analysis_data" in fa_result:
                    analysis = json.loads(fa_result["analysis_data"])
                    print(f"   위험 성향: {analysis.get('risk_profile', 'N/A')}")
                    print(f"   목표 수익률: {analysis.get('required_annual_return_rate', 'N/A')}%")
                else:
                    print("   분석 데이터를 파싱할 수 없습니다")
            except:
                print("   결과 파싱 실패")
        
        if "portfolio_design" in tool_results:
            print("\n📊 2단계: 포트폴리오 설계 결과")
            print("-" * 30)
            try:
                import json
                pd_result = json.loads(tool_results["portfolio_design"])
                if "portfolio_result" in pd_result:
                    portfolio = json.loads(pd_result["portfolio_result"])
                    if "portfolio_allocation" in portfolio:
                        print("   추천 포트폴리오:")
                        for etf, ratio in portfolio["portfolio_allocation"].items():
                            print(f"     {etf}: {ratio}%")
                else:
                    print("   포트폴리오 데이터를 파싱할 수 없습니다")
            except:
                print("   결과 파싱 실패")
        
        if "risk_analysis" in tool_results:
            print("\n⚠️ 3단계: 리스크 분석 결과")
            print("-" * 30)
            try:
                import json
                ra_result = json.loads(tool_results["risk_analysis"])
                if "risk_result" in ra_result:
                    risk = json.loads(ra_result["risk_result"])
                    if "scenario1" in risk:
                        print(f"   시나리오 1: {risk['scenario1'].get('name', 'N/A')}")
                    if "scenario2" in risk:
                        print(f"   시나리오 2: {risk['scenario2'].get('name', 'N/A')}")
                else:
                    print("   리스크 데이터를 파싱할 수 없습니다")
            except:
                print("   결과 파싱 실패")
        
        print(f"\n💾 세션 정보:")
        print(f"   세션 ID: {advisor.session_id}")
        print(f"   메모리 ID: {advisor.memory_id}")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())