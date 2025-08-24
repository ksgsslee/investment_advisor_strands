"""
cleanup.py
Financial Analyst Runtime 정리 스크립트
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
    root_dir = current_dir.parent
    
    files_to_delete = [
        # 로컬 배포 정보
        current_dir / "deployment_info.json",
        # Docker 관련 파일들 (루트에 생성됨)
        current_dir / "Dockerfile",
        current_dir / ".dockerignore", 
        current_dir / ".bedrock_agentcore.yaml",
    ]
    
    for file_path in files_to_delete:
        try:
            if file_path.exists():
                file_path.unlink()
                print(f"  ✅ 삭제: {file_path.name}")
        except Exception as e:
            print(f"  ⚠️ 삭제 실패 {file_path.name}: {e}")

def main():
    print(f"🧹 {Config.AGENT_NAME} Runtime 정리 중...")
    
    # 배포 정보 로드
    info_file = Path(__file__).parent / "deployment_info.json"
    deployment_info = None
    
    if info_file.exists():
        with open(info_file) as f:
            deployment_info = json.load(f)
        
        print(f"✅ 배포 정보 로드:")
        print(f"   📍 Agent: {deployment_info.get('agent_arn', 'N/A')}")
        print(f"   🔐 IAM Role: agentcore-runtime-{Config.AGENT_NAME}-role")
        print(f"   📦 ECR Repo: bedrock-agentcore-{Config.AGENT_NAME}")
    else:
        print("⚠️ 배포 정보 파일이 없습니다. 기본값으로 진행합니다.")
    
    # 확인
    response = input("\n정말로 모든 리소스를 삭제하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 취소됨")
        return
    
    # 1. AgentCore Runtime 삭제
    if deployment_info and 'agent_arn' in deployment_info:
        try:
            # agent_arn에서 runtime_id 추출
            runtime_id = deployment_info['agent_arn'].split('/')[-1]
            region = deployment_info.get('region', Config.REGION)
            client = boto3.client('bedrock-agentcore-control', region_name=region)
            client.delete_agent_runtime(agentRuntimeId=runtime_id)
            print(f"✅ Runtime 삭제: {runtime_id}")
        except Exception as e:
            print(f"⚠️ Runtime 삭제 실패: {e}")
    else:
        print("⚠️ Agent ARN 정보가 없어 Runtime 삭제를 건너뜁니다.")
    
    # 2. ECR 리포지토리 삭제
    try:
        region = deployment_info.get('region', Config.REGION) if deployment_info else Config.REGION
        ecr = boto3.client('ecr', region_name=region)
        
        # Config에서 ECR 리포지토리 이름 생성
        repo_name = f"bedrock-agentcore-{Config.AGENT_NAME}"
        
        ecr.delete_repository(repositoryName=repo_name, force=True)
        print(f"✅ ECR 리포지토리 삭제: {repo_name}")
    except Exception as e:
        print(f"⚠️ ECR 삭제 실패: {e}")
    
    # 3. IAM 역할 삭제
    try:
        iam = boto3.client('iam')
        
        # Config에서 IAM 역할 이름 생성
        role_name = f'agentcore-runtime-{Config.AGENT_NAME}-role'
        
        # 정책 삭제
        policies = iam.list_role_policies(RoleName=role_name)
        for policy in policies['PolicyNames']:
            iam.delete_role_policy(RoleName=role_name, PolicyName=policy)
        
        # 역할 삭제
        iam.delete_role(RoleName=role_name)
        print(f"✅ IAM 역할 삭제: {role_name}")
    except Exception as e:
        print(f"⚠️ IAM 삭제 실패: {e}")
    
    # 4. 생성된 파일들 정리
    cleanup_generated_files()
    
    print("🎉 정리 완료!")

if __name__ == "__main__":
    main()