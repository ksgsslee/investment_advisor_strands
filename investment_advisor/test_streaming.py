"""
test_streaming.py
Investment Advisor Sequential Multi-Agent 스트리밍 테스트

4단계 순차 투자 상담 시스템 테스트
1단계: 재무 분석 → 2단계: 포트폴리오 설계 → 3단계: 리스크 분석 → 4단계: 종합 보고서
"""

import asyncio
import json
from investment_advisor import InvestmentAdvisor

async def main():
    """Sequential Multi-Agent 스트리밍 테스트"""
    print("🚀 Investment Advisor Sequential Multi-Agent 스트리밍 테스트")
    print("=" * 70)
    
    # Investment Advisor 초기화
    advisor = InvestmentAdvisor()
    
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
    print()
    
    # 단계별 진행 상황 추적
    step_results = {}
    step_names = {
        1: "🔍 재무 분석",
        2: "📊 포트폴리오 설계", 
        3: "⚠️ 리스크 분석",
        4: "📝 종합 보고서 작성"
    }
    
    try:
        print("🎬 Sequential Multi-Agent 투자 상담 시작!")
        print("-" * 50)
        
        async for event in advisor.run_consultation_async(user_input):
            
            # 단계별 진행 메시지
            if event.get("type") == "data" and "message" in event:
                message = event.get("message", "")
                step = event.get("step")
                if step and step in step_names:
                    print(f"\n{step_names[step]} 단계 시작...")
                    print(f"   {message}")
            
            # 단계 완료
            elif event.get("type") == "step_complete":
                step = event.get("step")
                step_name = event.get("step_name", "")
                data = event.get("data", {})
                
                step_results[step] = data
                print(f"   ✅ {step_name} 완료!")
                
                # 각 단계별 간단한 결과 미리보기
                if step == 1 and "analysis_data" in data:
                    try:
                        analysis = json.loads(data["analysis_data"])
                        print(f"      위험성향: {analysis.get('risk_profile', 'N/A')}")
                        print(f"      목표수익률: {analysis.get('required_annual_return_rate', 'N/A')}%")
                    except:
                        print("      분석 결과 파싱 실패")
                
                elif step == 2 and "portfolio_result" in data:
                    try:
                        portfolio = json.loads(data["portfolio_result"])
                        if "portfolio_allocation" in portfolio:
                            print("      추천 포트폴리오:")
                            for etf, ratio in list(portfolio["portfolio_allocation"].items())[:3]:
                                print(f"        {etf}: {ratio}%")
                    except:
                        print("      포트폴리오 결과 파싱 실패")
                
                elif step == 3 and "risk_result" in data:
                    try:
                        risk = json.loads(data["risk_result"])
                        scenarios = [k for k in risk.keys() if k.startswith('scenario')]
                        print(f"      분석된 시나리오: {len(scenarios)}개")
                    except:
                        print("      리스크 결과 파싱 실패")
                
                elif step == 4 and "final_report" in data:
                    report = data["final_report"]
                    lines = report.split('\n')[:5]  # 첫 5줄만 미리보기
                    print("      보고서 미리보기:")
                    for line in lines:
                        if line.strip():
                            print(f"        {line.strip()}")
                    print("        ...")
            
            # 최종 결과
            elif event.get("type") == "streaming_complete":
                final_result = event.get("final_result", {})
                print(f"\n🎉 4단계 투자 상담 완료!")
                
                # 최종 보고서 출력
                if "final_report" in final_result:
                    print("\n" + "=" * 70)
                    print("📋 최종 투자 상담 보고서")
                    print("=" * 70)
                    print(final_result["final_report"])
                
                break
            
            # 오류 처리
            elif event.get("type") == "error":
                print(f"\n❌ 오류 발생: {event.get('error')}")
                return
        
        # 단계별 결과 요약
        print("\n" + "=" * 70)
        print("📊 4단계 분석 결과 요약")
        print("=" * 70)
        
        for step in range(1, 5):
            if step in step_results:
                print(f"\n{step_names[step]} 결과:")
                print("-" * 40)
                
                data = step_results[step]
                
                if step == 1 and "analysis_data" in data:
                    try:
                        analysis = json.loads(data["analysis_data"])
                        print(f"   위험 성향: {analysis.get('risk_profile', 'N/A')}")
                        print(f"   위험 성향 근거: {analysis.get('risk_profile_reason', 'N/A')[:100]}...")
                        print(f"   목표 수익률: {analysis.get('required_annual_return_rate', 'N/A')}%")
                    except:
                        print("   결과 파싱 실패")
                
                elif step == 2 and "portfolio_result" in data:
                    try:
                        portfolio = json.loads(data["portfolio_result"])
                        if "portfolio_allocation" in portfolio:
                            print("   추천 포트폴리오:")
                            for etf, ratio in portfolio["portfolio_allocation"].items():
                                print(f"     {etf}: {ratio}%")
                        if "expected_annual_return" in portfolio:
                            print(f"   예상 연간 수익률: {portfolio['expected_annual_return']}%")
                    except:
                        print("   결과 파싱 실패")
                
                elif step == 3 and "risk_result" in data:
                    try:
                        risk = json.loads(data["risk_result"])
                        scenarios = [k for k in risk.keys() if k.startswith('scenario')]
                        print(f"   분석된 시나리오: {len(scenarios)}개")
                        for scenario_key in scenarios[:2]:  # 처음 2개만 표시
                            scenario = risk[scenario_key]
                            print(f"     {scenario.get('name', 'N/A')}: {scenario.get('expected_loss', 'N/A')}% 손실")
                    except:
                        print("   결과 파싱 실패")
                
                elif step == 4 and "final_report" in data:
                    report = data["final_report"]
                    word_count = len(report.split())
                    line_count = len(report.split('\n'))
                    print(f"   보고서 길이: {word_count}단어, {line_count}줄")
                    print("   보고서 구조: 종합 분석 → 추천 포트폴리오 → 리스크 관리 → 실행 가이드")
        
        print(f"\n💾 테스트 완료!")
        print(f"   총 {len(step_results)}단계 실행됨")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())