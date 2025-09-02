"""
deploy_mcp.py

MCP Server 배포 스크립트
ETF 데이터 조회용 MCP Server 배포
"""

import boto3
import sys
import time
import json
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime

# shared 모듈 경로 추가
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))
from cognito_utils import get_or_create_user_pool, get_or_create_resource_server, get_or_create_m2m_client
from runtime_utils import create_agentcore_runtime_role

class Config:
    """MCP Server 배포 설정"""
    REGION = "us-west-2"
    MCP_SERVER_NAME = "mcp_server"

def setup_cognito_auth():
    """Cognito 인증 설정"""
    print("🔐 Cognito 인증 설정 중...")
    cognito = boto3.client('cognito-idp', region_name=Config.REGION)
    
    # User Pool 생성/조회
    user_pool_id = get_or_create_user_pool(cognito, f"{Config.MCP_SERVER_NAME}-pool", Config.REGION)
    
    # Resource Server 생성/조회
    resource_server_id = f"{Config.MCP_SERVER_NAME}-server"
    scopes = [
        {"ScopeName": "runtime:read", "ScopeDescription": "Runtime read access"},
        {"ScopeName": "runtime:write", "ScopeDescription": "Runtime write access"}
    ]
    get_or_create_resource_server(cognito, user_pool_id, resource_server_id, 
                                 f"{Config.MCP_SERVER_NAME} Resource Server", scopes)
    
    # M2M Client 생성/조회
    client_id, client_secret = get_or_create_m2m_client(
        cognito, user_pool_id, f"{Config.MCP_SERVER_NAME}-client", 
        resource_server_id, ["runtime:read", "runtime:write"]
    )
    
    discovery_url = f'https://cognito-idp.{Config.REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
    
    return {
        'user_pool_id': user_pool_id,
        'client_id': client_id,
        'client_secret': client_secret,
        'discovery_url': discovery_url
    }

def create_mcp_runtime(role_arn, auth_components):
    """MCP Server Runtime 생성"""
    print("🔧 MCP Server Runtime 구성 중...")
    current_dir = Path(__file__).parent
    
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [auth_components['client_id']],
            "discoveryUrl": auth_components['discovery_url'],
        }
    }
    
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / "server.py"),
        execution_role=role_arn,
        auto_create_ecr=True,
        requirements_file=str(current_dir / "requirements.txt"),
        region=Config.REGION,
        authorizer_configuration=auth_config,
        protocol="MCP",
        agent_name=Config.MCP_SERVER_NAME
    )
    
    # 배포 실행
    launch_result = runtime.launch()
    
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
        raise Exception(f"MCP Server 배포 실패: {status}")
    
    return {
        'agent_arn': launch_result.agent_arn,
        'agent_id': launch_result.agent_id
    }

def save_deployment_info(result):
    """배포 정보 저장"""
    info_file = Path(__file__).parent / "mcp_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(result, f, indent=2)
    return str(info_file)

def main():
    try:
        print("🚀 ETF Data MCP Server 배포")
        
        # IAM 역할 생성
        iam_role = create_agentcore_runtime_role(Config.MCP_SERVER_NAME, Config.REGION)
        iam_role_name = iam_role['Role']['RoleName']
        time.sleep(10)  # IAM 전파 대기
        
        # Cognito 인증 설정
        auth_components = setup_cognito_auth()
        
        # MCP Server Runtime 생성
        runtime_result = create_mcp_runtime(iam_role['Role']['Arn'], auth_components)
        
        # ECR 리포지토리 이름 추출
        ecr_repo_name = None
        if hasattr(runtime_result, 'ecr_uri') and runtime_result['ecr_uri']:
            ecr_repo_name = runtime_result['ecr_uri'].split('/')[-1].split(':')[0]

        # 배포 결과 구성
        result = {
            'agent_arn': runtime_result['agent_arn'],
            'agent_id': runtime_result['agent_id'],
            'user_pool_id': auth_components['user_pool_id'],
            'client_id': auth_components['client_id'],
            'client_secret': auth_components['client_secret'],
            'region': Config.REGION,
            'iam_role_name': iam_role_name,
            'ecr_repo_name': ecr_repo_name,
            'deployed_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 배포 정보 저장
        info_file = save_deployment_info(result)
        
        print(f"\n🎉 MCP Server 배포 완료!")
        print(f"🔗 Agent ARN: {result['agent_arn']}")
        print(f"📄 배포 정보: {info_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ MCP Server 배포 실패: {e}")
        raise

if __name__ == "__main__":
    main()