"""
deploy.py
MCP Server 배포 스크립트

ETF 데이터 조회를 위한 MCP Server를 AWS Bedrock AgentCore Runtime에 배포합니다.
"""

import sys
import os
import time
import json
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime

# 공통 utils 모듈 import
utils_path = str(Path(__file__).parent.parent.parent)
sys.path.append(utils_path)
from utils import create_agentcore_role

# ================================
# 설정 상수
# ================================

class Config:
    """MCP Server 배포 설정 상수"""
    MCP_SERVER_NAME = "runtime_mcp_server"
    REGION = "us-west-2"
    MAX_DEPLOY_MINUTES = 15
    STATUS_CHECK_INTERVAL = 30

# ================================
# MCP Server 배포 함수들
# ================================

def deploy_mcp_server():
    """
    MCP Server 배포
    
    ETF 데이터 조회 도구를 제공하는 MCP Server를 AgentCore Runtime에 배포합니다.
    
    Returns:
        dict: MCP Server 배포 정보 (agent_arn, bearer_token 등)
    """
    print("🚀 MCP Server 배포 시작...")
    
    # 1. Cognito 인증 설정
    print("🔐 Cognito 인증 설정 중...")
    cognito_config = setup_cognito_user_pool()
    print("✅ Cognito 설정 완료")
    
    # 2. IAM 역할 생성
    print("🔐 IAM 역할 생성 중...")
    agentcore_iam_role = create_agentcore_role(agent_name=Config.MCP_SERVER_NAME)
    print("✅ IAM 역할 생성 완료")
    
    # 3. Runtime 구성
    print("🔧 MCP Server Runtime 구성 중...")
    current_dir = Path(__file__).parent
    
    agentcore_runtime = Runtime()
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [cognito_config['client_id']],
            "discoveryUrl": cognito_config['discovery_url'],
        }
    }
    
    agentcore_runtime.configure(
        entrypoint=str(current_dir / "server.py"),
        execution_role=agentcore_iam_role['Role']['Arn'],
        auto_create_ecr=True,
        requirements_file=str(current_dir / "requirements.txt"),
        region=Config.REGION,
        authorizer_configuration=auth_config,
        protocol="MCP",
        agent_name=Config.MCP_SERVER_NAME
    )
    print("✅ MCP Server Runtime 구성 완료")
    
    # 4. 배포 실행
    print("🚀 MCP Server 배포 중...")
    launch_result = agentcore_runtime.launch()
    print("✅ MCP Server 배포 시작 완료")
    
    # 5. 배포 상태 대기
    print("⏳ MCP Server 배포 상태 모니터링 중...")
    end_statuses = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
    max_checks = (Config.MAX_DEPLOY_MINUTES * 60) // Config.STATUS_CHECK_INTERVAL
    
    for i in range(max_checks):
        try:
            status_response = agentcore_runtime.status()
            status = status_response.endpoint['status']
            elapsed_time = (i + 1) * Config.STATUS_CHECK_INTERVAL
            print(f"📊 MCP Server 상태: {status} ({elapsed_time//60}분 {elapsed_time%60}초 경과)")
            
            if status in end_statuses:
                break
                
        except Exception as e:
            print(f"⚠️ 상태 확인 오류: {str(e)}")
            
        time.sleep(Config.STATUS_CHECK_INTERVAL)
    
    if status != 'READY':
        raise Exception(f"MCP Server 배포 실패: {status}")
    
    print("✅ MCP Server 배포 완료!")
    
    # 6. 배포 정보를 AWS에 저장
    print("📄 MCP Server 정보 AWS에 저장 중...")
    
    return {
        "agent_arn": launch_result.agent_arn,
        "agent_id": launch_result.agent_id,
        "bearer_token": cognito_config['bearer_token'],
        "region": Config.REGION
    }

# ================================
# 배포 정보 저장
# ================================

def save_deployment_info(mcp_server_info):
    """
    MCP Server 배포 정보 저장
    
    Args:
        mcp_server_info (dict): MCP Server 배포 정보
        
    Returns:
        str: 저장된 JSON 파일 경로
    """
    print("📄 MCP Server 배포 정보 저장 중...")
    
    current_dir = Path(__file__).parent
    deployment_info = {
        "agent_name": Config.MCP_SERVER_NAME,
        "agent_arn": mcp_server_info["agent_arn"],
        "agent_id": mcp_server_info["agent_id"],
        "bearer_token": mcp_server_info["bearer_token"],
        "region": mcp_server_info["region"],
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = current_dir / "mcp_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"✅ MCP Server 배포 정보 저장: {info_file}")
    return str(info_file)

# ================================
# 메인 실행 함수
# ================================

def main():
    """
    메인 배포 함수
    
    MCP Server를 AWS에 배포합니다.
    
    Returns:
        int: 성공 시 0, 실패 시 1
    """
    try:
        print("=" * 60)
        print("🚀 ETF Data MCP Server 배포")
        print(f"🌍 리전: {Config.REGION}")
        print(f"📍 서버명: {Config.MCP_SERVER_NAME}")
        print("=" * 60)
        
        # MCP Server 배포
        mcp_server_info = deploy_mcp_server()
        
        # 배포 정보 저장
        info_file = save_deployment_info(mcp_server_info)
        
        print("\n" + "=" * 60)
        print("🎉 MCP Server 배포 완료!")
        print(f"🔗 MCP Server ARN: {mcp_server_info['agent_arn']}")
        print(f"📄 배포 정보: {info_file}")
        print("=" * 60)
        
        print("\n📋 다음 단계:")
        print("1. MCP Server 테스트: python test_remote.py")
        print("2. Portfolio Architect 배포: cd .. && python deploy.py")
        
        return 0
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ MCP Server 배포 실패: {str(e)}")
        print("💡 문제 해결 방법:")
        print("1. AWS 권한 확인")
        print("2. 필수 파일 존재 확인")
        print("3. 로그 확인 후 재시도")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())