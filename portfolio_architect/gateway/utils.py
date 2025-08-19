"""
utils.py
Gateway 배포 전용 유틸리티 함수들

이 모듈은 AgentCore Gateway 배포에 필요한 AWS 리소스 생성 및 관리 함수들을 제공합니다.
주요 기능:
- IAM 역할 생성 및 관리
- Cognito 사용자 풀, 리소스 서버, 클라이언트 관리
- OAuth2 토큰 획득
"""

import boto3
import json
import time
import requests


def create_agentcore_gateway_role(gateway_name, region):
    """
    AgentCore Gateway용 IAM 역할 생성
    
    Gateway가 Lambda 함수를 호출하고 다른 AWS 서비스에 접근할 수 있도록
    필요한 권한을 가진 IAM 역할을 생성합니다.
    
    Args:
        gateway_name (str): 게이트웨이 이름 (역할명에 포함됨)
        region (str): AWS 리전
        
    Returns:
        dict: 생성된 IAM 역할 정보
        
    Note:
        - 기존 역할이 있으면 삭제 후 재생성
        - Bedrock AgentCore, Lambda 호출 등 필요한 모든 권한 포함
    """
    print("🔐 Gateway IAM 역할 생성 중...")
    
    iam_client = boto3.client('iam')
    agentcore_gateway_role_name = f'agentcore-gateway-{gateway_name}-role'
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    # Gateway가 사용할 수 있는 권한 정책
    role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "GatewayPermissions",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:*",              # Bedrock AgentCore 관련 모든 권한
                "bedrock:*",                        # Bedrock 관련 모든 권한
                "agent-credential-provider:*",      # 자격 증명 공급자 권한
                "iam:PassRole",                     # IAM 역할 전달 권한
                "secretsmanager:GetSecretValue",    # Secrets Manager 접근 권한
                "lambda:InvokeFunction"             # Lambda 함수 호출 권한 (중요!)
            ],
            "Resource": "*"
        }]
    }
    
    # Bedrock AgentCore 서비스가 이 역할을 사용할 수 있도록 하는 신뢰 정책
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AssumeRolePolicy",
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"  # AgentCore 서비스만 사용 가능
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": f"{account_id}"  # 현재 계정에서만 사용
                },
                "ArnLike": {
                    "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                }
            }
        }]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)
    role_policy_document = json.dumps(role_policy)
    
    try:
        # 새 IAM 역할 생성
        agentcore_gateway_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json,
            Description='AgentCore Gateway execution role for Lambda invocation and AWS service access'
        )
        print("✅ 새 IAM 역할 생성 완료")
        time.sleep(10)  # 역할 전파 대기
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        # 기존 역할이 있으면 삭제 후 재생성 (깔끔한 상태 보장)
        print("♻️ 기존 역할 삭제 후 재생성 중...")
        
        # 기존 인라인 정책들 삭제
        policies = iam_client.list_role_policies(
            RoleName=agentcore_gateway_role_name,
            MaxItems=100
        )
        
        for policy_name in policies['PolicyNames']:
            iam_client.delete_role_policy(
                RoleName=agentcore_gateway_role_name,
                PolicyName=policy_name
            )
        
        # 기존 역할 삭제
        iam_client.delete_role(RoleName=agentcore_gateway_role_name)
        
        # 새 역할 생성
        agentcore_gateway_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json,
            Description='AgentCore Gateway execution role for Lambda invocation and AWS service access'
        )
        print("✅ 역할 재생성 완료")

    # 권한 정책 연결
    try:
        iam_client.put_role_policy(
            PolicyDocument=role_policy_document,
            PolicyName="AgentCorePolicy",
            RoleName=agentcore_gateway_role_name
        )
        print("✅ 권한 정책 연결 완료")
    except Exception as e:
        print(f"⚠️ 정책 연결 오류: {e}")

    return agentcore_gateway_iam_role


def get_or_create_user_pool(cognito, user_pool_name, region):
    """
    Cognito 사용자 풀 조회 또는 생성
    
    OAuth2 인증을 위한 Cognito 사용자 풀을 생성하거나 기존 풀을 조회합니다.
    Gateway 인증에 사용됩니다.
    
    Args:
        cognito: Cognito 클라이언트
        user_pool_name (str): 사용자 풀 이름
        region (str): AWS 리전
    
    Returns:
        str: 사용자 풀 ID
        
    Note:
        - 기존 풀이 있으면 재사용
        - 새 풀 생성 시 도메인도 자동 생성
    """
    print("🔍 Cognito 사용자 풀 확인 중...")
    
    # 기존 사용자 풀 조회
    response = cognito.list_user_pools(MaxResults=60)
    for pool in response["UserPools"]:
        if pool["Name"] == user_pool_name:
            user_pool_id = pool["Id"]
            print(f"♻️ 기존 사용자 풀 사용: {user_pool_id}")
            
            # 도메인 정보 확인 (디버깅용)
            pool_info = cognito.describe_user_pool(UserPoolId=user_pool_id)
            domain = pool_info.get('UserPool', {}).get('Domain')
            if domain:
                pool_region = user_pool_id.split('_')[0] if '_' in user_pool_id else region
                domain_url = f"https://{domain}.auth.{pool_region}.amazoncognito.com"
                print(f"📍 도메인: {domain_url}")
            return user_pool_id
    
    # 새 사용자 풀 생성
    print("🆕 새 사용자 풀 생성 중...")
    created = cognito.create_user_pool(PoolName=user_pool_name)
    user_pool_id = created["UserPool"]["Id"]
    
    # 도메인 생성 (OAuth2 토큰 엔드포인트용)
    domain_prefix = user_pool_id.replace("_", "").lower()
    cognito.create_user_pool_domain(
        Domain=domain_prefix,
        UserPoolId=user_pool_id
    )
    print(f"✅ 사용자 풀 생성 완료: {user_pool_id}")
    print(f"📍 도메인 생성: {domain_prefix}")
    
    return user_pool_id


