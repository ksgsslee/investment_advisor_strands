"""
Portfolio Architect Lambda 함수 배포 스크립트

이 스크립트는 포트폴리오 설계를 위한 Lambda 함수를 AWS에 배포합니다.
주요 기능:
- ETF 상품 목록 조회 (get_available_products)
- 실시간 가격 데이터 조회 (get_product_data)
"""

import boto3
import zipfile
import json
import os
import time
from pathlib import Path


# 설정 상수
class Config:
    """배포 설정 상수"""
    FUNCTION_NAME = 'agentcore-portfolio-architect'
    ROLE_NAME = 'agentcore-portfolio-architect-role'
    REGION = 'us-west-2'
    RUNTIME = 'python3.12'
    TIMEOUT = 30
    MEMORY_SIZE = 256  # 128MB에서 256MB로 증가 (yfinance 사용)
    ZIP_FILENAME = 'lambda_function.zip'


def create_lambda_zip():
    """Lambda 함수 코드를 ZIP 파일로 패키징"""
    current_dir = Path(__file__).parent
    zip_path = current_dir / Config.ZIP_FILENAME
    lambda_file = current_dir / 'lambda_function.py'
    
    if not lambda_file.exists():
        raise FileNotFoundError(f"Lambda 함수 파일을 찾을 수 없습니다: {lambda_file}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(lambda_file, 'lambda_function.py')
    
    return str(zip_path)


def create_lambda_role():
    """Lambda 실행을 위한 IAM 역할 생성"""
    iam = boto3.client('iam')
    
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
            RoleName=Config.ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Portfolio Architect Lambda 실행 역할 - ETF 데이터 조회 및 처리'
        )
        role_arn = response['Role']['Arn']
        
        iam.attach_role_policy(
            RoleName=Config.ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        time.sleep(10)  # IAM 역할 전파 대기
        return role_arn
        
    except iam.exceptions.EntityAlreadyExistsException:
        response = iam.get_role(RoleName=Config.ROLE_NAME)
        return response['Role']['Arn']

def deploy_lambda_function():
    """Lambda 함수 배포 메인 로직"""
    lambda_client = boto3.client('lambda', region_name=Config.REGION)
    
    zip_filename = create_lambda_zip()
    role_arn = create_lambda_role()
    
    with open(zip_filename, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    try:
        response = lambda_client.create_function(
            FunctionName=Config.FUNCTION_NAME,
            Runtime=Config.RUNTIME,
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='Portfolio Architect - ETF 데이터 조회 및 포트폴리오 분석 도구',
            Timeout=Config.TIMEOUT,
            MemorySize=Config.MEMORY_SIZE
        )
        function_arn = response['FunctionArn']
        
    except lambda_client.exceptions.ResourceConflictException:
        lambda_client.update_function_code(
            FunctionName=Config.FUNCTION_NAME,
            ZipFile=zip_content
        )
        
        lambda_client.update_function_configuration(
            FunctionName=Config.FUNCTION_NAME,
            Runtime=Config.RUNTIME,
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Description='Portfolio Architect - ETF 데이터 조회 및 포트폴리오 분석 도구',
            Timeout=Config.TIMEOUT,
            MemorySize=Config.MEMORY_SIZE
        )
        
        response = lambda_client.get_function(FunctionName=Config.FUNCTION_NAME)
        function_arn = response['Configuration']['FunctionArn']
    
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
    
    _wait_for_function_active(lambda_client, Config.FUNCTION_NAME)
    return function_arn


def _wait_for_function_active(lambda_client, function_name, max_attempts=15):
    """Lambda 함수가 활성 상태가 될 때까지 대기"""
    for attempt in range(max_attempts):
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            state = response['Configuration']['State']
            
            if state == 'Active':
                return
            elif state == 'Failed':
                raise Exception(f"Lambda 함수 활성화 실패: {response['Configuration'].get('StateReason', 'Unknown error')}")
            
            time.sleep(2)
            
        except Exception as e:
            if attempt == max_attempts - 1:
                raise Exception(f"Lambda 함수 상태 확인 실패: {str(e)}")
            time.sleep(2)
    
    raise Exception("Lambda 함수 활성화 타임아웃")

def save_deployment_info(function_arn):
    """배포 정보를 JSON 파일로 저장"""
    current_dir = Path(__file__).parent
    deployment_info = {
        "function_name": Config.FUNCTION_NAME,
        "function_arn": function_arn,
        "region": Config.REGION,
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = current_dir / "lambda_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    return str(info_file)


def main():
    """메인 실행 함수"""
    try:
        print(f"🚀 Lambda 배포 시작: {Config.FUNCTION_NAME}")
        
        function_arn = deploy_lambda_function()
        info_file = save_deployment_info(function_arn)
        
        print(f"✅ 배포 완료: {function_arn}")
        print(f"📄 배포 정보 저장: {info_file}")
        
        return function_arn
        
    except Exception as e:
        print(f"❌ 배포 실패: {str(e)}")
        raise


if __name__ == "__main__":
    main()
