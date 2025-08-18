"""
각 Lab 에이전트 개별 테스트 스크립트
"""
import os
import sys
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def test_lab1():
    """Lab 1: Financial Analyst 테스트"""
    print("=" * 50)
    print("Lab 1: Financial Analyst (Reflection Pattern) 테스트")
    print("=" * 50)
    
    try:
        from agents.lab1_financial_analyst import test_financial_analyst
        result = test_financial_analyst()
        return result
    except Exception as e:
        print(f"Lab 1 테스트 실패: {e}")
        return None

def test_lab2():
    """Lab 2: Portfolio Architect 테스트"""
    print("\n" + "=" * 50)
    print("Lab 2: Portfolio Architect (Tool Use Pattern) 테스트")
    print("=" * 50)
    
    try:
        from agents.lab2_portfolio_architect import test_portfolio_architect
        result = test_portfolio_architect()
        return result
    except Exception as e:
        print(f"Lab 2 테스트 실패: {e}")
        return None

def test_lab3():
    """Lab 3: Risk Manager 테스트"""
    print("\n" + "=" * 50)
    print("Lab 3: Risk Manager (Planning Pattern) 테스트")
    print("=" * 50)
    
    try:
        from agents.lab3_risk_manager import test_risk_manager
        result = test_risk_manager()
        return result
    except Exception as e:
        print(f"Lab 3 테스트 실패: {e}")
        return None

def test_lab4():
    """Lab 4: Investment Advisor 테스트"""
    print("\n" + "=" * 50)
    print("Lab 4: Investment Advisor (Multi-Agent Pattern) 테스트")
    print("=" * 50)
    
    try:
        from agents.lab4_investment_advisor import test_investment_advisor
        result = test_investment_advisor()
        return result
    except Exception as e:
        print(f"Lab 4 테스트 실패: {e}")
        return None

def main():
    """메인 테스트 함수"""
    print("🤖 Strands Agent 기반 AI 투자 어드바이저 테스트")
    print("=" * 60)
    
    # API 키 확인
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일을 생성하고 API 키를 설정해주세요.")
        return
    
    print("✅ API 키 확인 완료")
    
    # 각 Lab 순차 테스트
    results = {}
    
    # Lab 1 테스트
    results['lab1'] = test_lab1()
    
    # Lab 2 테스트 (Lab 1 성공 시)
    if results['lab1'] and results['lab1'].get('is_valid'):
        results['lab2'] = test_lab2()
    else:
        print("\n⚠️ Lab 1 검증 실패로 Lab 2 건너뜀")
    
    # Lab 3 테스트 (Lab 2 성공 시)
    if results.get('lab2') and results['lab2'].get('status') == 'success':
        results['lab3'] = test_lab3()
    else:
        print("\n⚠️ Lab 2 실패로 Lab 3 건너뜀")
    
    # Lab 4 통합 테스트
    print("\n" + "=" * 50)
    print("전체 통합 테스트 실행")
    print("=" * 50)
    results['lab4'] = test_lab4()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("🎯 테스트 결과 요약")
    print("=" * 60)
    
    for lab, result in results.items():
        if result is None:
            print(f"❌ {lab.upper()}: 실행 실패")
        elif lab == 'lab1':
            status = "✅ 성공" if result.get('is_valid') else "❌ 검증 실패"
            print(f"{status} {lab.upper()}: Reflection Pattern")
        elif lab in ['lab2', 'lab3']:
            status = "✅ 성공" if result.get('status') == 'success' else "❌ 실패"
            pattern = "Tool Use Pattern" if lab == 'lab2' else "Planning Pattern"
            print(f"{status} {lab.upper()}: {pattern}")
        elif lab == 'lab4':
            status = "✅ 성공" if result.get('status') == 'success' else "❌ 실패"
            print(f"{status} {lab.upper()}: Multi-Agent Pattern")
    
    print("\n🚀 Streamlit 앱 실행: streamlit run streamlit_app.py")

if __name__ == "__main__":
    main()