"""
deploy_mcp.py
MCP Server 배포 스크립트

ETF 데이터 조회를 위한 MCP Server를 AWS Bedrock AgentCore Runtime에 배포합니다.
"""
import boto3
import sys
import os
import time
import json
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime

import sys
from pathlib import Path

# shared 모듈 경로 추가
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

# 공통 유틸리티 import
from cognito_utils import (
    get_or_create_user_pool,
    get_or_create_resource_server,
    get_or_create_m2m_client,
    get_token
)
from runtime_utils import (
    create_agentcore_runtime_role
)


# ================================
# 설정 상수
# ================================

class Config:
    """MCP Server 배포 설정 상수"""
    MCP_SERVER_NAME = "mcp_server"
    REGION = "us-west-2"
    MAX_DEPLOY_MINUTES = 15
    STATUS_CHECK_INTERVAL = 30

# ================================
# MCP Server 배포 함수들
# ================================

def deploy_mcp_server():
    """
    MCP Server 배포 메인 프로세스
    
    Returns:
        dict: 배포 결과 정보
    """
    print("🚀 MCP Server 배포 시작...")
    
    # 1. IAM 역할 생성
    iam_role = create_agentcore_runtime_role(Config.MCP_SERVER_NAME, Config.REGION)
    role_arn = iam_role['Role']['Arn']
    time.sleep(10)
    
    # 2. Cognito 인증 설정
    auth_components = _setup_cognito_authentication()
    
    # 3. MCP Server Runtime 생성
    runtime_result = _create_mcp_runtime(role_arn, auth_components)
    
    # 4. 배포 결과 구성
    result = {
        'agent_arn': runtime_result['agent_arn'],
        'agent_id': runtime_result['agent_id'],
        'user_pool_id': auth_components['user_pool_id'],
        'client_id': auth_components['client_id'],
        'client_secret': auth_components['client_secret'],
        'region': Config.REGION,
        'deployed_at': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print("✅ MCP Server 배포 완료!")
    return result

def _setup_cognito_authentication():
    """
    Cognito M2M 인증 구성 요소 설정 (risk_manager 패턴)
    
    Returns:
        dict: 인증 구성 요소
    """
    print("🔐 Cognito 인증 설정 중...")
    cognito = boto3.client('cognito-idp', region_name=Config.REGION)
    
    # 사용자 풀 생성/조회
    user_pool_id = get_or_create_user_pool(
        cognito, 
        f"{Config.MCP_SERVER_NAME}-pool", 
        Config.REGION
    )
    
    # 리소스 서버 생성/조회
    resource_server_id = f"{Config.MCP_SERVER_NAME}-server"
    resource_server_name = f"{Config.MCP_SERVER_NAME} Resource Server"
    scopes = [
        {"ScopeName": "runtime:read", "ScopeDescription": "Runtime read access"},
        {"ScopeName": "runtime:write", "ScopeDescription": "Runtime write access"}
    ]
    
    resource_server_id = get_or_create_resource_server(
        cognito, 
        user_pool_id, 
        resource_server_id, 
        resource_server_name, 
        scopes
    )
    
    # M2M 클라이언트 생성/조회
    client_id, client_secret = get_or_create_m2m_client(
        cognito,
        user_pool_id,
        f"{Config.MCP_SERVER_NAME}-client",
        resource_server_id,
        ["runtime:read", "runtime:write"]
    )
    
    # Discovery URL 구성
    discovery_url = f'https://cognito-idp.{Config.REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
    
    print("✅ Cognito 인증 설정 완료 (토큰은 런타임에서 동적 획득)")
    
    return {
        'user_pool_id': user_pool_id,
        'client_id': client_id,
        'client_secret': client_secret,
        'discovery_url': discovery_url
    }

def _create_mcp_runtime(role_arn, auth_components):
    """
    MCP Server Runtime 생성
    
    Args:
        role_arn (str): Runtime 실행용 IAM 역할 ARN
        auth_components (dict): Cognito 인증 구성 요소
        
    Returns:
        dict: 생성된 Runtime 정보
    """
    print("🔧 MCP Server Runtime 구성 중...")
    current_dir = Path(__file__).parent
    
    # JWT 인증 설정
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [auth_components['client_id']],
            "discoveryUrl": auth_components['discovery_url'],
        }
    }
    
    agentcore_runtime = Runtime()
    agentcore_runtime.configure(
        entrypoint=str(current_dir / "server.py"),
        execution_role=role_arn,
        auto_create_ecr=True,
        requirements_file=str(current_dir / "requirements.txt"),
        region=Config.REGION,
        authorizer_configuration=auth_config,
        protocol="MCP",
        agent_name=Config.MCP_SERVER_NAME
    )
    print("✅ MCP Server Runtime 구성 완료")
    
    # 배포 실행
    print("🚀 MCP Server 배포 중...")
    launch_result = agentcore_runtime.launch()
    print("✅ MCP Server 배포 시작 완료")
    
    # 배포 상태 대기
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
    
    print(f"✅ MCP Server Runtime 생성 완료: {launch_result.agent_id}")
    return {
        'agent_arn': launch_result.agent_arn,
        'agent_id': launch_result.agent_id
    }

# ================================
# 배포 정보 관리
# ================================

def save_deployment_info(result):
    """
    MCP Server 배포 정보를 JSON 파일로 저장
    
    Args:
        result (dict): 배포 결과 정보
        
    Returns:
        str: 저장된 JSON 파일 경로
    """
    current_dir = Path(__file__).parent
    info_file = current_dir / "mcp_deployment_info.json"
    
    with open(info_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"📄 배포 정보 저장: {info_file}")
    return str(info_file)

# ================================
# 메인 실행 함수
# ================================

def main():
    """
    메인 실행 함수
    
    ETF Data MCP Server의 전체 배포 프로세스를 관리합니다.
    """
    try:
        print("=" * 60)
        print("🚀 ETF Data MCP Server 배포 시작")
        print(f"📍 서버명: {Config.MCP_SERVER_NAME}")
        print(f"🌍 리전: {Config.REGION}")
        print("=" * 60)
        
        # MCP Server 배포 실행
        result = deploy_mcp_server()
        
        # 배포 정보 저장
        info_file = save_deployment_info(result)
        
        print("=" * 60)
        print("🎉 MCP Server 배포 성공!")
        print(f"🔗 Agent ARN: {result['agent_arn']}")
        print(f"📄 배포 정보: {info_file}")
        print("=" * 60)
        
        print("\n📋 다음 단계:")
        print("1. MCP Server 테스트: python test_remote.py")
        print("2. Portfolio Architect 배포: cd .. && python deploy.py")
        
        return result
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ MCP Server 배포 실패: {str(e)}")
        print("=" * 60)
        raise

if __name__ == "__main__":
    sys.exit(main())