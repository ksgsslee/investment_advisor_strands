"""
deploy.py
Portfolio Architect 배포 스크립트

MCP Server와 Portfolio Architect Runtime을 순차적으로 배포합니다.
단순화된 아키텍처로 관리하기 쉬운 시스템을 구축합니다.

주요 기능:
1. MCP Server 배포 (ETF 데이터 조회 도구)
2. Portfolio Architect Runtime 배포 (AI 에이전트)
"""

import sys
import os
import time
import json
import boto3
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime

# 공통 utils 모듈 import
utils_path = str(Path(__file__).parent.parent)
sys.path.append(utils_path)
from utils import create_agentcore_role, setup_cognito_user_pool

# ================================
# 설정 상수
# ================================

class Config:
    """배포 설정 상수"""
    MCP_SERVER_NAME = "mcp_server_portfolio"
    AGENT_NAME = "portfolio_architect"
    REGION = "us-west-2"
    MAX_DEPLOY_MINUTES = 15
    STATUS_CHECK_INTERVAL = 30

# ================================
# MCP Server 배포 함수들
# ================================

def deploy_mcp_server():
    """
    MCP Server 배포 (mcp 폴더의 deploy.py 호출)
    
    Returns:
        dict: MCP Server 배포 정보 (agent_arn, bearer_token 등)
    """
    print("🚀 MCP Server 배포 시작...")
    
    # mcp 폴더의 deploy.py 실행
    import subprocess
    current_dir = Path(__file__).parent
    mcp_deploy_script = current_dir / "mcp" / "deploy.py"
    
    result = subprocess.run([
        sys.executable, str(mcp_deploy_script)
    ], capture_output=True, text=True, cwd=str(current_dir / "mcp"))
    
    if result.returncode != 0:
        print(f"❌ MCP Server 배포 실패:")
        print(result.stdout)
        print(result.stderr)
        raise Exception("MCP Server 배포 실패")
    
    print("✅ MCP Server 배포 완료!")
    
    # 배포 정보 로드
    mcp_info_file = current_dir / "mcp" / "deployment_info.json"
    with open(mcp_info_file, 'r') as f:
        mcp_deployment_info = json.load(f)
    
    return mcp_deployment_info["mcp_server"]

# ================================
# Portfolio Architect Runtime 배포 함수들
# ================================

def deploy_portfolio_architect(mcp_server_info):
    """
    Portfolio Architect Runtime 배포
    
    MCP Server와 연동하는 AI 포트폴리오 설계사를 배포합니다.
    
    Args:
        mcp_server_info (dict): MCP Server 배포 정보
        
    Returns:
        dict: Portfolio Architect 배포 정보
    """
    print("🎯 Portfolio Architect Runtime 배포 시작...")
    
    # 1. IAM 역할 생성
    print("🔐 Portfolio Architect IAM 역할 생성 중...")
    agentcore_iam_role = create_agentcore_role(agent_name=Config.AGENT_NAME)
    print("✅ IAM 역할 생성 완료")
    
    # 2. Runtime 구성
    print("🔧 Portfolio Architect Runtime 구성 중...")
    current_dir = Path(__file__).parent
    
    agentcore_runtime = Runtime()
    agentcore_runtime.configure(
        entrypoint=str(current_dir / "portfolio_architect.py"),
        execution_role=agentcore_iam_role['Role']['Arn'],
        auto_create_ecr=True,
        requirements_file=str(current_dir / "requirements.txt"),
        region=Config.REGION,
        agent_name=Config.AGENT_NAME
    )
    print("✅ Portfolio Architect Runtime 구성 완료")
    
    # 3. 배포 실행
    print("🚀 Portfolio Architect 배포 중...")
    launch_result = agentcore_runtime.launch(auto_update_on_conflict=True)
    print("✅ Portfolio Architect 배포 시작 완료")
    
    # 4. 배포 상태 대기
    print("⏳ Portfolio Architect 배포 상태 모니터링 중...")
    end_statuses = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
    max_checks = (Config.MAX_DEPLOY_MINUTES * 60) // Config.STATUS_CHECK_INTERVAL
    
    for i in range(max_checks):
        try:
            status_response = agentcore_runtime.status()
            status = status_response.endpoint['status']
            elapsed_time = (i + 1) * Config.STATUS_CHECK_INTERVAL
            print(f"📊 Portfolio Architect 상태: {status} ({elapsed_time//60}분 {elapsed_time%60}초 경과)")
            
            if status in end_statuses:
                break
                
        except Exception as e:
            print(f"⚠️ 상태 확인 오류: {str(e)}")
            
        time.sleep(Config.STATUS_CHECK_INTERVAL)
    
    if status != 'READY':
        raise Exception(f"Portfolio Architect 배포 실패: {status}")
    
    print("✅ Portfolio Architect 배포 완료!")
    
    return {
        "agent_arn": launch_result.agent_arn,
        "agent_id": launch_result.agent_id,
        "mcp_server_arn": mcp_server_info["agent_arn"],
        "region": Config.REGION
    }

