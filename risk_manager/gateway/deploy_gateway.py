"""
deploy_gateway.py
Risk Manager Gateway 배포 스크립트

이 스크립트는 Risk Manager를 위한 AgentCore Gateway를 배포합니다.
Lambda 함수와 AI 에이전트 간의 MCP(Model Context Protocol) 통신을 중개하여
실시간 뉴스 및 거시경제 데이터 조회 기능을 제공합니다.

주요 기능:
- Lambda 함수를 MCP 도구로 노출
- Cognito OAuth2 인증 설정  
- Gateway Target 구성 (뉴스 및 시장 데이터 조회 도구들)
- 자동 Lambda ARN 로드 및 설정
"""

import boto3
import time
import json
from pathlib import Path
import copy
from target_config import TARGET_CONFIGURATION
from utils import (
    create_agentcore_gateway_role,
    get_or_create_resource_server,
    get_or_create_user_pool,
    get_or_create_m2m_client
)

# ================================
# 설정 상수
# ================================

class Config:
    """Gateway 배포 설정 상수"""
    GATEWAY_NAME = "gateway-risk-manager"
    REGION = "us-west-2"
    TARGET_NAME = "target-risk-manager"

# ================================
# 유틸리티 함수들
# ================================

def load_lambda_info():
    """
    Lambda 배포 정보 JSON 파일에서 Lambda ARN 로드
    
    Returns:
        str: Lambda 함수 ARN
        
    Raises:
        FileNotFoundError: Lambda 배포 정보 파일이 없을 때
        KeyError: JSON에서 function_arn 키를 찾을 수 없을 때
    """
    lambda_dir = Path(__file__).parent.parent / "lambda"
    info_file = lambda_dir / "lambda_deployment_info.json"
    
    if not info_file.exists():
        raise FileNotFoundError(
            f"Lambda 배포 정보 파일을 찾을 수 없습니다: {info_file}\n"
            "먼저 'python lambda/deploy_lambda.py'를 실행하세요."
        )
    
    with open(info_file, 'r') as f:
        lambda_info = json.load(f)
    
    lambda_arn = lambda_info.get('function_arn')
    if not lambda_arn:
        raise KeyError("Lambda 배포 정보에서 function_arn을 찾을 수 없습니다.")
    
    print(f"📋 Lambda ARN 로드: {lambda_arn}")
    return lambda_arn

def delete_existing_gateway(gateway_name, region):
    """
    기존 Gateway 삭제 (Target들 먼저 삭제)
    
    Args:
        gateway_name (str): 삭제할 Gateway 이름
        region (str): AWS 리전
    """
    try:
        print("🔍 기존 Gateway 확인 중...")
        gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
        gateways = gateway_client.list_gateways().get('items', [])

        for gw in gateways:
            if gw['name'] == gateway_name:
                gateway_id = gw['gatewayId']
                print(f"🗑️ 기존 Gateway 삭제 중: {gateway_id}")
                
                # Target들 먼저 삭제
                targets = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id).get('items', [])
                for target in targets:
                    print(f"🗑️ Target 삭제 중: {target['targetId']}")
                    gateway_client.delete_gateway_target(
                        gatewayIdentifier=gateway_id,
                        targetId=target['targetId']
                    )
                
                time.sleep(3)
                
                # Gateway 삭제
                gateway_client.delete_gateway(gatewayIdentifier=gateway_id)
                print("✅ 기존 Gateway 삭제 완료")
                time.sleep(3)
                break
        else:
            print("ℹ️ 삭제할 기존 Gateway 없음")
                
    except Exception as e:
        print(f"⚠️ Gateway 삭제 중 오류 (무시하고 진행): {str(e)}")
        pass

# ================================
# 메인 배포 함수
# ================================

