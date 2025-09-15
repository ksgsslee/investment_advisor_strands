"""
cleanup.py

Portfolio Architect 시스템 정리 스크립트
모든 AWS 리소스 삭제 및 정리 정보 JSON 저장
"""

import json
import boto3
import time
import sys
from pathlib import Path

# Config 클래스들은 더 이상 필요 없음 - 배포 정보에서 리전 정보 직접 사용

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

def delete_runtime(agent_arn, region):
    """Runtime 삭제"""
    try:
        runtime_id = agent_arn.split('/')[-1]
        client = boto3.client('bedrock-agentcore-control', region_name=region)
        client.delete_agent_runtime(agentRuntimeId=runtime_id)
        print(f"✅ Runtime 삭제: {runtime_id} (리전: {region})")
        return True
    except Exception as e:
        print(f"⚠️ Runtime 삭제 실패: {e}")
        return False

def delete_ecr_repo(repo_name, region):
    """ECR 리포지토리 삭제"""
    try:
        ecr = boto3.client('ecr', region_name=region)
        ecr.delete_repository(repositoryName=repo_name, force=True)
        print(f"✅ ECR 삭제: {repo_name} (리전: {region})")
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



def delete_cognito_resources(user_pool_id, region):
    """Cognito 리소스 삭제"""
    try:
        cognito = boto3.client('cognito-idp', region_name=region)
        
        print(f"🔍 Cognito User Pool 삭제 시작: {user_pool_id}")
        
        # 1. User Pool Domain 삭제 (있는 경우)
        try:
            domain_prefix = user_pool_id.replace("_", "").lower()
            cognito.delete_user_pool_domain(
                Domain=domain_prefix,
                UserPoolId=user_pool_id
            )
            print(f"✅ User Pool Domain 삭제: {domain_prefix}")
            time.sleep(2)  # Domain 삭제 대기
        except Exception as e:
            print(f"ℹ️ User Pool Domain 삭제 스킵 (없거나 이미 삭제됨): {e}")
        
        # 2. Resource Server들 삭제
        try:
            resource_servers = cognito.list_resource_servers(
                UserPoolId=user_pool_id,
                MaxResults=50  # maxResults 파라미터 명시적으로 설정
            )
            for server in resource_servers['ResourceServers']:
                cognito.delete_resource_server(
                    UserPoolId=user_pool_id,
                    Identifier=server['Identifier']
                )
                print(f"✅ Resource Server 삭제: {server['Identifier']}")
        except Exception as e:
            print(f"ℹ️ Resource Server 삭제 스킵: {e}")
        
        # 3. 클라이언트들 삭제
        try:
            clients = cognito.list_user_pool_clients(
                UserPoolId=user_pool_id,
                MaxResults=50  # maxResults 파라미터 명시적으로 설정
            )
            for client in clients['UserPoolClients']:
                cognito.delete_user_pool_client(
                    UserPoolId=user_pool_id,
                    ClientId=client['ClientId']
                )
                print(f"✅ User Pool Client 삭제: {client['ClientId']}")
        except Exception as e:
            print(f"ℹ️ User Pool Client 삭제 스킵: {e}")
        
        # 4. User Pool 삭제
        time.sleep(3)  # 리소스 정리 대기
        cognito.delete_user_pool(UserPoolId=user_pool_id)
        print(f"✅ Cognito User Pool 삭제 완료: {user_pool_id} (리전: {region})")
        return True
        
    except cognito.exceptions.ResourceNotFoundException:
        print(f"ℹ️ Cognito User Pool이 이미 삭제됨: {user_pool_id}")
        return True
    except Exception as e:
        print(f"⚠️ Cognito 삭제 실패: {e}")
        print(f"💡 수동 삭제 필요: AWS 콘솔에서 User Pool {user_pool_id}를 확인하세요.")
        return False

def cleanup_local_files():
    """로컬 생성 파일들 삭제"""
    current_dir = Path(__file__).parent
    files_to_delete = [
        current_dir / "deployment_info.json",
        current_dir / "Dockerfile",
        current_dir / ".dockerignore", 
        current_dir / ".bedrock_agentcore.yaml",
        current_dir / "mcp_server" / "mcp_deployment_info.json",
        current_dir / "mcp_server" / "Dockerfile",
        current_dir / "mcp_server" / ".dockerignore",
        current_dir / "mcp_server" / ".bedrock_agentcore.yaml",
    ]
    
    deleted_count = 0
    for file_path in files_to_delete:
        if file_path.exists():
            file_path.unlink()
            print(f"✅ 파일 삭제: {file_path.name}")
            deleted_count += 1
    
    if deleted_count > 0:
        print(f"✅ 로컬 파일 정리 완료! ({deleted_count}개 파일 삭제)")
    else:
        print("📁 삭제할 로컬 파일이 없습니다.")



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
        region = portfolio_info.get('region', 'us-west-2')  # 기본값 fallback
        delete_runtime(portfolio_info['agent_arn'], region)
    
    # 2. MCP Server Runtime 삭제
    if mcp_info and 'agent_arn' in mcp_info:
        region = mcp_info.get('region', 'us-west-2')  # 기본값 fallback
        delete_runtime(mcp_info['agent_arn'], region)
    
    # 3. ECR 리포지토리들 삭제
    if portfolio_info and 'ecr_repo_name' in portfolio_info and portfolio_info['ecr_repo_name']:
        region = portfolio_info.get('region', 'us-west-2')
        delete_ecr_repo(portfolio_info['ecr_repo_name'], region)
    
    if mcp_info and 'ecr_repo_name' in mcp_info and mcp_info['ecr_repo_name']:
        region = mcp_info.get('region', 'us-west-2')
        delete_ecr_repo(mcp_info['ecr_repo_name'], region)
    
    # 4. IAM 역할들 삭제 (IAM은 글로벌 서비스라 리전 불필요)
    if portfolio_info and 'iam_role_name' in portfolio_info:
        delete_iam_role(portfolio_info['iam_role_name'])
    
    if mcp_info and 'iam_role_name' in mcp_info:
        delete_iam_role(mcp_info['iam_role_name'])
    
    # 5. Cognito 리소스 삭제
    if mcp_info and 'user_pool_id' in mcp_info:
        region = mcp_info.get('region', 'us-west-2')
        delete_cognito_resources(mcp_info['user_pool_id'], region)
    
    print("\n🎉 AWS 리소스 정리 완료!")
    
    # 6. 로컬 파일들 정리
    if input("\n로컬 생성 파일들도 삭제하시겠습니까? (y/N): ").lower() == 'y':
        cleanup_local_files()
    else:
        print("📁 로컬 파일들은 유지됩니다.")

if __name__ == "__main__":
    main()