def get_or_create_resource_server(cognito, user_pool_id, resource_server_id, resource_server_name, scopes):
    """
    Cognito 리소스 서버 조회 또는 생성
    
    OAuth2 스코프를 정의하는 리소스 서버를 생성합니다.
    Gateway 접근 권한을 세분화하는 데 사용됩니다.
    
    Args:
        cognito: Cognito 클라이언트
        user_pool_id (str): Cognito 사용자 풀 ID
        resource_server_id (str): 리소스 서버 식별자
        resource_server_name (str): 리소스 서버 이름
        scopes (list): 스코프 목록 [{"ScopeName": "read", "ScopeDescription": "..."}]
    
    Returns:
        str: 리소스 서버 ID
        
    Note:
        - 기존 서버가 있으면 재사용
        - 스코프는 gateway:read, gateway:write 등으로 정의
    """
    print("🔍 리소스 서버 확인 중...")
    
    try:
        # 기존 리소스 서버 조회
        cognito.describe_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id
        )
        print(f"♻️ 기존 리소스 서버 사용: {resource_server_id}")
        return resource_server_id
        
    except cognito.exceptions.ResourceNotFoundException:
        # 새 리소스 서버 생성
        print("🆕 새 리소스 서버 생성 중...")
        cognito.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id,
            Name=resource_server_name,
            Scopes=scopes
        )
        print(f"✅ 리소스 서버 생성 완료: {resource_server_id}")
        return resource_server_id


def get_or_create_m2m_client(cognito, user_pool_id, client_name, resource_server_id):
    """
    Machine-to-Machine 클라이언트 조회 또는 생성
    
    서버 간 통신을 위한 OAuth2 클라이언트를 생성합니다.
    client_credentials 플로우를 사용하여 토큰을 획득합니다.
    
    Args:
        cognito: Cognito 클라이언트
        user_pool_id (str): 사용자 풀 ID
        client_name (str): 클라이언트 이름
        resource_server_id (str): 리소스 서버 ID
    
    Returns:
        tuple: (클라이언트 ID, 클라이언트 시크릿)
        
    Note:
        - 기존 클라이언트가 있으면 재사용
        - client_credentials 플로우만 허용
        - 지정된 스코프에만 접근 가능
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
    
    # 새 클라이언트 생성
    print("🆕 새 M2M 클라이언트 생성 중...")
    created = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,                          # 시크릿 자동 생성
        AllowedOAuthFlows=["client_credentials"],     # M2M 플로우만 허용
        AllowedOAuthScopes=[                          # 허용된 스코프
            f"{resource_server_id}/gateway:read", 
            f"{resource_server_id}/gateway:write"
        ],
        AllowedOAuthFlowsUserPoolClient=True,         # OAuth 플로우 활성화
        SupportedIdentityProviders=["COGNITO"],       # Cognito 인증만 사용
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"] # 리프레시 토큰 허용
    )
    
    client_id = created["UserPoolClient"]["ClientId"]
    client_secret = created["UserPoolClient"]["ClientSecret"]
    print(f"✅ M2M 클라이언트 생성 완료: {client_id}")
    
    return client_id, client_secret


def get_token(user_pool_id, client_id, client_secret, scope_string, region):
    """
    Cognito OAuth2 토큰 획득
    
    client_credentials 플로우를 사용하여 액세스 토큰을 획득합니다.
    Gateway 호출 시 Authorization 헤더에 사용됩니다.
    
    Args:
        user_pool_id (str): Cognito 사용자 풀 ID
        client_id (str): 클라이언트 ID
        client_secret (str): 클라이언트 시크릿
        scope_string (str): OAuth2 스코프 문자열 (공백으로 구분)
        region (str): AWS 리전
    
    Returns:
        dict: 토큰 정보 또는 오류 메시지
        
    Example:
        token_info = get_token(pool_id, client_id, secret, "server/gateway:read", "us-west-2")
        access_token = token_info["access_token"]
    """
    try:
        # Cognito 도메인 URL 구성 (언더스코어 제거 필요)
        user_pool_id_without_underscore = user_pool_id.replace("_", "")
        url = f"https://{user_pool_id_without_underscore}.auth.{region}.amazoncognito.com/oauth2/token"
        
        # OAuth2 토큰 요청
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",  # M2M 플로우
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope_string,
        }

        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as err:
        return {"error": str(err)}