# ================================
# 배포 정보 저장
# ================================

def save_deployment_info(mcp_server_info, portfolio_architect_info):
    """
    전체 배포 정보 저장
    
    Args:
        mcp_server_info (dict): MCP Server 배포 정보
        portfolio_architect_info (dict): Portfolio Architect 배포 정보
        
    Returns:
        str: 저장된 JSON 파일 경로
    """
    print("📄 전체 배포 정보 저장 중...")
    
    current_dir = Path(__file__).parent
    deployment_info = {
        "mcp_server": mcp_server_info,
        "portfolio_architect": portfolio_architect_info,
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = current_dir / "deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"✅ 배포 정보 저장: {info_file}")
    return str(info_file)

# ================================
# 메인 실행 함수
# ================================

def main():
    """
    메인 배포 함수
    
    MCP Server와 Portfolio Architect를 순차적으로 배포합니다.
    
    Returns:
        int: 성공 시 0, 실패 시 1
    """
    try:
        print("=" * 70)
        print("🎯 Portfolio Architect 전체 시스템 배포")
        print(f"🌍 리전: {Config.REGION}")
        print("📋 배포 순서:")
        print("   1. MCP Server (ETF 데이터 조회 도구)")
        print("   2. Portfolio Architect (AI 포트폴리오 설계사)")
        print("=" * 70)
        
        # 1. MCP Server 배포
        mcp_server_info = deploy_mcp_server()
        
        print("\n" + "=" * 50)
        print("🎉 MCP Server 배포 성공!")
        print(f"🔗 MCP Server ARN: {mcp_server_info['agent_arn']}")
        print("=" * 50)
        
        # 2. Portfolio Architect 배포
        portfolio_architect_info = deploy_portfolio_architect(mcp_server_info)
        
        print("\n" + "=" * 50)
        print("🎉 Portfolio Architect 배포 성공!")
        print(f"🔗 Portfolio Architect ARN: {portfolio_architect_info['agent_arn']}")
        print("=" * 50)
        
        # 3. 배포 정보 저장
        info_file = save_deployment_info(mcp_server_info, portfolio_architect_info)
        
        print("\n" + "=" * 70)
        print("🎉 전체 시스템 배포 완료!")
        print(f"📄 배포 정보: {info_file}")
        print("=" * 70)
        
        print("\n📋 다음 단계:")
        print("1. MCP Server 테스트: cd mcp && python test_remote.py")
        print("2. Streamlit 앱 실행: streamlit run app.py")
        print("3. 전체 시스템 테스트")
        
        return 0
        
    except Exception as e:
        print("=" * 70)
        print(f"❌ 배포 실패: {str(e)}")
        print("💡 문제 해결 방법:")
        print("1. AWS 권한 확인")
        print("2. 필수 파일 존재 확인")
        print("3. 로그 확인 후 재시도")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())