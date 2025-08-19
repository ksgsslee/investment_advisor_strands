import boto3
import time
import json
from utils import (
    create_agentcore_gateway_role,
    get_or_create_resource_server,
    get_or_create_user_pool,
    get_or_create_m2m_client
)


def delete_existing_gateway(gateway_name, region):
    """
    기존 Gateway가 존재하는 경우 삭제합니다.
    
    동일한 이름의 Gateway가 이미 존재하는 경우, 새로운 Gateway 생성 전에
    기존 Gateway를 삭제하여 이름 충돌을 방지합니다.
    
    Args:
        gateway_name (str): 삭제할 Gateway 이름
        region (str): AWS 리전
    
    Returns:
        None
    """
    try:
        # Bedrock AgentCore Gateway 클라이언트 생성
        gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        # 현재 존재하는 모든 Gateway 목록 조회
        gateways = gateway_client.list_gateways().get('items', [])
        
        # 동일한 이름의 Gateway 검색 및 삭제
        for gw in gateways:
            if gw['name'] == gateway_name:
                print(f"🗑️ Deleting existing gateway '{gateway_name}' (ID: {gw['gatewayId']})...")
                gateway_client.delete_gateway(gatewayIdentifier=gw['gatewayId'])
                
                # Gateway 삭제 완료까지 대기 (AWS 리소스 정리 시간 필요)
                time.sleep(3)
                print(f"✅ Gateway '{gateway_name}' deleted successfully")
                break
        else:
            print(f"ℹ️ No existing gateway found with name '{gateway_name}'")
            
    except Exception as e:
        print(f"⚠️ Error while deleting existing gateway: {str(e)}")
        # 삭제 실패해도 배포는 계속 진행 (Gateway가 없을 수도 있음)
        pass


def deploy_gateway(lambda_arn, gateway_name, region):
    """
    Gateway 배포 프로세스
    
    Args:
        lambda_arn (str): Lambda 함수 ARN
        gateway_name (str): Gateway 이름
        region (str): AWS 리전
    
    Returns:
        dict: 배포 결과 정보
    """
    try:
        print("Starting gateway deployment...")
        
        # 기존 Gateway 삭제 (동일한 이름의 Gateway가 있다면 삭제)
        delete_existing_gateway(gateway_name, region)

        # 1. IAM 역할 생성
        print("Creating IAM role...")
        iam_role = create_agentcore_gateway_role(gateway_name, region)
        role_arn = iam_role['Role']['Arn']
        print(f"Created role: {role_arn}")
        time.sleep(10)  # IAM 역할 전파 대기
        
        # 2. Cognito 설정
        cognito = boto3.client('cognito-idp', region_name=region)
        
        # 사용자 풀 생성
        print("Setting up Cognito...")
        user_pool_id = get_or_create_user_pool(cognito, f"{gateway_name}-pool", region)
        
        # 리소스 서버 생성
        resource_server_id = f"{gateway_name}-server"
        resource_server_name = f"{gateway_name} Resource Server"
        scopes = [
            {"ScopeName": "gateway:read", "ScopeDescription": "Read access"},
            {"ScopeName": "gateway:write", "ScopeDescription": "Write access"}
        ]
        resource_server_id = get_or_create_resource_server(
            cognito, 
            user_pool_id, 
            resource_server_id, 
            resource_server_name, 
            scopes
        )
        
        # M2M 클라이언트 생성
        client_id, client_secret = get_or_create_m2m_client(
            cognito,
            user_pool_id,
            f"{gateway_name}-client",
            resource_server_id
        )
        
        # 3. Gateway 생성
        print("Creating Gateway...")
        gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        auth_config = {
            'customJWTAuthorizer': {
                'allowedClients': [client_id],
                'discoveryUrl': f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
            }
        }
        
        gateway = gateway_client.create_gateway(
            name=gateway_name,
            roleArn=role_arn,
            protocolType='MCP',
            authorizerType='CUSTOM_JWT',
            authorizerConfiguration=auth_config,
            description=f'Gateway for {gateway_name}'
        )
        
        # 4. Gateway Target 생성
        print("Creating Gateway Target...")
        target = gateway_client.create_gateway_target(
            gatewayIdentifier=gateway['gatewayId'],
            name=f"{gateway_name}-target",
            targetConfiguration={
                'mcp': {
                    'lambda': {
                        'lambdaArn': lambda_arn,
                        'toolSchema': {
                            'inlinePayload': [
                                {
                                    'name': 'get_available_products',
                                    'description': '사용 가능한 투자 상품 목록을 조회합니다.',
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {},
                                        "required": []
                                    }
                                },
                                {
                                    "name": "get_product_data",
                                    "description": "선택한 투자 상품의 최근 가격 데이터를 조회합니다.",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "ticker": {
                                                "type": "string",
                                                "description": "조회할 투자 상품의 티커"
                                            }
                                        },
                                        "required": ["ticker"]
                                    }
                                }
                            ]
                        }
                    }
                }
            },
            credentialProviderConfigurations=[{
                'credentialProviderType': 'GATEWAY_IAM_ROLE'
            }]
        )
        
        result = {
            'role_arn': role_arn,
            'user_pool_id': user_pool_id,
            'client_id': client_id,
            'client_secret': client_secret,
            'gateway_id': gateway['gatewayId'],
            'gateway_url': gateway['gatewayUrl'],
            'target': target
        }
        
        print("\nGateway deployment completed successfully!")
        print(f"Gateway URL: {gateway['gatewayUrl']}")
        return result
        
    except Exception as e:
        print(f"Deployment failed: {str(e)}")
        raise


if __name__ == "__main__":
    # 설정값
    LAMBDA_ARN = "arn:aws:lambda:us-west-2:905418397079:function:lambda-portfolio-architect"
    GATEWAY_NAME = "sample-gateway"
    REGION = "us-west-2"
    
    # 배포 실행
    result = deploy_gateway(LAMBDA_ARN, GATEWAY_NAME, REGION)
    print(f"Deployment result: {json.dumps(result, indent=2)}")
