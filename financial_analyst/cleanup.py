"""
cleanup.py
Financial Analyst Runtime 정리 스크립트
"""

import json
import boto3
from pathlib import Path

def main():
    print("🧹 Financial Analyst Runtime 정리 중...")
    
    # 배포 정보 로드
    info_file = Path(__file__).parent / "deployment_info.json"
    deployment_info = None
    
    if info_file.exists():
        with open(info_file) as f:
            deployment_info = json.load(f)
        print(f"✅ 배포 정보 로드: {deployment_info['agent_arn']}")
    
    # 1. AgentCore Runtime 삭제
    if deployment_info:
        try:
            runtime_id = deployment_info['agent_arn'].split('/')[-1]
            client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')
            client.delete_agent_runtime(agentRuntimeId=runtime_id)
            print(f"✅ Runtime 삭제: {runtime_id}")
        except Exception as e:
            print(f"⚠️ Runtime 삭제 실패: {e}")
    
    # 2. ECR 리포지토리 삭제
    try:
        ecr = boto3.client('ecr', region_name='us-west-2')
        ecr.delete_repository(repositoryName='bedrock-agentcore-financial_analyst', force=True)
        print("✅ ECR 리포지토리 삭제")
    except Exception as e:
        print(f"⚠️ ECR 삭제 실패: {e}")
    
    # 3. IAM 역할 삭제
    try:
        iam = boto3.client('iam')
        role_name = 'agentcore-runtime-financial_analyst-role'
        
        # 정책 삭제
        policies = iam.list_role_policies(RoleName=role_name)
        for policy in policies['PolicyNames']:
            iam.delete_role_policy(RoleName=role_name, PolicyName=policy)
        
        # 역할 삭제
        iam.delete_role(RoleName=role_name)
        print("✅ IAM 역할 삭제")
    except Exception as e:
        print(f"⚠️ IAM 삭제 실패: {e}")
    
    # 4. 로컬 파일 삭제
    if info_file.exists():
        info_file.unlink()
        print("✅ 배포 정보 파일 삭제")
    
    print("🎉 정리 완료!")

if __name__ == "__main__":
    main()