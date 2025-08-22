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

# shared 모듈 경로 추가
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))

# 공통 유틸리티 import
from runtime_utils import create_agentcore_runtime_role

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

def load_mcp_server_info():
    """
    MCP Server 배포 정보 로드
    
    Portfolio Architect 배포에 필요한 MCP Server 정보를 JSON 파일에서 로드합니다.
    MCP Server가 먼저 배포되어 있어야 합니다.
    
    Returns:
        dict: MCP Server 배포 정보 (agent_arn, bearer_token 등)
        
    Raises:
        FileNotFoundError: MCP Server 배포 정보 파일이 없을 때
    """
    print("📋 MCP Server 배포 정보 로드 중...")
    
    current_dir = Path(__file__).parent
    mcp_dir = current_dir / "mcp_server"
    info_file = mcp_dir / "mcp_deployment_info.json"
    
    if not info_file.exists():
        raise FileNotFoundError(
            f"MCP Server 배포 정보를 찾을 수 없습니다: {info_file}\n"
            "먼저 'python mcp/deploy.py'를 실행하세요."
        )
    
    with open(info_file, 'r') as f:
        mcp_server_info = json.load(f)
    
    print(f"✅ MCP Server ARN: {mcp_server_info['agent_arn']}")
    return mcp_server_info

def deploy_mcp_server():
    """
    MCP Server 배포 (mcp 폴더의 deploy.py 호출)
    
    Returns:
        dict: MCP Server 배포 정보 (agent_arn, bearer_token 등)
    """
    print("🚀 MCP Server 배포 시작...")
    
    # mcp_server 폴더의 deploy_mcp.py 실행
    import subprocess
    current_dir = Path(__file__).parent
    mcp_deploy_script = current_dir / "mcp_server" / "deploy_mcp.py"
    
    result = subprocess.run([
        sys.executable, str(mcp_deploy_script)
    ], capture_output=True, text=True, cwd=str(current_dir / "mcp_server"))
    
    if result.returncode != 0:
        print(f"❌ MCP Server 배포 실패:")
        print(result.stdout)
        print(result.stderr)
        raise Exception("MCP Server 배포 실패")
    
    print("✅ MCP Server 배포 완료!")
    
    # 배포 정보 로드
    return load_mcp_server_info()

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
    agentcore_iam_role = create_agentcore_runtime_role(Config.AGENT_NAME, Config.REGION)
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
    
    # 3. MCP Server 정보를 환경변수로 설정 (Cognito OAuth2 방식)
    env_vars = {
        "MCP_AGENT_ARN": mcp_server_info['agent_arn'],
        "MCP_CLIENT_ID": mcp_server_info['client_id'],
        "MCP_CLIENT_SECRET": mcp_server_info['client_secret'],
        "MCP_USER_POOL_ID": mcp_server_info['user_pool_id'],
        "AWS_REGION": mcp_server_info['region']
    }
    
    # 4. 배포 실행 (환경변수와 함께)
    print("🚀 Portfolio Architect 배포 중...")
    launch_result = agentcore_runtime.launch(auto_update_on_conflict=True, env_vars=env_vars)
    print("✅ Portfolio Architect 배포 시작 완료")
    
    # 5. 배포 상태 대기
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
        "agent_name": Config.AGENT_NAME,
        "agent_arn": portfolio_architect_info["agent_arn"],
        "agent_id": portfolio_architect_info["agent_id"],
        "region": portfolio_architect_info["region"],
        "mcp_server_arn": mcp_server_info["agent_arn"],
        "mcp_server_id": mcp_server_info["agent_id"],
        "mcp_client_id": mcp_server_info["client_id"],
        "mcp_user_pool_id": mcp_server_info["user_pool_id"],
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
    MCP Server가 이미 배포되어 있으면 재사용하고, 없으면 새로 배포합니다.
    
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
        
        # 1. MCP Server 정보 확인 및 배포
        try:
            # 기존 MCP Server 정보 로드 시도
            mcp_server_info = load_mcp_server_info()
            print("✅ 기존 MCP Server 정보 사용")
        except FileNotFoundError:
            # MCP Server가 없으면 새로 배포
            print("📋 MCP Server 배포 정보가 없습니다. 새로 배포합니다.")
            mcp_server_info = deploy_mcp_server()
        
        print("\n" + "=" * 50)
        print("🎉 MCP Server 준비 완료!")
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
        print("1. MCP Server 테스트: cd mcp_server && python test_remote.py")
        print("2. Streamlit 앱 실행: streamlit run app.py")
        print("3. 전체 시스템 테스트")
        
        return 0
        
    except Exception as e:
        print("=" * 70)
        print(f"❌ 배포 실패: {str(e)}")
        print("💡 문제 해결 방법:")
        print("1. AWS 권한 확인")
        print("2. 필수 파일 존재 확인")
        print("3. MCP Server 먼저 배포: cd mcp_server && python deploy_mcp.py")
        print("4. 로그 확인 후 재시도")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())