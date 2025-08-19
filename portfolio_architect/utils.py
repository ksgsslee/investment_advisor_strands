import boto3
import json
import time
from boto3.session import Session

def create_agentcore_gateway_role(gateway_name, region):
    """
    AgentCore Gateway용 IAM 역할 생성
    
    Args:
        gateway_name (str): 게이트웨이 이름
        region (str): AWS 리전
        
    Returns:
        dict: 생성된 IAM 역할 정보
    """
    iam_client = boto3.client('iam')
    agentcore_gateway_role_name = f'agentcore-{gateway_name}-role'
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    # 역할 권한 정책
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
                "lambda:InvokeFunction"             # Lambda 함수 호출 권한
            ],
            "Resource": "*"
        }]
    }
    
    # 신뢰 정책
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{
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
        }]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)
    role_policy_document = json.dumps(role_policy)
    
    # IAM 역할 생성
    try:
        agentcore_gateway_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )
        # 역할 생성 대기
        time.sleep(10)
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        print("Role already exists -- deleting and creating it again")
        
        # 기존 정책들 삭제
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
        print(f"deleting {agentcore_gateway_role_name}")
        iam_client.delete_role(RoleName=agentcore_gateway_role_name)
        
        # 새 역할 생성
        print(f"recreating {agentcore_gateway_role_name}")
        agentcore_gateway_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )

    # 정책 연결
    print(f"attaching role policy {agentcore_gateway_role_name}")
    try:
        iam_client.put_role_policy(
            PolicyDocument=role_policy_document,
            PolicyName="AgentCorePolicy",
            RoleName=agentcore_gateway_role_name
        )
    except Exception as e:
        print(f"정책 연결 오류: {e}")

    return agentcore_gateway_iam_role


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
    # 기존 사용자 풀 조회
    response = cognito.list_user_pools(MaxResults=60)
    for pool in response["UserPools"]:
        if pool["Name"] == user_pool_name:
            user_pool_id = pool["Id"]
            pool_info = cognito.describe_user_pool(UserPoolId=user_pool_id)
            
            # 도메인 정보 확인
            domain = pool_info.get('UserPool', {}).get('Domain')
            if domain:
                pool_region = user_pool_id.split('_')[0] if '_' in user_pool_id else region
                domain_url = f"https://{domain}.auth.{pool_region}.amazoncognito.com"
                print(f"Found domain for user pool {user_pool_id}: {domain_url}")
            return user_pool_id
    
    # 새 사용자 풀 생성
    print('Creating new user pool...')
    created = cognito.create_user_pool(PoolName=user_pool_name)
    user_pool_id = created["UserPool"]["Id"]
    
    # 도메인 생성
    domain_prefix = user_pool_id.replace("_", "").lower()
    cognito.create_user_pool_domain(
        Domain=domain_prefix,
        UserPoolId=user_pool_id
    )
    print(f"Created domain: {domain_prefix}")
    
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
    try:
        # 기존 리소스 서버 조회
        cognito.describe_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id
        )
        return resource_server_id
    except cognito.exceptions.ResourceNotFoundException:
        print('Creating new resource server...')
        # 새 리소스 서버 생성
        cognito.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id,
            Name=resource_server_name,
            Scopes=scopes
        )
        return resource_server_id


def get_or_create_m2m_client(cognito, user_pool_id, client_name, resource_server_id):
    """
    Machine-to-Machine 클라이언트 조회 또는 생성
    
    Args:
        cognito: Cognito 클라이언트
        user_pool_id (str): 사용자 풀 ID
        client_name (str): 클라이언트 이름
        resource_server_id (str): 리소스 서버 ID
    
    Returns:
        tuple: (클라이언트 ID, 클라이언트 시크릿)
    """
    # 기존 클라이언트 조회
    response = cognito.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=60)
    for client in response["UserPoolClients"]:
        if client["ClientName"] == client_name:
            describe = cognito.describe_user_pool_client(
                UserPoolId=user_pool_id, 
                ClientId=client["ClientId"]
            )
            return client["ClientId"], describe["UserPoolClient"]["ClientSecret"]
    
    # 새 클라이언트 생성
    print('Creating new M2M client...')
    created = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=[
            f"{resource_server_id}/gateway:read", 
            f"{resource_server_id}/gateway:write"
        ],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"]
    )
    
    return (
        created["UserPoolClient"]["ClientId"], 
        created["UserPoolClient"]["ClientSecret"]
    )
