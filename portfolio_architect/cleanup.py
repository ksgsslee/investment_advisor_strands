"""
cleanup.py
Portfolio Architect 전체 시스템 정리 스크립트

MCP Server와 Portfolio Architect Runtime을 포함한 모든 AWS 리소스를 정리합니다.
"""

import json
import boto3
from pathlib import Path
import sys

# deploy.py의 Config 가져오기
sys.path.insert(0, str(Path(__file__).parent))
from deploy import Config

def cleanup_generated_files():
    """배포 과정에서 생성된 파일들 정리"""
    print("🗑️ 생성된 파일들 정리 중...")
    
    current_dir = Path(__file__).parent
    mcp_dir = current_dir / "mcp_server"
    
    files_to_delete = [
        # Portfolio Architect 관련 파일들
        current_dir / "deployment_info.json",
        current_dir / "Dockerfile",
        current_dir / ".dockerignore", 
        current_dir / ".bedrock_agentcore.yaml",
        
        # MCP Server 관련 파일들
        mcp_dir / "mcp_deployment_info.json",
        mcp_dir / "Dockerfile",
        mcp_dir / ".dockerignore",
        mcp_dir / ".bedrock_agentcore.yaml",
    ]
    
    for file_path in files_to_delete:
        try:
            if file_path.exists():
                file_path.unlink()
                print(f"  ✅ 삭제: {file_path.relative_to(current_dir)}")
        except Exception as e:
            print(f"  ⚠️ 삭제 실패 {file_path.name}: {e}")

def delete_cognito_resources(deployment_info):
    """Cognito User Pool 및 관련 리소스 삭제"""
    if 'mcp_user_pool_id' not in deployment_info:
        print("⚠️ Cognito User Pool 정보가 없어 삭제를 건너뜁니다.")
        return
    
    try:
        print("🗑️ Cognito 리소스 삭제 중...")
        region = deployment_info.get('region', Config.REGION)
        cognito = boto3.client('cognito-idp', region_name=region)
        
        user_pool_id = deployment_info['mcp_user_pool_id']
        
        # User Pool 클라이언트들 삭제
        try:
            clients = cognito.list_user_pool_clients(UserPoolId=user_pool_id)
            for client in clients['UserPoolClients']:
                cognito.delete_user_pool_client(
                    UserPoolId=user_pool_id,
                    ClientId=client['ClientId']
                )
                print(f"  ✅ User Pool 클라이언트 삭제: {client['ClientId']}")
        except Exception as e:
            print(f"  ⚠️ User Pool 클라이언트 삭제 실패: {e}")
        
        # User Pool 도메인 삭제 (있는 경우)
        try:
            domain_name = user_pool_id.replace("_", "").lower()
            cognito.delete_user_pool_domain(
                Domain=domain_name,
                UserPoolId=user_pool_id
            )
            print(f"  ✅ User Pool 도메인 삭제: {domain_name}")
        except Exception as e:
            # 도메인이 없을 수 있으므로 경고만 출력
            print(f"  ⚠️ User Pool 도메인 삭제 실패 (없을 수 있음): {e}")
        
        # User Pool 삭제
        cognito.delete_user_pool(UserPoolId=user_pool_id)
        print(f"✅ Cognito User Pool 삭제: {user_pool_id}")
        
    except Exception as e:
        print(f"⚠️ Cognito 삭제 실패: {e}")

