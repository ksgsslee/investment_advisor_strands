"""
cleanup.py

Risk Manager 시스템 정리 스크립트
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
    
    # Risk Manager 정보
    risk_manager_info = None
    risk_manager_file = current_dir / "deployment_info.json"
    if risk_manager_file.exists():
        with open(risk_manager_file) as f:
            risk_manager_info = json.load(f)
    
    # Gateway 정보
    gateway_info = None
    gateway_file = current_dir / "gateway" / "gateway_deployment_info.json"
    if gateway_file.exists():
        with open(gateway_file) as f:
            gateway_info = json.load(f)
    
    # Lambda 정보
    lambda_info = None
    lambda_file = current_dir / "lambda" / "lambda_deployment_info.json"
    if lambda_file.exists():
        with open(lambda_file) as f:
            lambda_info = json.load(f)
    
    # Lambda Layer 정보
    layer_info = None
    layer_file = current_dir / "lambda_layer" / "layer_deployment_info.json"
    if layer_file.exists():
        with open(layer_file) as f:
            layer_info = json.load(f)
    
    return risk_manager_info, gateway_info, lambda_info, layer_info

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

def delete_gateway(gateway_id, region):
    """Gateway 삭제"""
    try:
        client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        # Target들 먼저 삭제
        targets = client.list_gateway_targets(gatewayIdentifier=gateway_id).get('items', [])
        for target in targets:
            client.delete_gateway_target(
                gatewayIdentifier=gateway_id,
                targetId=target['targetId']
            )
        
        time.sleep(3)
        client.delete_gateway(gatewayIdentifier=gateway_id)
        print(f"✅ Gateway 삭제: {gateway_id} (리전: {region})")
        return True
    except Exception as e:
        print(f"⚠️ Gateway 삭제 실패: {e}")
        return False

def delete_lambda_function(function_name, region):
    """Lambda 함수 삭제"""
    try:
        lambda_client = boto3.client('lambda', region_name=region)
        lambda_client.delete_function(FunctionName=function_name)
        print(f"✅ Lambda 함수 삭제: {function_name} (리전: {region})")
        return True
    except Exception as e:
        print(f"⚠️ Lambda 함수 삭제 실패: {e}")
        return False

def delete_lambda_layer(layer_name, region):
    """Lambda Layer 삭제"""
    try:
        lambda_client = boto3.client('lambda', region_name=region)
        
        # Layer의 모든 버전 조회
        versions = lambda_client.list_layer_versions(LayerName=layer_name)
        
        # 각 버전 삭제
        for version in versions['LayerVersions']:
            version_number = version['Version']
            lambda_client.delete_layer_version(
                LayerName=layer_name,
                VersionNumber=version_number
            )
            print(f"✅ Lambda Layer 버전 삭제: {layer_name} v{version_number}")
        
        return True
    except Exception as e:
        print(f"⚠️ Lambda Layer 삭제 실패 {layer_name}: {e}")
        return False

def delete_s3_bucket(bucket_name, region):
    """S3 버킷 삭제 (객체 포함)"""
    try:
        s3 = boto3.client('s3', region_name=region)
        
        # 버킷 존재 확인
        try:
            s3.head_bucket(Bucket=bucket_name)
        except:
            print(f"ℹ️ S3 버킷이 존재하지 않음: {bucket_name}")
            return True
        
        # 버킷 내 모든 객체 삭제
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                objects = [{'Key': obj['Key']} for obj in page['Contents']]
                s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
        
        # 버킷 삭제
        s3.delete_bucket(Bucket=bucket_name)
        print(f"✅ S3 버킷 삭제: {bucket_name} (리전: {region})")
        return True
    except Exception as e:
        print(f"⚠️ S3 버킷 삭제 실패 {bucket_name}: {e}")
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
        current_dir / "gateway" / "gateway_deployment_info.json",
        current_dir / "lambda" / "lambda_deployment_info.json",
        current_dir / "lambda_layer" / "layer_deployment_info.json",
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
    print("🧹 Risk Manager 시스템 정리")
    
    # 배포 정보 로드
    risk_manager_info, gateway_info, lambda_info, layer_info = load_deployment_info()
    
    if not risk_manager_info and not gateway_info and not lambda_info and not layer_info:
        print("⚠️ 배포 정보가 없습니다.")
        return
    
    # 확인
    response = input("\n정말로 모든 리소스를 삭제하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 취소됨")
        return
    
    print("\n🗑️ AWS 리소스 삭제 중...")
    
    # 1. Risk Manager Runtime 삭제
    if risk_manager_info and 'agent_arn' in risk_manager_info:
        region = risk_manager_info.get('region', 'us-west-2')
        delete_runtime(risk_manager_info['agent_arn'], region)
    
    # 2. Gateway 삭제
    if gateway_info and 'gateway_id' in gateway_info:
        region = gateway_info.get('region', 'us-west-2')
        delete_gateway(gateway_info['gateway_id'], region)
    
    # 3. Lambda 함수 삭제
    if lambda_info and 'function_name' in lambda_info:
        region = lambda_info.get('region', 'us-west-2')
        delete_lambda_function(lambda_info['function_name'], region)
    
    # 4. Lambda Layer 삭제
    if layer_info and 'layer_name' in layer_info:
        region = layer_info.get('region', 'us-west-2')
        delete_lambda_layer(layer_info['layer_name'], region)
    
    # 5. S3 버킷 삭제 (Layer 배포용)
    if layer_info and 's3_bucket' in layer_info:
        region = layer_info.get('region', 'us-west-2')
        delete_s3_bucket(layer_info['s3_bucket'], region)
    
    # 6. ECR 리포지토리 삭제
    if risk_manager_info and 'ecr_repo_name' in risk_manager_info and risk_manager_info['ecr_repo_name']:
        region = risk_manager_info.get('region', 'us-west-2')
        delete_ecr_repo(risk_manager_info['ecr_repo_name'], region)
    
    # 7. IAM 역할들 삭제
    if risk_manager_info and 'iam_role_name' in risk_manager_info:
        delete_iam_role(risk_manager_info['iam_role_name'])
    
    if gateway_info and 'iam_role_name' in gateway_info:
        delete_iam_role(gateway_info['iam_role_name'])
    
    # Lambda 역할은 자동 생성된 이름 패턴 사용
    if lambda_info and 'function_name' in lambda_info:
        lambda_role_name = f"{lambda_info['function_name']}-role"
        delete_iam_role(lambda_role_name)
    
    # 8. Cognito 리소스 삭제
    if gateway_info and 'user_pool_id' in gateway_info:
        region = gateway_info.get('region', 'us-west-2')
        delete_cognito_resources(gateway_info['user_pool_id'], region)
    
    print("\n🎉 AWS 리소스 정리 완료!")
    
    # 9. 로컬 파일들 정리
    if input("\n로컬 생성 파일들도 삭제하시겠습니까? (y/N): ").lower() == 'y':
        cleanup_local_files()
    else:
        print("📁 로컬 파일들은 유지됩니다.")

if __name__ == "__main__":
    main()