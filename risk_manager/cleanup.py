#!/usr/bin/env python3
"""
risk_manager cleanup.py
간단하고 깔끔한 Risk Manager 전체 시스템 정리

"""

import json
import boto3
from pathlib import Path
import sys

# Config 가져오기
sys.path.insert(0, str(Path(__file__).parent))
from deploy import Config

def load_deployment_info():
    """배포 정보 파일들 로드"""
    base_dir = Path(__file__).parent
    
    info_files = {
        'main': base_dir / 'deployment_info.json',
        'gateway': base_dir / 'gateway' / 'gateway_deployment_info.json', 
        'lambda': base_dir / 'lambda' / 'lambda_deployment_info.json',
        'layer': base_dir / 'lambda_layer' / 'layer_deployment_info.json'
    }
    
    deployment_info = {}
    for name, file_path in info_files.items():
        if file_path.exists():
            with open(file_path) as f:
                deployment_info[name] = json.load(f)
                print(f"✅ {name} 배포 정보 로드")
        else:
            print(f"⚠️ {name} 배포 정보 없음")
    
    return deployment_info

def delete_runtimes(deployment_info):
    """AgentCore Runtime들 삭제"""
    print("🗑️ Runtime 삭제 중...")
    
    client = boto3.client('bedrock-agentcore-control', region_name=Config.REGION)
    
    # Main Runtime 삭제
    if 'main' in deployment_info and 'agent_arn' in deployment_info['main']:
        try:
            runtime_id = deployment_info['main']['agent_arn'].split('/')[-1]
            client.delete_agent_runtime(agentRuntimeId=runtime_id)
            print(f"  ✅ Main Runtime: {runtime_id}")
        except Exception as e:
            print(f"  ⚠️ Main Runtime 실패: {e}")

def delete_lambda_layer_s3_bucket():
    """Lambda Layer용 S3 버킷 삭제"""
    print("🗑️ Lambda Layer S3 버킷 삭제 중...")
    
    try:
        s3_client = boto3.client('s3', region_name=Config.REGION)
        sts_client = boto3.client('sts', region_name=Config.REGION)
        
        # 계정 ID로 버킷명 생성 (deploy_lambda_layer.py와 동일한 패턴)
        account_id = sts_client.get_caller_identity()["Account"]
        bucket_name = f"layer-yfinance-risk-manager-{account_id}"
        
        # 버킷 존재 확인
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                print("  ⚠️ S3 버킷이 존재하지 않음")
                return
            else:
                raise
        
        # 버킷 내 모든 객체 삭제
        objects = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in objects:
            delete_keys = [{'Key': obj['Key']} for obj in objects['Contents']]
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': delete_keys}
            )
        
        # 버킷 삭제
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"  ✅ S3 버킷: {bucket_name}")
        
    except Exception as e:
        print(f"  ⚠️ S3 버킷 삭제 실패: {e}")

def delete_lambda_layer(deployment_info):
    """Lambda Layer 삭제 (먼저 삭제해야 함)"""
    print("🗑️ Lambda Layer 삭제 중...")
    
    if 'layer' not in deployment_info or 'layer_name' not in deployment_info['layer']:
        print("  ⚠️ Layer 정보 없음")
        return
    
    try:
        lambda_client = boto3.client('lambda', region_name=Config.REGION)
        layer_name = deployment_info['layer']['layer_name']
        
        # 모든 버전 삭제
        versions = lambda_client.list_layer_versions(LayerName=layer_name)
        for version in versions['LayerVersions']:
            lambda_client.delete_layer_version(
                LayerName=layer_name,
                VersionNumber=version['Version']
            )
        
        print(f"  ✅ Lambda Layer: {layer_name}")
    except Exception as e:
        print(f"  ⚠️ Layer 삭제 실패: {e}")
    
    # S3 버킷도 삭제
    delete_lambda_layer_s3_bucket()

def delete_lambda_function(deployment_info):
    """Lambda 함수 삭제"""
    print("🗑️ Lambda 함수 삭제 중...")
    
    if 'lambda' not in deployment_info or 'function_name' not in deployment_info['lambda']:
        print("  ⚠️ Lambda 정보 없음")
        return
    
    try:
        lambda_client = boto3.client('lambda', region_name=Config.REGION)
        function_name = deployment_info['lambda']['function_name']
        lambda_client.delete_function(FunctionName=function_name)
        print(f"  ✅ Lambda 함수: {function_name}")
    except Exception as e:
        print(f"  ⚠️ Lambda 삭제 실패: {e}")