def main():
    print(f"🧹 {Config.AGENT_NAME} 전체 시스템 정리 중...")
    
    # 배포 정보 로드
    info_file = Path(__file__).parent / "deployment_info.json"
    mcp_info_file = Path(__file__).parent / "mcp_server" / "mcp_deployment_info.json"
    
    deployment_info = None
    mcp_deployment_info = None
    
    # Portfolio Architect 배포 정보 로드
    if info_file.exists():
        with open(info_file) as f:
            deployment_info = json.load(f)
        print(f"✅ Portfolio Architect 배포 정보 로드:")
        print(f"   📍 Agent: {deployment_info.get('agent_arn', 'N/A')}")
        print(f"   🔗 MCP Server: {deployment_info.get('mcp_server_arn', 'N/A')}")
    else:
        print("⚠️ Portfolio Architect 배포 정보 파일이 없습니다.")
    
    # MCP Server 배포 정보 로드
    if mcp_info_file.exists():
        with open(mcp_info_file) as f:
            mcp_deployment_info = json.load(f)
        print(f"✅ MCP Server 배포 정보 로드:")
        print(f"   📍 MCP Agent: {mcp_deployment_info.get('agent_arn', 'N/A')}")
        print(f"   🔐 User Pool: {mcp_deployment_info.get('user_pool_id', 'N/A')}")
    else:
        print("⚠️ MCP Server 배포 정보 파일이 없습니다.")
    
    if not deployment_info and not mcp_deployment_info:
        print("⚠️ 배포 정보가 없습니다. 기본값으로 진행합니다.")
    
    # 확인
    response = input("\n정말로 모든 리소스를 삭제하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 취소됨")
        return
    
    # 1. Portfolio Architect Runtime 삭제
    if deployment_info and 'agent_arn' in deployment_info:
        try:
            runtime_id = deployment_info['agent_arn'].split('/')[-1]
            region = deployment_info.get('region', Config.REGION)
            client = boto3.client('bedrock-agentcore-control', region_name=region)
            client.delete_agent_runtime(agentRuntimeId=runtime_id)
            print(f"✅ Portfolio Architect Runtime 삭제: {runtime_id}")
        except Exception as e:
            print(f"⚠️ Portfolio Architect Runtime 삭제 실패: {e}")
    else:
        print("⚠️ Portfolio Architect ARN 정보가 없어 Runtime 삭제를 건너뜁니다.")
    
    # 2. MCP Server Runtime 삭제
    if mcp_deployment_info and 'agent_arn' in mcp_deployment_info:
        try:
            mcp_runtime_id = mcp_deployment_info['agent_arn'].split('/')[-1]
            region = mcp_deployment_info.get('region', Config.REGION)
            client = boto3.client('bedrock-agentcore-control', region_name=region)
            client.delete_agent_runtime(agentRuntimeId=mcp_runtime_id)
            print(f"✅ MCP Server Runtime 삭제: {mcp_runtime_id}")
        except Exception as e:
            print(f"⚠️ MCP Server Runtime 삭제 실패: {e}")
    else:
        print("⚠️ MCP Server ARN 정보가 없어 Runtime 삭제를 건너뜁니다.")
    
    # 3. ECR 리포지토리들 삭제
    try:
        region = deployment_info.get('region', Config.REGION) if deployment_info else Config.REGION
        ecr = boto3.client('ecr', region_name=region)
        
        # Portfolio Architect ECR 삭제
        portfolio_repo_name = f"bedrock-agentcore-{Config.AGENT_NAME}"
        try:
            ecr.delete_repository(repositoryName=portfolio_repo_name, force=True)
            print(f"✅ Portfolio Architect ECR 삭제: {portfolio_repo_name}")
        except Exception as e:
            print(f"⚠️ Portfolio Architect ECR 삭제 실패: {e}")
        
        # MCP Server ECR 삭제
        mcp_repo_name = f"bedrock-agentcore-{Config.MCP_SERVER_NAME}"
        try:
            ecr.delete_repository(repositoryName=mcp_repo_name, force=True)
            print(f"✅ MCP Server ECR 삭제: {mcp_repo_name}")
        except Exception as e:
            print(f"⚠️ MCP Server ECR 삭제 실패: {e}")
            
    except Exception as e:
        print(f"⚠️ ECR 클라이언트 생성 실패: {e}")
    
    # 4. IAM 역할들 삭제
    try:
        iam = boto3.client('iam')
        
        # Portfolio Architect IAM 역할 삭제
        portfolio_role_name = f'agentcore-runtime-{Config.AGENT_NAME}-role'
        try:
            # 정책 삭제
            policies = iam.list_role_policies(RoleName=portfolio_role_name)
            for policy in policies['PolicyNames']:
                iam.delete_role_policy(RoleName=portfolio_role_name, PolicyName=policy)
            
            # 역할 삭제
            iam.delete_role(RoleName=portfolio_role_name)
            print(f"✅ Portfolio Architect IAM 역할 삭제: {portfolio_role_name}")
        except Exception as e:
            print(f"⚠️ Portfolio Architect IAM 삭제 실패: {e}")
        
        # MCP Server IAM 역할 삭제
        mcp_role_name = f'agentcore-runtime-{Config.MCP_SERVER_NAME}-role'
        try:
            # 정책 삭제
            policies = iam.list_role_policies(RoleName=mcp_role_name)
            for policy in policies['PolicyNames']:
                iam.delete_role_policy(RoleName=mcp_role_name, PolicyName=policy)
            
            # 역할 삭제
            iam.delete_role(RoleName=mcp_role_name)
            print(f"✅ MCP Server IAM 역할 삭제: {mcp_role_name}")
        except Exception as e:
            print(f"⚠️ MCP Server IAM 삭제 실패: {e}")
            
    except Exception as e:
        print(f"⚠️ IAM 클라이언트 생성 실패: {e}")
    
    # 5. Cognito 리소스 삭제 (MCP Server 인증용)
    if deployment_info or mcp_deployment_info:
        # 두 배포 정보 중 하나에서 Cognito 정보 가져오기
        cognito_info = deployment_info if deployment_info and 'mcp_user_pool_id' in deployment_info else mcp_deployment_info
        if cognito_info:
            delete_cognito_resources(cognito_info)
    
    # 6. 생성된 파일들 정리
    cleanup_generated_files()
    
    print("🎉 전체 시스템 정리 완료!")
    print("\n📋 정리된 항목:")
    print("• Portfolio Architect Runtime")
    print("• MCP Server Runtime") 
    print("• ECR 리포지토리들 (Docker 이미지 포함)")
    print("• IAM 역할들 및 정책")
    print("• Cognito User Pool 및 클라이언트")
    print("• 로컬 배포 정보 파일들")

if __name__ == "__main__":
    main()