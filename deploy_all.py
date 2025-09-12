#!/usr/bin/env python3
"""
deploy_all.py - 전체 시스템 배포
"""

import subprocess
import sys
from pathlib import Path
from config import Config

def run_cmd(cmd, cwd=None):
    """명령어 실행"""
    print(f"🔄 {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ 실패: {cmd}")
        return False
    print(f"✅ 완료: {cmd}")
    return True

def deploy_step(name, commands):
    """배포 단계 실행"""
    print(f"\n🎯 {name}")
    for cmd, cwd in commands:
        if not run_cmd(cmd, cwd):
            response = input("계속 진행하시겠습니까? (y/N): ")
            if response.lower() != 'y':
                return False
    return True

def main():
    print("🚀 AI 투자 어드바이저 시스템 배포")
    print(f"📍 배포 리전: {Config.REGION}")
    print(f"🏗️ 에이전트 구성: {Config.FINANCIAL_ANALYST_NAME}, {Config.PORTFOLIO_ARCHITECT_NAME}, {Config.RISK_MANAGER_NAME}, {Config.INVESTMENT_ADVISOR_NAME}")
    
    # AWS 확인
    if not run_cmd("aws sts get-caller-identity"):
        print("❌ AWS 자격 증명을 설정하세요: aws configure")
        return 1
    
    # 배포 단계
    steps = [
        ("Lab 1: Financial Analyst", [
            ("python deploy.py", "financial_analyst")
        ]),
        ("Lab 2: Portfolio Architect", [
            ("python deploy_mcp.py", "portfolio_architect/mcp_server"),
            ("python deploy.py", "portfolio_architect")
        ]),
        ("Lab 3: Risk Manager", [
            ("python deploy_lambda_layer.py", "risk_manager/lambda_layer"),
            ("python deploy_lambda.py", "risk_manager/lambda"),
            ("python deploy_gateway.py", "risk_manager/gateway"),
            ("python deploy.py", "risk_manager")
        ]),
        ("Lab 4: Investment Advisor", [
            ("python deploy_agentcore_memory.py", "investment_advisor/agentcore_memory"),
            ("python deploy.py", "investment_advisor")
        ])
    ]
    
    for name, commands in steps:
        if not deploy_step(name, commands):
            return 1
    
    print("\n🎉 배포 완료!")
    print("웹 앱 실행: cd investment_advisor && streamlit run app.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())