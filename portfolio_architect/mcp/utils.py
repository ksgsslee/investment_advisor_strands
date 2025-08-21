"""
utils.py
MCP Server 배포 전용 유틸리티 함수들

이 모듈은 MCP Server 배포에 필요한 Cognito 설정 함수들을 제공합니다.
risk_manager의 utils 함수들을 MCP Server용으로 적용한 버전입니다.

주요 기능:
- Cognito 사용자 풀, M2M 클라이언트 관리 (risk_manager 패턴)
- OAuth 2.0 client_credentials를 통한 Bearer 토큰 획득
"""

import boto3
import requests





def get_or_create_user_pool(cognito, user_pool_name, region):
    """
    Cognito 사용자 풀 조회 또는 생성 (risk_manager 패턴)
    
    Args:
        cognito: Cognito 클라이언트
        user_pool_name (str): 사용자 풀 이름
        region (str): AWS 리전
    
    Returns:
        str: 사용자 풀 ID
    """
    print("🔍 Cognito 사용자 풀 확인 중...")
    
    # 기존 사용자 풀 조회
    response = cognito.list_user_pools(MaxResults=60)
    for pool in response["UserPools"]:
        if pool["Name"] == user_pool_name:
            user_pool_id = pool["Id"]
            print(f"♻️ 기존 사용자 풀 사용: {user_pool_id}")
            return user_pool_id
    
    # 새 사용자 풀 생성
    print("🆕 새 사용자 풀 생성 중...")
    created = cognito.create_user_pool(PoolName=user_pool_name)
    user_pool_id = created["UserPool"]["Id"]
    
    # 도메인 생성
    domain_prefix = user_pool_id.replace("_", "").lower()
    cognito.create_user_pool_domain(
        Domain=domain_prefix,
        UserPoolId=user_pool_id
    )
    print(f"✅ 사용자 풀 생성 완료: {user_pool_id}")
    
    return user_pool_id


def get_or_create_m2m_client(cognito, user_pool_id, client_name):
    """
    Machine-to-Machine 클라이언트 조회 또는 생성 (MCP Server용 - 스코프 없음)
    
    Args:
        cognito: Cognito 클라이언트
        user_pool_id (str): 사용자 풀 ID
        client_name (str): 클라이언트 이름
    
    Returns:
        tuple: (클라이언트 ID, 클라이언트 시크릿)
    """
    print("🔍 M2M 클라이언트 확인 중...")
    
    # 기존 클라이언트 조회
    response = cognito.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=60)
    for client in response["UserPoolClients"]:
        if client["ClientName"] == client_name:
            describe = cognito.describe_user_pool_client(
                UserPoolId=user_pool_id, 
                ClientId=client["ClientId"]
            )
            client_id = client["ClientId"]
            client_secret = describe["UserPoolClient"]["ClientSecret"]
            print(f"♻️ 기존 M2M 클라이언트 사용: {client_id}")
            return client_id, client_secret
    
    # 새 클라이언트 생성 (스코프 없는 M2M)
    print("🆕 새 M2M 클라이언트 생성 중...")
    created = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"]
        # AllowedOAuthScopes 없음 = 기본 권한만 사용 (스코프 없는 M2M)
    )
    
    client_id = created["UserPoolClient"]["ClientId"]
    client_secret = created["UserPoolClient"]["ClientSecret"]
    print(f"✅ M2M 클라이언트 생성 완료: {client_id}")
    
    return client_id, client_secret


def get_token(user_pool_id, client_id, client_secret, region):
    """
    Cognito OAuth2 토큰 획득 (risk_manager 패턴 - 스코프 없는 M2M)
    
    Args:
        user_pool_id (str): Cognito 사용자 풀 ID
        client_id (str): 클라이언트 ID
        client_secret (str): 클라이언트 시크릿
        region (str): AWS 리전
    
    Returns:
        dict: 토큰 정보 또는 오류 메시지
    """
    try:
        user_pool_id_without_underscore = user_pool_id.replace("_", "")
        url = f"https://{user_pool_id_without_underscore}.auth.{region}.amazoncognito.com/oauth2/token"
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
            # scope 없음 = 기본 권한만 사용
        }

        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as err:
        return {"error": str(err)}