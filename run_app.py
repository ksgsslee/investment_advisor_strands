#!/usr/bin/env python3
"""
AI 투자 어드바이저 실행 스크립트
"""
import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """필수 요구사항 확인"""
    print("🔍 시스템 요구사항 확인 중...")
    
    # Python 버전 확인
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 이상이 필요합니다.")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} 확인")
    
    # .env 파일 확인
    if not Path('.env').exists():
        print("❌ .env 파일이 없습니다.")
        print("   .env.example을 복사하여 .env 파일을 생성하고 API 키를 설정해주세요.")
        return False
    
    # API 키 확인
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 API 키를 설정해주세요.")
        return False
    
    print("✅ API 키 확인 완료")
    
    return True

def install_requirements():
    """필요한 패키지 설치"""
    print("📦 필요한 패키지 설치 중...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ 패키지 설치 완료")
        return True
    except subprocess.CalledProcessError:
        print("❌ 패키지 설치 실패")
        return False

def run_tests():
    """에이전트 테스트 실행"""
    print("🧪 에이전트 테스트 실행 중...")
    
    try:
        result = subprocess.run([sys.executable, "test_agents.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 에이전트 테스트 완료")
            return True
        else:
            print("⚠️ 일부 테스트 실패 (Streamlit 앱은 실행 가능)")
            print(result.stdout)
            return True  # 테스트 실패해도 앱은 실행
    except Exception as e:
        print(f"⚠️ 테스트 실행 중 오류: {e}")
        return True  # 테스트 실패해도 앱은 실행

def run_streamlit():
    """Streamlit 앱 실행"""
    print("🚀 Streamlit 앱 실행 중...")
    print("   브라우저에서 http://localhost:8501 로 접속하세요.")
    print("   종료하려면 Ctrl+C를 누르세요.")
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"])
    except KeyboardInterrupt:
        print("\n👋 앱이 종료되었습니다.")
    except Exception as e:
        print(f"❌ 앱 실행 중 오류: {e}")

def main():
    """메인 실행 함수"""
    print("🤖 AI 투자 어드바이저 (Strands Agent) 시작")
    print("=" * 50)
    
    # 1. 요구사항 확인
    if not check_requirements():
        print("\n❌ 요구사항을 충족하지 않습니다. 설정을 확인해주세요.")
        return
    
    # 2. 패키지 설치 (선택사항)
    install_choice = input("\n📦 패키지를 다시 설치하시겠습니까? (y/N): ").lower()
    if install_choice in ['y', 'yes']:
        if not install_requirements():
            print("❌ 패키지 설치에 실패했습니다.")
            return
    
    # 3. 테스트 실행 (선택사항)
    test_choice = input("\n🧪 에이전트 테스트를 실행하시겠습니까? (y/N): ").lower()
    if test_choice in ['y', 'yes']:
        run_tests()
    
    # 4. Streamlit 앱 실행
    print("\n" + "=" * 50)
    run_streamlit()

if __name__ == "__main__":
    main()