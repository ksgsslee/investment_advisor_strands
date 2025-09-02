"""
Portfolio Architect 시스템 정리 스크립트
모든 AWS 리소스 삭제 및 정리 정보 JSON 저장
"""

import json
import boto3
import time
from pathlib import Path

class Config:
    """Portfolio Architect 정리 설정"""
    REGION = "us-west-2"
    AGENT_NAME = "portfolio_architect"
    MCP_SERVER_NAME = "mcp_server"

def load_deployment_info():
    """배포 정보 로드"""
    current_dir = Path(__file__).parent
    
    # Portfolio Architect 정보
    portfolio_info = None
    portfolio_file = current_dir / "deployment_info.json"
    if portfolio_file.exists():
        with open(portfolio_file) as f:
            portfolio_info = json.load(f)
    
    # MCP Server 정보
    mcp_info = None
    mcp_file = current_dir / "mcp_server" / "mcp_deployment_info.json"
    if mcp_file.exists():
        with open(mcp_file) as f:
            mcp_info = json.load(f)
    
    return portfolio_info, mcp_info

def delete_runtime(agent_arn):
    """Runtime 삭제"""
    try:
        runtime_id = agent_arn.split('/')[-1]
        client = boto3.client('bedrock-agentcore-control', region_name=Config.REGION)
        client.delete_agent_runtime(agentRuntimeId=runtime_id)
        print(f"✅ Runtime 삭제: {runtime_id}")
        return True
    except Exception as e:
        print(f"⚠️ Runtime 삭제 실패: {e}")
        return False

def delete_ecr_repo(repo_name):
    """ECR 리포지토리 삭제"""
    try:
        ecr = boto3.client('ecr', region_name=Config.REGION)
        ecr.delete_repository(repositoryName=repo_name, force=True)
        print(f"✅ ECR 삭제: {repo_name}")
        return True
    except Exception as e:
        print(f"⚠️ ECR 삭제 실패 {repo_name}: {e}")
        return False

def delete_iam_role(role_name):
    """IAM 역할 삭제"""
    try:
        iam = boto3.client('iam')
        
        # 정책 삭제
        policies = iam.list_role_policies(RoleName=role_name)
        for policy in policies['PolicyNames']:
            iam.delete_role_policy(RoleName=role_name, PolicyName=policy)
        
        # 역할 삭제
        iam.delete_role(RoleName=role_name)
        print(f"✅ IAM 역할 삭제: {role_name}")
        return True
    except Exception as e:
        print(f"⚠️ IAM 역할 삭제 실패 {role_name}: {e}")
        return False

def delete_cognito_resources(user_pool_id):
    """Cognito 리소스 삭제"""
    try:
        cognito = boto3.client('cognito-idp', region_name=Config.REGION)
        
        # 클라이언트들 삭제
        clients = cognito.list_user_pool_clients(UserPoolId=user_pool_id)
        for client in clients['UserPoolClients']:
            cognito.delete_user_pool_client(
                UserPoolId=user_pool_id,
                ClientId=client['ClientId']
            )
        
        # User Pool 삭제
        cognito.delete_user_pool(UserPoolId=user_pool_id)
        print(f"✅ Cognito User Pool 삭제: {user_pool_id}")
        return True
    except Exception as e:
        print(f"⚠️ Cognito 삭제 실패: {e}")
        return False

def get_generated_files():
    """삭제 가능한 생성된 파일들 목록 반환"""
    current_dir = Path(__file__).parent
    files_to_check = [
        current_dir / "deployment_info.json",
        current_dir / "Dockerfile",
        current_dir / ".dockerignore", 
        current_dir / ".bedrock_agentcore.yaml",
        current_dir / "mcp_server" / "mcp_deployment_info.json",
        current_dir / "mcp_server" / "Dockerfile",
        current_dir / "mcp_server" / ".dockerignore",
        current_dir / "mcp_server" / ".bedrock_agentcore.yaml",
    ]
    
    existing_files = []
    for file_path in files_to_check:
        if file_path.exists():
            existing_files.append(file_path)
    
    return existing_files

def cleanup_files(files_to_delete):
    """생성된 파일들 정리"""
    current_dir = Path(__file__).parent
    deleted_files = []
    
    for file_path in files_to_delete:
        try:
            file_path.unlink()
            deleted_files.append(str(file_path.relative_to(current_dir)))
            print(f"✅ 파일 삭제: {file_path.name}")
        except Exception as e:
            print(f"⚠️ 파일 삭제 실패 {file_path.name}: {e}")
    
    return deleted_files



def main():
    print("🧹 Portfolio Architect 시스템 정리")
    
    # 배포 정보 로드
    portfolio_info, mcp_info = load_deployment_info()
    
    if not portfolio_info and not mcp_info:
        print("⚠️ 배포 정보가 없습니다.")
        return
    
    # 확인
    response = input("\n정말로 모든 리소스를 삭제하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 취소됨")
        return
    
    print("\n🗑️ AWS 리소스 삭제 중...")
    
    # 1. Portfolio Architect Runtime 삭제
    if portfolio_info and 'agent_arn' in portfolio_info:
        delete_runtime(portfolio_info['agent_arn'])
    
    # 2. MCP Server Runtime 삭제
    if mcp_info and 'agent_arn' in mcp_info:
        delete_runtime(mcp_info['agent_arn'])
    
    # 3. ECR 리포지토리들 삭제
    portfolio_repo = f"bedrock-agentcore-{Config.AGENT_NAME}"
    delete_ecr_repo(portfolio_repo)
    
    mcp_repo = f"bedrock-agentcore-{Config.MCP_SERVER_NAME}"
    delete_ecr_repo(mcp_repo)
    
    # 4. IAM 역할들 삭제
    if portfolio_info and 'iam_role_name' in portfolio_info:
        delete_iam_role(portfolio_info['iam_role_name'])
    
    if mcp_info and 'iam_role_name' in mcp_info:
        delete_iam_role(mcp_info['iam_role_name'])
    
    # 5. Cognito 리소스 삭제
    if mcp_info and 'user_pool_id' in mcp_info:
        delete_cognito_resources(mcp_info['user_pool_id'])
    
    print("\n🎉 AWS 리소스 정리 완료!")
    
    # 6. 로컬 파일들 정리 (사용자 확인 후)
    generated_files = get_generated_files()
    if generated_files:
        print(f"\n📁 삭제 가능한 로컬 파일들 ({len(generated_files)}개):")
        current_dir = Path(__file__).parent
        for file_path in generated_files:
            print(f"   - {file_path.relative_to(current_dir)}")
        
        file_response = input("\n로컬 생성 파일들도 삭제하시겠습니까? (y/N): ")
        if file_response.lower() == 'y':
            deleted_files = cleanup_files(generated_files)
            print(f"✅ 로컬 파일 정리 완료! ({len(deleted_files)}개 파일 삭제)")
        else:
            print("📁 로컬 파일들은 유지됩니다.")
    else:
        print("\n📁 삭제할 로컬 파일이 없습니다.")

if __name__ == "__main__":
    main()