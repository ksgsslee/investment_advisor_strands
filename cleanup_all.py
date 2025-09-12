#!/usr/bin/env python3
"""
cleanup_all.py - 전체 시스템 정리
"""

import subprocess
import sys
from config import Config

def run_cmd(cmd, cwd=None):
    """명령어 실행"""
    print(f"🔄 {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"⚠️ 실패 (무시): {cmd}")
    else:
        print(f"✅ 완료: {cmd}")

def cleanup_step(name, commands):
    """정리 단계 실행"""
    print(f"\n🧹 {name}")
    for cmd, cwd in commands:
        run_cmd(cmd, cwd)

def main():
    print("🧹 AI 투자 어드바이저 시스템 정리")
    print(f"📍 정리 대상 리전: {Config.REGION}")
    
    response = input("정말로 모든 리소스를 삭제하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 취소됨")
        return 0
    
    # 정리 단계 (역순)
    steps = [
        ("Lab 4: Investment Advisor", [
            ("python cleanup.py", "investment_advisor")
        ]),
        ("Lab 3: Risk Manager", [
            ("python cleanup.py", "risk_manager")
        ]),
        ("Lab 2: Portfolio Architect", [
            ("python cleanup.py", "portfolio_architect")
        ]),
        ("Lab 1: Financial Analyst", [
            ("python cleanup.py", "financial_analyst")
        ])
    ]
    
    for name, commands in steps:
        cleanup_step(name, commands)
    
    print("\n🎉 정리 완료!")
    return 0

if __name__ == "__main__":
    sys.exit(main())