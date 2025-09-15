"""
cleanup.py

Fund Manager 시스템 정리 스크립트
모든 AWS 리소스 삭제 및 정리
"""

import json
import boto3
import time
import sys
from pathlib import Path

def load_deployment_info():
    """배포 정보 로드"""
    current_dir = Path(__file__).parent
    
    # Fund Manager 정보
    fund_manager_info = None
    fund_manager_file = current_dir / "deployment_info.json"
    if fund_manager_file.exists():
        with open(fund_manager_file) as f:
            fund_manager_info = json.load(f)
    
    # Memory 정보
    memory_info = None
    memory_file = current_dir / "agentcore_memory" / "deployment_info.json"
    if memory_file.exists():
        with open(memory_file) as f:
            memory_info = json.load(f)
    
    return fund_manager_info, memory_info

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
        
        # 관리형 정책 분리
        attached_policies = iam.list_attached_role_policies(RoleName=role_name)
        for policy in attached_policies['AttachedPolicies']:
            iam.detach_role_policy(RoleName=role_name, PolicyArn=policy['PolicyArn'])
        
        # 역할 삭제
        iam.delete_role(RoleName=role_name)
        print(f"✅ IAM 역할 삭제: {role_name}")
        return True
    except Exception as e:
        print(f"⚠️ IAM 역할 삭제 실패 {role_name}: {e}")
        return False

def delete_memory(memory_id, region):
    """AgentCore Memory 삭제"""
    try:
        from bedrock_agentcore.memory import MemoryClient
        memory_client = MemoryClient(region_name=region)
        memory_client.delete_memory(memory_id=memory_id)
        print(f"✅ Memory 삭제: {memory_id} (리전: {region})")
        return True
    except Exception as e:
        print(f"⚠️ Memory 삭제 실패: {e}")
        return False

def cleanup_local_files():
    """로컬 생성 파일들 삭제"""
    current_dir = Path(__file__).parent
    files_to_delete = [
        current_dir / "deployment_info.json",
        current_dir / "Dockerfile",
        current_dir / ".dockerignore", 
        current_dir / ".bedrock_agentcore.yaml",
        current_dir / "agentcore_memory" / "deployment_info.json",
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
    print("🧹 Fund Manager 시스템 정리")
    
    # 배포 정보 로드
    fund_manager_info, memory_info = load_deployment_info()
    
    if not fund_manager_info and not memory_info:
        print("⚠️ 배포 정보가 없습니다.")
        return
    
    # 확인
    response = input("\n정말로 모든 리소스를 삭제하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 취소됨")
        return
    
    print("\n🗑️ AWS 리소스 삭제 중...")
    
    # 1. Fund Manager Runtime 삭제
    if fund_manager_info and 'agent_arn' in fund_manager_info:
        region = fund_manager_info.get('region', 'us-west-2')
        delete_runtime(fund_manager_info['agent_arn'], region)
    
    # 2. ECR 리포지토리 삭제
    if fund_manager_info and 'ecr_repo_name' in fund_manager_info and fund_manager_info['ecr_repo_name']:
        region = fund_manager_info.get('region', 'us-west-2')
        delete_ecr_repo(fund_manager_info['ecr_repo_name'], region)
    
    # 3. IAM 역할 삭제
    if fund_manager_info and 'iam_role_name' in fund_manager_info:
        delete_iam_role(fund_manager_info['iam_role_name'])
    
    # 4. AgentCore Memory 삭제
    if memory_info and 'memory_id' in memory_info:
        region = memory_info.get('region', 'us-west-2')
        delete_memory(memory_info['memory_id'], region)
    
    print("\n🎉 AWS 리소스 정리 완료!")
    
    # 5. 로컬 파일들 정리
    if input("\n로컬 생성 파일들도 삭제하시겠습니까? (y/N): ").lower() == 'y':
        cleanup_local_files()
    else:
        print("📁 로컬 파일들은 유지됩니다.")

if __name__ == "__main__":
    main()