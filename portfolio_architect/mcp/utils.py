"""
utils.py
MCP Server 배포 전용 유틸리티 함수들

이 모듈은 MCP Server 배포에 필요한 모든 함수들을 제공합니다.
- IAM 역할 생성
- Cognito 설정
- OAuth 2.0 토큰 획득
"""

import boto3
import requests
import json
import time


def create_agentcore_role(agent_name, region):
    """
    AgentCore Runtime용 IAM 역할 생성
    
    Args:
        agent_name (str): 에이전트 이름
        region (str): AWS 리전
        
    Returns:
        dict: 생성된 IAM 역할 정보
    """
    iam_client = boto3.client('iam')
    agentcore_role_name = f'agentcore-runtime-{agent_name}-role'
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    # Runtime 실행에 필요한 권한 정책
    role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BedrockPermissions",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": "*"
            },
            {
                "Sid": "ECRImageAccess",
                "Effect": "Allow",
                "Action": [
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:GetAuthorizationToken"
                ],
                "Resource": [
                    f"arn:aws:ecr:{region}:{account_id}:repository/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogStreams",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups"
                ],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*",
                    f"arn:aws:logs:{region}:{account_id}:log-group:*"
                ]
            },
            {
                "Sid": "ECRTokenAccess",
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken"
                ],
                "Resource": "*"
            }
        ]
    }
    
    # AgentCore 서비스가 이 역할을 사용할 수 있도록 하는 신뢰 정책
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AssumeRolePolicy",
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": f"{account_id}"
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                    }
                }
            }
        ]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)
    role_policy_document = json.dumps(role_policy)
    
    try:
        # 새 IAM 역할 생성
        agentcore_iam_role = iam_client.create_role(
            RoleName=agentcore_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json,
            Description=f'AgentCore Runtime execution role for {agent_name}'
        )
        time.sleep(10)  # 역할 전파 대기
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        # 기존 역할 삭제 후 재생성
        print(f"기존 역할 삭제 후 재생성: {agentcore_role_name}")
        
        # 기존 인라인 정책들 삭제
        policies = iam_client.list_role_policies(
            RoleName=agentcore_role_name,
            MaxItems=100
        )
        
        for policy_name in policies['PolicyNames']:
            iam_client.delete_role_policy(
                RoleName=agentcore_role_name,
                PolicyName=policy_name
            )
        
        # 기존 역할 삭제
        iam_client.delete_role(RoleName=agentcore_role_name)
        
        # 새 역할 생성
        agentcore_iam_role = iam_client.create_role(
            RoleName=agentcore_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json,
            Description=f'AgentCore Runtime execution role for {agent_name}'
        )

    # 권한 정책 연결
    try:
        iam_client.put_role_policy(
            PolicyDocument=role_policy_document,
            PolicyName="AgentCorePolicy",
            RoleName=agentcore_role_name
        )
    except Exception as e:
        print(f"정책 연결 오류: {e}")

    return agentcore_iam_role


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
    Machine-to-Machine 클라이언트 조회 또는 생성 (OAuth2 Client Credentials)
    
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
    
    # 새 M2M 클라이언트 생성 (OAuth2 Client Credentials)
    print("🆕 새 M2M 클라이언트 생성 중...")
    created = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=["openid"],  # 기본 스코프 추가
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"]
    )
    
    client_id = created["UserPoolClient"]["ClientId"]
    client_secret = created["UserPoolClient"]["ClientSecret"]
    print(f"✅ M2M 클라이언트 생성 완료: {client_id}")
    
    return client_id, client_secret


def get_token(user_pool_id, client_id, client_secret, region):
    """
    Cognito OAuth2 토큰 획득 (Client Credentials Grant)
    
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
            "client_secret": client_secret,
            "scope": "openid",  # 스코프 추가
        }

        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as err:
        return {"error": str(err)}