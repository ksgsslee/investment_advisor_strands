"""
deploy_lambda.py

Lambda 함수 배포 스크립트
Risk Manager Lambda 함수 배포
"""

import boto3
import zipfile
import json
import os
import time
from pathlib import Path

class Config:
    """Lambda 배포 설정"""
    REGION = 'us-west-2'
    FUNCTION_NAME = 'lambda-agentcore-risk-manager'

def create_lambda_package():
    """Lambda 함수 패키징"""
    current_dir = Path(__file__).parent
    zip_filename = 'lambda_function.zip'
    zip_path = current_dir / zip_filename
    lambda_file = current_dir / 'lambda_function.py'
    
    if not lambda_file.exists():
        raise FileNotFoundError(f"Lambda 함수 파일을 찾을 수 없습니다: {lambda_file}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(lambda_file, 'lambda_function.py')
    
    return str(zip_path)

def setup_iam_role():
    """IAM 역할 설정"""
    print("🔐 IAM 역할 설정 중...")
    iam = boto3.client('iam')
    role_name = f'{Config.FUNCTION_NAME}-role'
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Risk Manager Lambda execution role'
        )
        role_arn = response['Role']['Arn']
        
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        time.sleep(10)  # IAM 전파 대기
        return role_arn
        
    except iam.exceptions.EntityAlreadyExistsException:
        response = iam.get_role(RoleName=role_name)
        return response['Role']['Arn']

def load_layer_info():
    """Layer 배포 정보 로드"""
    layer_dir = Path(__file__).parent.parent / "lambda_layer"
    info_file = layer_dir / "layer_deployment_info.json"
    
    if not info_file.exists():
        return None
    
    with open(info_file, 'r') as f:
        layer_info = json.load(f)
    
    return layer_info.get('layer_version_arn')

def create_lambda_function(role_arn, layer_arn, zip_content):
    """Lambda 함수 생성"""
    print("🔧 Lambda 함수 생성 중...")
    lambda_client = boto3.client('lambda', region_name=Config.REGION)
    
    # 기존 함수 삭제
    if _check_function_exists(lambda_client, Config.FUNCTION_NAME):
        lambda_client.delete_function(FunctionName=Config.FUNCTION_NAME)
        time.sleep(5)
    
    response = lambda_client.create_function(
        FunctionName=Config.FUNCTION_NAME,
        Runtime="python3.12",
        Role=role_arn,
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': zip_content},
        Description='Risk Manager - News and market data analysis',
        Timeout=30,
        MemorySize=256,
        Layers=[layer_arn]
    )
    
    # 함수 활성화 대기
    _wait_for_function_active(lambda_client, Config.FUNCTION_NAME)
    
    return {
        'function_arn': response['FunctionArn'],
        'function_name': response['FunctionName']
    }

def _check_function_exists(lambda_client, function_name):
    """Lambda 함수 존재 여부 확인"""
    try:
        lambda_client.get_function(FunctionName=function_name)
        return True
    except lambda_client.exceptions.ResourceNotFoundException:
        return False

def _wait_for_function_active(lambda_client, function_name, max_attempts=15):
    """Lambda 함수가 활성 상태가 될 때까지 대기"""
    for attempt in range(max_attempts):
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            state = response['Configuration']['State']
            
            if state == 'Active':
                return
            elif state == 'Failed':
                reason = response['Configuration'].get('StateReason', 'Unknown error')
                raise Exception(f"Lambda 함수 활성화 실패: {reason}")
            
            time.sleep(2)
            
        except Exception as e:
            if attempt == max_attempts - 1:
                raise Exception(f"Lambda 함수 상태 확인 실패: {str(e)}")
            time.sleep(2)
    
    raise Exception("Lambda 함수 활성화 타임아웃")

def save_deployment_info(result):
    """배포 정보 저장"""
    info_file = Path(__file__).parent / "lambda_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(result, f, indent=2)
    return str(info_file)

def main():
    try:
        print("🚀 Risk Manager Lambda 배포")
        
        # Layer 정보 확인
        layer_arn = load_layer_info()
        if not layer_arn:
            raise RuntimeError(
                "Layer가 없습니다. 먼저 Layer를 배포하세요:\n"
                "cd ../lambda_layer && python deploy_lambda_layer.py"
            )
        
        # Lambda 패키지 생성
        zip_filename = create_lambda_package()
        
        # IAM 역할 설정
        role_arn = setup_iam_role()
        
        # ZIP 파일 로드
        with open(zip_filename, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Lambda 함수 생성
        lambda_result = create_lambda_function(role_arn, layer_arn, zip_content)
        
        # 임시 파일 정리
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        
        # 배포 결과 구성
        result = {
            'function_name': lambda_result['function_name'],
            'function_arn': lambda_result['function_arn'],
            'region': Config.REGION,
            'deployed_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 배포 정보 저장
        info_file = save_deployment_info(result)
        
        print(f"\n🎉 Lambda 함수 배포 완료!")
        print(f"🔗 Function ARN: {result['function_arn']}")
        print(f"📄 배포 정보: {info_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Lambda 배포 실패: {e}")
        raise

if __name__ == "__main__":
    main()