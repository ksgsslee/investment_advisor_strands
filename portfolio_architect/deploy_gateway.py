
import boto3
import json
import time
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

def deploy_gateway_with_toolkit(lambda_arn, gateway_name="portfolio-architect-gateway", region="us-west-2"):
    """
    bedrock_agentcore_starter_toolkit을 사용한 Gateway 배포
    
    Args:
        lambda_arn (str): Lambda 함수 ARN
        gateway_name (str): Gateway 이름
        region (str): AWS 리전
    
    Returns:
        dict: 배포 결과 정보
    """
    try:
        print(f"Starting gateway deployment with toolkit: {gateway_name}")
        
        # 1. GatewayClient 초기화
        client = GatewayClient(region_name=region)
        
        # 2. Cognito OAuth 자동 설정
        print("Setting up Cognito OAuth...")
        cognito_result = client.create_oauth_authorizer_with_cognito(gateway_name)
        
        # 3. Gateway 생성
        print("Creating MCP Gateway...")
        gateway = client.create_mcp_gateway(
            name=gateway_name,
            role_arn=None,  # 자동으로 생성됨
            authorizer_config=cognito_result["authorizer_config"],
            enable_semantic_search=False
        )
        
        # 4. Lambda Target 추가
        print("Adding Lambda target...")
        target_config = {
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
        
        lambda_target = client.create_mcp_gateway_target(
            gateway=gateway,
            name=f"{gateway_name}-lambda-target",
            target_type="lambda",
            target_payload=target_config,
            credentials=[{
                'credentialProviderType': 'GATEWAY_IAM_ROLE'
            }]

        )

        # 5. 결과 정리
        result = {
            'gateway_id': gateway.gateway_id,
            'gateway_url': gateway.get_mcp_url(),
            'client_id': cognito_result['client_info']['client_id'],
            'client_secret': cognito_result['client_info']['client_secret'],
            'scope': cognito_result['client_info']['scope'],
            'target_id': target['targetId'],
            'lambda_arn': lambda_arn
        }
        
        print("\n✅ Gateway deployment completed successfully!")
        print(f"🔗 MCP Endpoint: {gateway.get_mcp_url()}")
        print(f"🔑 OAuth Credentials:")
        print(f"   Client ID: {cognito_result['client_info']['client_id']}")
        print(f"   Scope: {cognito_result['client_info']['scope']}")
        print(f"🎯 Target ID: {target['targetId']}")
        
        # 결과를 파일로 저장
        with open('gateway_deployment_info.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f"📄 Deployment info saved to gateway_deployment_info.json")
        
        return result
        
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        raise


if __name__ == "__main__":
    # 설정값
    LAMBDA_ARN = "arn:aws:lambda:us-west-2:905418397079:function:lambda-portfolio-architect"
    GATEWAY_NAME = "portfolio-architect-gateway"
    REGION = "us-west-2"
    
    # 배포 실행
    try:
        result = deploy_gateway_with_toolkit(LAMBDA_ARN, GATEWAY_NAME, REGION)
        print(f"\n🎉 Deployment successful!")
        print(f"📋 Summary:")
        for key, value in result.items():
            print(f"   {key}: {value}")
            
    except Exception as e:
        print(f"💥 Deployment failed: {e}")
        exit(1)