def deploy_gateway():
    """
    Gateway 배포 메인 프로세스
    
    Returns:
        dict: 배포 결과 정보
    """
    print("🚀 Gateway 배포 시작...")
    
    # 1. Lambda ARN 자동 로드
    lambda_arn = load_lambda_info()
    
    # 2. 기존 Gateway 정리
    delete_existing_gateway(Config.GATEWAY_NAME, Config.REGION)

    # 3. IAM 역할 생성
    iam_role = create_agentcore_gateway_role(Config.GATEWAY_NAME, Config.REGION)
    role_arn = iam_role['Role']['Arn']
    time.sleep(10)
    
    # 4. Cognito 인증 설정
    auth_components = _setup_cognito_authentication()
    
    # 5. Gateway 생성
    gateway = _create_gateway(role_arn, auth_components)
    
    # 6. Gateway Target 생성
    target = _create_gateway_target(gateway['gatewayId'], lambda_arn)
    
    # 7. 배포 결과 구성
    result = {
        'lambda_arn': lambda_arn,
        'role_arn': role_arn,
        'user_pool_id': auth_components['user_pool_id'],
        'client_id': auth_components['client_id'],
        'client_secret': auth_components['client_secret'],
        'gateway_id': gateway['gatewayId'],
        'gateway_url': gateway['gatewayUrl'],
        'target_id': target['targetId'],
        'region': Config.REGION,
        'deployed_at': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print("✅ Gateway 배포 완료!")
    print(f"🌐 Gateway URL: {gateway['gatewayUrl']}")
    return result

def _setup_cognito_authentication():
    """
    Cognito OAuth2 인증 구성 요소 설정
    
    Returns:
        dict: 인증 구성 요소
    """
    print("🔐 Cognito 인증 설정 중...")
    cognito = boto3.client('cognito-idp', region_name=Config.REGION)
    
    # 사용자 풀 생성/조회
    user_pool_id = get_or_create_user_pool(
        cognito, 
        f"{Config.GATEWAY_NAME}-pool", 
        Config.REGION
    )
    
    # 리소스 서버 생성/조회
    resource_server_id = f"{Config.GATEWAY_NAME}-server"
    resource_server_name = f"{Config.GATEWAY_NAME} Resource Server"
    scopes = [
        {"ScopeName": "gateway:read", "ScopeDescription": "Gateway read access"},
        {"ScopeName": "gateway:write", "ScopeDescription": "Gateway write access"}
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
        f"{Config.GATEWAY_NAME}-client",
        resource_server_id
    )
    
    return {
        'user_pool_id': user_pool_id,
        'client_id': client_id,
        'client_secret': client_secret
    }

def _create_gateway(role_arn, auth_components):
    """
    AgentCore Gateway 생성
    
    Args:
        role_arn (str): Gateway 실행용 IAM 역할 ARN
        auth_components (dict): Cognito 인증 구성 요소
        
    Returns:
        dict: 생성된 Gateway 정보
    """
    print("🌉 Gateway 생성 중...")
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=Config.REGION)
    
    # JWT 인증 설정
    auth_config = {
        'customJWTAuthorizer': {
            'allowedClients': [auth_components['client_id']],
            'discoveryUrl': f'https://cognito-idp.{Config.REGION}.amazonaws.com/{auth_components["user_pool_id"]}/.well-known/openid-configuration'
        }
    }
    
    gateway = gateway_client.create_gateway(
        name=Config.GATEWAY_NAME,
        roleArn=role_arn,
        protocolType='MCP',
        authorizerType='CUSTOM_JWT',
        authorizerConfiguration=auth_config,
        description='Risk Manager Gateway - News and market data analysis for portfolio risk management'
    )
    
    print(f"✅ Gateway 생성 완료: {gateway['gatewayId']}")
    return gateway

def _create_gateway_target(gateway_id, lambda_arn):
    """
    Gateway Target 생성 (Lambda 함수를 MCP 도구로 노출)
    
    Args:
        gateway_id (str): Gateway ID
        lambda_arn (str): Lambda 함수 ARN
        
    Returns:
        dict: 생성된 Target 정보
    """
    print("🎯 Gateway Target 생성 중...")
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=Config.REGION)
    
    # Target 설정 로드 및 Lambda ARN 주입
    target_config = copy.deepcopy(TARGET_CONFIGURATION)
    target_config['mcp']['lambda']['lambdaArn'] = lambda_arn
    
    tool_count = len(target_config["mcp"]["lambda"]["toolSchema"]["inlinePayload"])
    print(f"📋 Target 설정: {tool_count}개 도구 구성")
    
    # Gateway Target 생성
    target = gateway_client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name=Config.TARGET_NAME,
        targetConfiguration=target_config,
        credentialProviderConfigurations=[{
            'credentialProviderType': 'GATEWAY_IAM_ROLE'
        }]
    )
    
    print(f"✅ Gateway Target 생성 완료: {target['targetId']}")
    return target

# ================================
# 배포 정보 관리
# ================================

def save_deployment_info(result):
    """
    Gateway 배포 정보를 JSON 파일로 저장
    
    Args:
        result (dict): 배포 결과 정보
        
    Returns:
        str: 저장된 JSON 파일 경로
    """
    current_dir = Path(__file__).parent
    info_file = current_dir / "gateway_deployment_info.json"
    
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
    
    Risk Manager Gateway의 전체 배포 프로세스를 관리합니다.
    """
    try:
        print("=" * 60)
        print("🌉 Risk Manager Gateway 배포 시작")
        print(f"📍 Gateway명: {Config.GATEWAY_NAME}")
        print(f"🌍 리전: {Config.REGION}")
        print("=" * 60)
        
        # Gateway 배포 실행
        result = deploy_gateway()
        
        # 배포 정보 저장
        info_file = save_deployment_info(result)
        
        print("=" * 60)
        print("🎉 Gateway 배포 성공!")
        print(f"🌐 Gateway URL: {result['gateway_url']}")
        print(f"🔑 Client ID: {result['client_id']}")
        print(f"📄 배포 정보: {info_file}")
        print("=" * 60)
        
        print("\n📋 다음 단계:")
        print("1. Runtime 배포: python deploy.py")
        print("2. 또는 직접 테스트: python test.py")
        
        return result
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ Gateway 배포 실패: {str(e)}")
        print("=" * 60)
        raise

if __name__ == "__main__":
    main()