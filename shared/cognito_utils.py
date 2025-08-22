"""
cognito_utils.py
Cognito 인증 관련 공통 유틸리티 함수들

이 모듈은 AWS Cognito를 사용한 OAuth2 인증에 필요한 모든 함수들을 제공합니다.
- User Pool 관리
- Resource Server 관리  
- M2M Client 관리
- OAuth2 토큰 획득
"""

import boto3
import requests
import time


def get_or_create_user_pool(cognito, user_pool_name, region):
    """
    Cognito 사용자 풀 조회 또는 생성
    
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
    try:
        cognito.create_user_pool_domain(
            Domain=domain_prefix,
            UserPoolId=user_pool_id
        )
    except cognito.exceptions.InvalidParameterException:
        # 도메인이 이미 존재하는 경우 무시
        pass
    
    print(f"✅ 사용자 풀 생성 완료: {user_pool_id}")
    return user_pool_id


def get_or_create_resource_server(cognito, user_pool_id, resource_server_id, resource_server_name, scopes):
    """
    Cognito 리소스 서버 조회 또는 생성
    
    Args:
        cognito: Cognito 클라이언트
        user_pool_id (str): Cognito 사용자 풀 ID
        resource_server_id (str): 리소스 서버 식별자
        resource_server_name (str): 리소스 서버 이름
        scopes (list): 스코프 목록
    
    Returns:
        str: 리소스 서버 ID
    """
    print("🔍 리소스 서버 확인 중...")
    
    try:
        cognito.describe_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id
        )
        print(f"♻️ 기존 리소스 서버 사용: {resource_server_id}")
        return resource_server_id
        
    except cognito.exceptions.ResourceNotFoundException:
        print("🆕 새 리소스 서버 생성 중...")
        cognito.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id,
            Name=resource_server_name,
            Scopes=scopes
        )
        print(f"✅ 리소스 서버 생성 완료: {resource_server_id}")
        return resource_server_id


def get_or_create_m2m_client(cognito, user_pool_id, client_name, resource_server_id, scope_names=None):
    """
    Machine-to-Machine 클라이언트 조회 또는 생성
    
    Args:
        cognito: Cognito 클라이언트
        user_pool_id (str): 사용자 풀 ID
        client_name (str): 클라이언트 이름
        resource_server_id (str): 리소스 서버 ID
        scope_names (list): 스코프 이름 목록 (기본값: ["read", "write"])
    
    Returns:
        tuple: (클라이언트 ID, 클라이언트 시크릿)
    """
    print("🔍 M2M 클라이언트 확인 중...")
    
    if scope_names is None:
        scope_names = ["read", "write"]
    
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
    
    # 스코프 문자열 생성
    oauth_scopes = [f"{resource_server_id}/{scope}" for scope in scope_names]
    
    # 새 M2M 클라이언트 생성
    print("🆕 새 M2M 클라이언트 생성 중...")
    created = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=oauth_scopes,
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"]
    )
    
    client_id = created["UserPoolClient"]["ClientId"]
    client_secret = created["UserPoolClient"]["ClientSecret"]
    print(f"✅ M2M 클라이언트 생성 완료: {client_id}")
    
    return client_id, client_secret


def get_token(user_pool_id, client_id, client_secret, scope_string, region):
    """
    Cognito OAuth2 토큰 획득
    
    Args:
        user_pool_id (str): Cognito 사용자 풀 ID
        client_id (str): 클라이언트 ID
        client_secret (str): 클라이언트 시크릿
        scope_string (str): OAuth2 스코프 문자열
        region (str): AWS 리전
    
    Returns:
        dict: 토큰 정보 또는 오류 메시지
    """
    try:
        # User Pool ID에서 도메인 생성 (get_or_create_user_pool과 동일한 방식)
        domain_prefix = user_pool_id.replace("_", "").lower()
        url = f"https://{domain_prefix}.auth.{region}.amazoncognito.com/oauth2/token"
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope_string,
        }

        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as err:
        return {"error": str(err)}