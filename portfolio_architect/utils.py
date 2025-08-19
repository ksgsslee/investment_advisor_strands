import boto3
import json
import time
import requests
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
    agentcore_gateway_role_name = f'agentcore-runtime-{gateway_name}-role'
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