def delete_cognito_resources(deployment_info):
    """Cognito User Pool 삭제"""
    print("🗑️ Cognito 리소스 삭제 중...")
    
    if 'gateway' not in deployment_info or 'user_pool_id' not in deployment_info['gateway']:
        print("  ⚠️ Cognito 정보 없음")
        return
    
    try:
        cognito = boto3.client('cognito-idp', region_name=Config.REGION)
        user_pool_id = deployment_info['gateway']['user_pool_id']
        
        # User Pool 도메인 삭제 (있는 경우)
        try:
            # describe_user_pool로 도메인 정보 확인
            pool_info = cognito.describe_user_pool(UserPoolId=user_pool_id)
            if 'Domain' in pool_info['UserPool']:
                domain = pool_info['UserPool']['Domain']
                cognito.delete_user_pool_domain(
                    Domain=domain,
                    UserPoolId=user_pool_id
                )
                print(f"  ✅ User Pool 도메인: {domain}")
        except Exception as e:
            print(f"  ⚠️ 도메인 삭제 실패: {e}")
        
        # User Pool 클라이언트들 삭제
        clients = cognito.list_user_pool_clients(UserPoolId=user_pool_id)
        for client in clients['UserPoolClients']:
            cognito.delete_user_pool_client(
                UserPoolId=user_pool_id,
                ClientId=client['ClientId']
            )
        
        # User Pool 삭제
        cognito.delete_user_pool(UserPoolId=user_pool_id)
        print(f"  ✅ User Pool: {user_pool_id}")
    except Exception as e:
        print(f"  ⚠️ Cognito 삭제 실패: {e}")

def delete_ecr_repositories():
    """ECR 리포지토리들 삭제"""
    print("🗑️ ECR 리포지토리 삭제 중...")
    
    ecr = boto3.client('ecr', region_name=Config.REGION)
    
    repos = [
        f"bedrock-agentcore-{Config.AGENT_NAME}",
        "bedrock-agentcore-gateway-risk-manager"
    ]
    
    for repo_name in repos:
        try:
            ecr.delete_repository(repositoryName=repo_name, force=True)
            print(f"  ✅ ECR: {repo_name}")
        except Exception as e:
            print(f"  ⚠️ ECR {repo_name} 실패: {e}")

def delete_iam_roles():
    """IAM 역할들 삭제"""
    print("🗑️ IAM 역할 삭제 중...")
    
    iam = boto3.client('iam')
    
    roles = [
        f'agentcore-runtime-{Config.AGENT_NAME}-role',
        'agentcore-gateway-gateway-risk-manager-role',
        'agentcore-lambda-risk-manager-role'
    ]
    
    for role_name in roles:
        try:
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
            print(f"  ✅ IAM 역할: {role_name}")
        except Exception as e:
            print(f"  ⚠️ IAM {role_name} 실패: {e}")

def cleanup_files():
    """생성된 파일들 정리"""
    print("🗑️ 생성된 파일들 정리 중...")
    
    base_dir = Path(__file__).parent
    
    files_to_delete = [
        # Main 파일들
        base_dir / 'deployment_info.json',
        base_dir / 'Dockerfile',
        base_dir / '.dockerignore',
        base_dir / '.bedrock_agentcore.yaml',
        
        # Gateway 파일들
        base_dir / 'gateway' / 'gateway_deployment_info.json',
        
        # Lambda 파일들
        base_dir / 'lambda' / 'lambda_deployment_info.json',
        
        # Lambda Layer 파일들
        base_dir / 'lambda_layer' / 'layer_deployment_info.json',
    ]
    
    for file_path in files_to_delete:
        if file_path.exists():
            file_path.unlink()
            print(f"  ✅ 삭제: {file_path.relative_to(base_dir)}")

def main():
    print(f"🧹 {Config.AGENT_NAME} 전체 시스템 정리")
    print("=" * 50)
    
    # 배포 정보 로드
    deployment_info = load_deployment_info()
    
    # 확인
    response = input("\n정말로 모든 리소스를 삭제하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 취소됨")
        return
    
    print("\n🚀 정리 시작...")
    
    # 1. Lambda Layer 삭제 (먼저 삭제)
    delete_lambda_layer(deployment_info)
    
    # 2. Lambda 함수 삭제
    delete_lambda_function(deployment_info)
    
    # 3. Runtime들 삭제
    delete_runtimes(deployment_info)
    
    # 4. Cognito 리소스 삭제
    delete_cognito_resources(deployment_info)
    
    # 5. ECR 리포지토리들 삭제
    delete_ecr_repositories()
    
    # 6. IAM 역할들 삭제
    delete_iam_roles()
    
    # 7. 파일들 정리
    cleanup_files()
    
    print("\n🎉 정리 완료!")
    print("\n📋 정리된 항목:")
    print("• Lambda Layer")
    print("• Lambda 함수")
    print("• Risk Manager Runtime")
    print("• Cognito User Pool")
    print("• ECR 리포지토리들")
    print("• IAM 역할들")
    print("• 생성된 파일들")

if __name__ == "__main__":
    main()