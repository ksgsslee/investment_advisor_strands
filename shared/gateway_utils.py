"""
gateway_utils.py
AgentCore Gateway 관련 공통 유틸리티 함수들

이 모듈은 AWS Bedrock AgentCore Gateway 배포에 필요한 함수들을 제공합니다.
- Gateway용 IAM 역할 생성
- Gateway 생성 및 관리
- Gateway Target 생성
"""

import boto3
import json
import time


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
    """
    print("🔐 Gateway IAM 역할 생성 중...")
    
    iam_client = boto3.client('iam')
    agentcore_gateway_role_name = f'{gateway_name}-role'
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    # Gateway가 사용할 수 있는 권한 정책
    role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "GatewayPermissions",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:*",
                "bedrock:*",
                "agent-credential-provider:*",
                "iam:PassRole",
                "secretsmanager:GetSecretValue",
                "lambda:InvokeFunction"
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
    
    try:
        # 새 IAM 역할 생성
        agentcore_gateway_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json,
            Description='AgentCore Gateway execution role for Lambda invocation and AWS service access'
        )
        print("✅ 새 IAM 역할 생성 완료")
        time.sleep(10)
        
    except iam_client.exceptions.EntityAlreadyExistsException:
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


def create_gateway(gateway_name, role_arn, auth_components, region):
    """
    AgentCore Gateway 생성
    
    Args:
        gateway_name (str): Gateway 이름
        role_arn (str): Gateway 실행용 IAM 역할 ARN
        auth_components (dict): Cognito 인증 구성 요소
        region (str): AWS 리전
        
    Returns:
        dict: 생성된 Gateway 정보
    """
    print("🌉 Gateway 생성 중...")
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    # JWT 인증 설정
    auth_config = {
        'customJWTAuthorizer': {
            'allowedClients': [auth_components['client_id']],
            'discoveryUrl': auth_components['discovery_url']
        }
    }
    
    gateway = gateway_client.create_gateway(
        name=gateway_name,
        roleArn=role_arn,
        protocolType='MCP',
        authorizerType='CUSTOM_JWT',
        authorizerConfiguration=auth_config,
        description=f'{gateway_name} - MCP Gateway for AI agent integration'
    )
    
    gateway_id = gateway['gatewayId']
    print(f"✅ Gateway 생성 시작: {gateway_id}")
    
    # Gateway가 READY 상태가 될 때까지 대기
    print("⏳ Gateway가 READY 상태가 될 때까지 대기 중...")
    max_attempts = 60  # 최대 5분 대기
    for attempt in range(max_attempts):
        try:
            response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            status = response['status']
            
            if status == 'READY':
                print(f"✅ Gateway READY 상태 확인: {gateway_id}")
                break
            elif status in ['CREATE_FAILED', 'DELETE_FAILED']:
                raise Exception(f"Gateway 생성 실패: {status}")
            
            if attempt % 6 == 0:  # 30초마다 상태 출력
                print(f"   상태: {status} ({attempt * 5}초 경과)")
            
            time.sleep(5)
        except Exception as e:
            if attempt == max_attempts - 1:
                raise Exception(f"Gateway 상태 확인 실패: {str(e)}")
            time.sleep(5)
    else:
        raise Exception("Gateway READY 상태 대기 시간 초과")
    
    return gateway


def create_gateway_target(gateway_id, target_name, target_config, region):
    """
    Gateway Target 생성 (Lambda 함수를 MCP 도구로 노출)
    
    Args:
        gateway_id (str): Gateway ID
        target_name (str): Target 이름
        target_config (dict): Target 설정
        region (str): AWS 리전
        
    Returns:
        dict: 생성된 Target 정보
    """
    print("🎯 Gateway Target 생성 중...")
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    tool_count = len(target_config["mcp"]["lambda"]["toolSchema"]["inlinePayload"])
    print(f"📋 Target 설정: {tool_count}개 도구 구성")
    
    # Gateway Target 생성
    target = gateway_client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name=target_name,
        targetConfiguration=target_config,
        credentialProviderConfigurations=[{
            'credentialProviderType': 'GATEWAY_IAM_ROLE'
        }]
    )
    
    print(f"✅ Gateway Target 생성 완료: {target['targetId']}")
    return target