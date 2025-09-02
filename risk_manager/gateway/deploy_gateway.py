"""
deploy_gateway.py

Risk Manager Gateway 배포 스크립트
Lambda 함수와 AI 에이전트 간의 MCP 통신을 중개합니다.
"""

import boto3
import time
import json
import copy
import sys
from pathlib import Path
from target_config import TARGET_CONFIGURATION

# shared 모듈 경로 추가
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))
from cognito_utils import get_or_create_user_pool, get_or_create_resource_server, get_or_create_m2m_client
from gateway_utils import create_agentcore_gateway_role, create_gateway, create_gateway_target

class Config:
    """Gateway 배포 설정"""
    REGION = "us-west-2"
    GATEWAY_NAME = "gateway-risk-manager"
    TARGET_NAME = "target-risk-manager"

def load_lambda_info():
    """Lambda 배포 정보 로드"""
    info_file = Path(__file__).parent.parent / "lambda" / "lambda_deployment_info.json"
    
    if not info_file.exists():
        raise FileNotFoundError("Lambda 배포 정보를 찾을 수 없습니다. 먼저 Lambda를 배포하세요.")
    
    with open(info_file, 'r') as f:
        lambda_info = json.load(f)
    
    lambda_arn = lambda_info.get('function_arn')
    if not lambda_arn:
        raise KeyError("Lambda ARN을 찾을 수 없습니다.")
    
    return lambda_arn

def cleanup_existing_gateway():
    """기존 Gateway 정리"""
    try:
        print("🔍 기존 Gateway 확인 중...")
        gateway_client = boto3.client('bedrock-agentcore-control', region_name=Config.REGION)
        gateways = gateway_client.list_gateways().get('items', [])

        for gw in gateways:
            if gw['name'] == Config.GATEWAY_NAME:
                gateway_id = gw['gatewayId']
                print(f"🗑️ 기존 Gateway 삭제 중: {gateway_id}")
                
                # Target들 먼저 삭제
                targets = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id).get('items', [])
                for target in targets:
                    gateway_client.delete_gateway_target(
                        gatewayIdentifier=gateway_id,
                        targetId=target['targetId']
                    )
                
                time.sleep(3)
                gateway_client.delete_gateway(gatewayIdentifier=gateway_id)
                time.sleep(3)
                break
                
    except Exception as e:
        print(f"⚠️ Gateway 정리 중 오류 (무시하고 진행): {str(e)}")
        pass

def setup_cognito_auth():
    """Cognito 인증 설정"""
    print("🔐 Cognito 인증 설정 중...")
    cognito = boto3.client('cognito-idp', region_name=Config.REGION)
    
    # User Pool 생성/조회
    user_pool_id = get_or_create_user_pool(cognito, f"{Config.GATEWAY_NAME}-pool", Config.REGION)
    
    # Resource Server 생성/조회
    resource_server_id = f"{Config.GATEWAY_NAME}-server"
    scopes = [
        {"ScopeName": "gateway:read", "ScopeDescription": "Gateway read access"},
        {"ScopeName": "gateway:write", "ScopeDescription": "Gateway write access"}
    ]
    get_or_create_resource_server(cognito, user_pool_id, resource_server_id, 
                                 f"{Config.GATEWAY_NAME} Resource Server", scopes)
    
    # M2M Client 생성/조회
    client_id, client_secret = get_or_create_m2m_client(
        cognito, user_pool_id, f"{Config.GATEWAY_NAME}-client", 
        resource_server_id, ["gateway:read", "gateway:write"]
    )
    
    discovery_url = f'https://cognito-idp.{Config.REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
    
    return {
        'user_pool_id': user_pool_id,
        'client_id': client_id,
        'client_secret': client_secret,
        'discovery_url': discovery_url
    }

def create_gateway_runtime(role_arn, auth_components, lambda_arn):
    """Gateway Runtime 생성"""
    print("� CGateway Runtime 구성 중...")
    
    # Gateway 생성
    gateway = create_gateway(Config.GATEWAY_NAME, role_arn, auth_components, Config.REGION)
    
    # Gateway Target 생성 (Lambda 함수를 MCP 도구로 노출)
    target_config = copy.deepcopy(TARGET_CONFIGURATION)
    target_config['mcp']['lambda']['lambdaArn'] = lambda_arn
    target = create_gateway_target(gateway['gatewayId'], Config.TARGET_NAME, target_config, Config.REGION)
    
    return {
        'gateway_id': gateway['gatewayId'],
        'gateway_url': gateway['gatewayUrl'],
        'target_id': target['targetId']
    }

def save_deployment_info(result):
    """배포 정보 저장"""
    info_file = Path(__file__).parent / "gateway_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(result, f, indent=2)
    return str(info_file)

def main():
    try:
        print("🚀 Risk Manager Gateway 배포")
        
        # Lambda ARN 로드
        lambda_arn = load_lambda_info()
        
        # 기존 Gateway 정리
        cleanup_existing_gateway()
        
        # IAM 역할 생성
        iam_role = create_agentcore_gateway_role(Config.GATEWAY_NAME, Config.REGION)
        iam_role_name = iam_role['Role']['RoleName']
        time.sleep(10)  # IAM 전파 대기
        
        # Cognito 인증 설정
        auth_components = setup_cognito_auth()
        
        # Gateway Runtime 생성
        runtime_result = create_gateway_runtime(iam_role['Role']['Arn'], auth_components, lambda_arn)
        
        # 배포 결과 구성
        result = {
            'lambda_arn': lambda_arn,
            'gateway_id': runtime_result['gateway_id'],
            'gateway_url': runtime_result['gateway_url'],
            'target_id': runtime_result['target_id'],
            'user_pool_id': auth_components['user_pool_id'],
            'client_id': auth_components['client_id'],
            'client_secret': auth_components['client_secret'],
            'region': Config.REGION,
            'iam_role_name': iam_role_name,
            'deployed_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 배포 정보 저장
        info_file = save_deployment_info(result)
        
        print(f"\n🎉 Gateway 배포 완료!")
        print(f"🌐 Gateway URL: {result['gateway_url']}")
        print(f"📄 배포 정보: {info_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Gateway 배포 실패: {e}")
        raise

if __name__ == "__main__":
    main()