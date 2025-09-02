"""
deploy.py

Portfolio Architect 배포 스크립트
MCP Server와 Portfolio Architect Runtime 순차 배포
"""

import sys
import os
import time
import json
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime

# shared 모듈 경로 추가
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))
from runtime_utils import create_agentcore_runtime_role

class Config:
    """Portfolio Architect 배포 설정"""
    REGION = "us-west-2"
    AGENT_NAME = "portfolio_architect"

def load_mcp_info():
    """MCP Server 배포 정보 로드"""
    info_file = Path(__file__).parent / "mcp_server" / "mcp_deployment_info.json"
    if not info_file.exists():
        print("❌ MCP Server 배포 정보가 없습니다.")
        print("💡 먼저 다음 명령을 실행하세요:")
        print("   cd mcp_server")
        print("   python deploy_mcp.py")
        raise FileNotFoundError("MCP Server를 먼저 배포해주세요.")
    
    with open(info_file) as f:
        return json.load(f)

def deploy_portfolio_architect(mcp_info):
    """Portfolio Architect Runtime 배포"""
    print("🎯 Portfolio Architect 배포 중...")
    
    # IAM 역할 생성
    iam_role = create_agentcore_runtime_role(Config.AGENT_NAME, Config.REGION)
    iam_role_name = iam_role['Role']['RoleName']
    
    # Runtime 구성
    current_dir = Path(__file__).parent
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / "portfolio_architect.py"),
        execution_role=iam_role['Role']['Arn'],
        auto_create_ecr=True,
        requirements_file=str(current_dir / "requirements.txt"),
        region=Config.REGION,
        agent_name=Config.AGENT_NAME
    )
    
    # 환경변수 설정
    env_vars = {
        "MCP_AGENT_ARN": mcp_info['agent_arn'],
        "MCP_CLIENT_ID": mcp_info['client_id'],
        "MCP_CLIENT_SECRET": mcp_info['client_secret'],
        "MCP_USER_POOL_ID": mcp_info['user_pool_id'],
        "AWS_REGION": Config.REGION
    }
    
    # 배포 실행
    launch_result = runtime.launch(auto_update_on_conflict=True, env_vars=env_vars)
    
    # 배포 완료 대기
    for i in range(30):  # 최대 15분 대기
        try:
            status = runtime.status().endpoint['status']
            print(f"📊 상태: {status} ({i*30}초 경과)")
            if status in ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']:
                break
        except Exception as e:
            print(f"⚠️ 상태 확인 오류: {e}")
        time.sleep(30)
    
    if status != 'READY':
        raise Exception(f"배포 실패: {status}")
    
    # ECR 리포지토리 이름 추출
    ecr_repo_name = None
    if hasattr(launch_result, 'ecr_uri') and launch_result.ecr_uri:
        ecr_repo_name = launch_result.ecr_uri.split('/')[-1].split(':')[0]
    
    return {
        "agent_arn": launch_result.agent_arn,
        "agent_id": launch_result.agent_id,
        "region": Config.REGION,
        "iam_role_name": iam_role_name,
        "ecr_repo_name": ecr_repo_name
    }

def save_deployment_info(mcp_info, architect_info):
    """배포 정보 저장"""
    deployment_info = {
        "agent_name": Config.AGENT_NAME,
        "agent_arn": architect_info["agent_arn"],
        "agent_id": architect_info["agent_id"],
        "region": Config.REGION,
        "iam_role_name": architect_info["iam_role_name"],
        "ecr_repo_name": architect_info.get("ecr_repo_name"),
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = Path(__file__).parent / "deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    return str(info_file)

def main():
    try:
        print("🎯 Portfolio Architect 전체 시스템 배포")
        
        # MCP Server 정보 로드 (필수)
        mcp_info = load_mcp_info()
        print("✅ MCP Server 정보 로드 완료")
        
        # Portfolio Architect 배포
        architect_info = deploy_portfolio_architect(mcp_info)
        
        # 배포 정보 저장
        info_file = save_deployment_info(mcp_info, architect_info)
        
        print(f"\n🎉 배포 완료!")
        print(f"📄 배포 정보: {info_file}")
        print(f"🔗 Portfolio Architect ARN: {architect_info['agent_arn']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 배포 실패: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())