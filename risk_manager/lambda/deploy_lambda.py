"""
deploy_lambda.py
Risk Manager Lambda 함수 배포 스크립트

이 스크립트는 리스크 관리를 위한 Lambda 함수를 AWS에 배포합니다.
yfinance Layer와 함께 배포되어 실시간 뉴스 및 거시경제 데이터 조회 기능을 제공합니다.

주요 기능:
- ETF 뉴스 조회 (get_product_news)
- 거시경제 지표 조회 (get_market_data)
- yfinance Layer 자동 연결
- IAM 역할 자동 생성
"""

import boto3
import zipfile
import json
import os
import time
from pathlib import Path

# ================================
# 설정 상수
# ================================

class Config:
    """Lambda 배포 설정 상수"""
    FUNCTION_NAME = 'agentcore-risk-manager'
    ROLE_NAME = 'lambda-risk-manager-role'
    REGION = 'us-west-2'
    RUNTIME = 'python3.12'
    TIMEOUT = 30
    MEMORY_SIZE = 256  # yfinance 사용을 위해 256MB 할당
    ZIP_FILENAME = 'lambda_function.zip'

# ================================
# 유틸리티 함수들
# ================================

def create_lambda_zip():
    """
    Lambda 함수 코드를 ZIP 파일로 패키징
    
    Returns:
        str: 생성된 ZIP 파일의 경로
    """
    print("📦 ZIP 파일 생성 중...")
    
    current_dir = Path(__file__).parent
    zip_path = current_dir / Config.ZIP_FILENAME
    lambda_file = current_dir / 'lambda_function.py'
    
    if not lambda_file.exists():
        raise FileNotFoundError(f"Lambda 함수 파일을 찾을 수 없습니다: {lambda_file}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(lambda_file, 'lambda_function.py')
    
    print("✅ ZIP 파일 생성 완료")
    return str(zip_path)

def create_lambda_role():
    """
    Lambda 실행을 위한 IAM 역할 생성
    
    Returns:
        str: 생성된 IAM 역할의 ARN
    """
    print("🔐 IAM 역할 설정 중...")
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
            Description='Risk Manager Lambda execution role for news and market data processing'
        )
        role_arn = response['Role']['Arn']
        
        iam.attach_role_policy(
            RoleName=Config.ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        print("✅ 새 IAM 역할 생성 완료")
        print("⏳ IAM 역할 전파 대기 중...")
        time.sleep(10)
        return role_arn
        
    except iam.exceptions.EntityAlreadyExistsException:
        response = iam.get_role(RoleName=Config.ROLE_NAME)
        print("♻️ 기존 IAM 역할 사용")
        return response['Role']['Arn']

def load_layer_info():
    """
    Layer 배포 정보 로드 (필수)
    
    Returns:
        str: Layer Version ARN
    """
    layer_dir = Path(__file__).parent.parent / "lambda_layer"
    info_file = layer_dir / "layer_deployment_info.json"
    
    if not info_file.exists():
        return None
    
    with open(info_file, 'r') as f:
        layer_info = json.load(f)
    
    layer_arn = layer_info.get('layer_version_arn')
    if not layer_arn:
        return None
        
    print(f"📋 Layer 정보 로드: {layer_arn}")
    return layer_arn

def deploy_lambda_function():
    """
    Lambda 함수 배포 메인 로직
    
    Returns:
        str: 배포된 Lambda 함수의 ARN
    """
    print("🔨 Lambda 함수 배포 중...")
    lambda_client = boto3.client('lambda', region_name=Config.REGION)
    
    # 1. 배포용 ZIP 파일 생성
    zip_filename = create_lambda_zip()
    
    # 2. Lambda 실행용 IAM 역할 준비
    role_arn = create_lambda_role()
    
    # 3. Layer 정보 로드 (필수)
    layer_arn = load_layer_info()
    if not layer_arn:
        print("⚠️ Layer가 없습니다. 먼저 Layer를 배포하세요:")
        print("   cd ../lambda_layer && python deploy_layer.py")
        raise RuntimeError("Layer 배포가 필요합니다.")
    
    # 4. ZIP 파일을 메모리로 로드
    print("📤 Lambda 함수 업로드 중...")
    with open(zip_filename, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    # 5. 기존 함수 존재 여부 확인
    function_exists = _check_function_exists(lambda_client, Config.FUNCTION_NAME)
    
    if function_exists:
        print("♻️ 기존 함수 삭제 중...")
        lambda_client.delete_function(FunctionName=Config.FUNCTION_NAME)
        print("🗑️ 기존 함수 삭제 완료")
        
        print("⏳ 삭제 완료 대기 중...")
        time.sleep(5)
    
    # 6. 새 Lambda 함수 생성
    print("🔨 새 Lambda 함수 생성 중...")
    print(f"📦 Layer 연결: {layer_arn}")
    
    response = lambda_client.create_function(
        FunctionName=Config.FUNCTION_NAME,
        Runtime=Config.RUNTIME,
        Role=role_arn,
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': zip_content},
        Description='Risk Manager - News and market data analysis for portfolio risk management',
        Timeout=Config.TIMEOUT,
        MemorySize=Config.MEMORY_SIZE,
        Layers=[layer_arn]
    )
    function_arn = response['FunctionArn']
    print("✅ 새 Lambda 함수 생성 완료")
    
    # 7. 임시 ZIP 파일 정리
    print("🧹 임시 파일 정리 중...")
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
    
    # 8. Lambda 함수 활성화 대기
    print("⏳ Lambda 함수 활성화 대기 중...")
    _wait_for_function_active(lambda_client, Config.FUNCTION_NAME)
    print("✅ Lambda 함수 활성화 완료")
    
    return function_arn

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

def save_deployment_info(function_arn):
    """
    배포 정보를 JSON 파일로 저장
    
    Args:
        function_arn (str): 배포된 Lambda 함수의 ARN
        
    Returns:
        str: 저장된 JSON 파일의 경로
    """
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
    """
    메인 실행 함수
    
    Risk Manager Lambda 함수의 전체 배포 프로세스를 관리합니다.
    """
    try:
        print("=" * 50)
        print(f"🚀 Risk Manager Lambda 배포 시작")
        
        function_arn = deploy_lambda_function()
        info_file = save_deployment_info(function_arn)
        
        print("=" * 50)
        print("🎉 배포 성공!")
        print(f"📄 배포 정보: {info_file}")
       
        return function_arn
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ 배포 실패: {str(e)}")
        raise

if __name__ == "__main__":
    main()