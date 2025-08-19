"""
deploy_lambda.py
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
    """
    Lambda 함수 코드를 ZIP 파일로 패키징
    
    Lambda 배포를 위해 lambda_function.py 파일을 ZIP 형태로 압축합니다.
    AWS Lambda는 코드를 ZIP 파일 형태로만 업로드할 수 있습니다.
    
    Returns:
        str: 생성된 ZIP 파일의 경로
        
    Raises:
        FileNotFoundError: lambda_function.py 파일이 존재하지 않을 때
    """
    print("📦 ZIP 파일 생성 중...")
    
    # 현재 스크립트가 위치한 디렉토리 경로 획득
    current_dir = Path(__file__).parent
    zip_path = current_dir / Config.ZIP_FILENAME
    lambda_file = current_dir / 'lambda_function.py'
    
    # Lambda 함수 파일 존재 여부 확인
    if not lambda_file.exists():
        raise FileNotFoundError(f"Lambda 함수 파일을 찾을 수 없습니다: {lambda_file}")
    
    # ZIP 파일 생성 (압축률 최적화를 위해 ZIP_DEFLATED 사용)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(lambda_file, 'lambda_function.py')
    
    print("✅ ZIP 파일 생성 완료")
    return str(zip_path)


def create_lambda_role():
    """
    Lambda 실행을 위한 IAM 역할 생성
    
    Lambda 함수가 AWS 서비스에 접근할 수 있도록 하는 IAM 역할을 생성합니다.
    기본적으로 CloudWatch Logs에 로그를 쓸 수 있는 권한을 부여합니다.
    
    Returns:
        str: 생성된 IAM 역할의 ARN
        
    Note:
        - 역할이 이미 존재하면 기존 역할의 ARN을 반환
        - IAM 역할 생성 후 전파를 위해 10초 대기
    """
    print("🔐 IAM 역할 설정 중...")
    iam = boto3.client('iam')
    
    # Lambda 서비스가 이 역할을 사용할 수 있도록 하는 신뢰 정책
    # 이 정책이 없으면 Lambda가 역할을 assume할 수 없음
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},  # Lambda 서비스만 이 역할 사용 가능
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # 새 IAM 역할 생성
        response = iam.create_role(
            RoleName=Config.ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Portfolio Architect Lambda execution role for ETF data processing'
        )
        role_arn = response['Role']['Arn']
        
        # Lambda 기본 실행 권한 연결 (CloudWatch Logs 접근 권한 포함)
        iam.attach_role_policy(
            RoleName=Config.ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        print("✅ 새 IAM 역할 생성 완료")
        print("⏳ IAM 역할 전파 대기 중...")
        time.sleep(10)  # IAM 역할이 AWS 전체에 전파될 때까지 대기 (중요!)
        return role_arn
        
    except iam.exceptions.EntityAlreadyExistsException:
        # 동일한 이름의 역할이 이미 존재하는 경우
        response = iam.get_role(RoleName=Config.ROLE_NAME)
        print("♻️ 기존 IAM 역할 사용")
        return response['Role']['Arn']

def load_layer_info():
    """
    Layer 배포 정보 로드
    
    Returns:
        str: Layer Version ARN (없으면 None)
    """
    # lambda_layer 폴더에서 배포 정보 찾기
    layer_dir = Path(__file__).parent.parent / "lambda_layer"
    info_file = layer_dir / "layer_deployment_info.json"
    
    if not info_file.exists():
        print("ℹ️ Layer 정보 없음 - Layer 없이 배포")
        return None
    
    with open(info_file, 'r') as f:
        layer_info = json.load(f)
    
    layer_arn = layer_info.get('layer_version_arn')
    print(f"📦 Layer 연결: {layer_arn}")
    return layer_arn


def deploy_lambda_function():
    """
    Lambda 함수 배포 메인 로직
    
    ZIP 파일 생성, IAM 역할 설정, Lambda 함수 생성/업데이트를 순차적으로 실행합니다.
    함수가 이미 존재하는 경우 코드와 설정을 업데이트합니다.
    
    Returns:
        str: 배포된 Lambda 함수의 ARN
        
    Process:
        1. ZIP 파일 생성
        2. IAM 역할 생성/조회
        3. Lambda 함수 생성 또는 업데이트
        4. 임시 파일 정리
        5. 함수 활성화 대기
    """
    print("🔨 Lambda 함수 배포 중...")
    lambda_client = boto3.client('lambda', region_name=Config.REGION)
    
    # 1. 배포용 ZIP 파일 생성
    zip_filename = create_lambda_zip()
    
    # 2. Lambda 실행용 IAM 역할 준비
    role_arn = create_lambda_role()
    
    # 2.5. Layer 정보 로드
    layer_arn = load_layer_info()
    
    # 3. ZIP 파일을 메모리로 로드
    print("📤 Lambda 함수 업로드 중...")
    with open(zip_filename, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    # 4. 기존 함수 존재 여부 확인
    function_exists = _check_function_exists(lambda_client, Config.FUNCTION_NAME)
    
    if function_exists:
        # 4-A. 기존 함수가 있으면 삭제
        print("♻️ 기존 함수 삭제 중...")
        lambda_client.delete_function(FunctionName=Config.FUNCTION_NAME)
        print("🗑️ 기존 함수 삭제 완료")
        
        # 삭제 완료 대기
        print("⏳ 삭제 완료 대기 중...")
        time.sleep(5)
    
    # 4-B. 새 Lambda 함수 생성
    print("🔨 새 Lambda 함수 생성 중...")
    
    # Lambda 함수 설정 구성
    function_config = {
        'FunctionName': Config.FUNCTION_NAME,
        'Runtime': Config.RUNTIME,                    # Python 3.12 런타임
        'Role': role_arn,                            # 실행 역할 ARN
        'Handler': 'lambda_function.lambda_handler',  # 진입점 함수
        'Code': {'ZipFile': zip_content},            # 함수 코드 (ZIP 바이너리)
        'Description': 'Portfolio Architect - ETF data retrieval and portfolio analysis tool',
        'Timeout': Config.TIMEOUT,                   # 30초 타임아웃
        'MemorySize': Config.MEMORY_SIZE             # 256MB 메모리 (yfinance 사용을 위해)
    }
    
    # Layer가 있으면 추가
    if layer_arn:
        function_config['Layers'] = [layer_arn]
        print(f"📦 Layer 연결됨: {layer_arn}")
    
    response = lambda_client.create_function(**function_config)
    function_arn = response['FunctionArn']
    print("✅ 새 Lambda 함수 생성 완료")
    
    # 5. 임시 ZIP 파일 정리
    print("🧹 임시 파일 정리 중...")
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
    
    # 6. Lambda 함수가 완전히 활성화될 때까지 대기
    print("⏳ Lambda 함수 활성화 대기 중...")
    _wait_for_function_active(lambda_client, Config.FUNCTION_NAME)
    print("✅ Lambda 함수 활성화 완료")
    
    return function_arn



def _check_function_exists(lambda_client, function_name):
    """
    Lambda 함수 존재 여부 확인
    
    Args:
        lambda_client: AWS Lambda 클라이언트
        function_name (str): 확인할 Lambda 함수명
        
    Returns:
        bool: 함수가 존재하면 True, 없으면 False
    """
    try:
        lambda_client.get_function(FunctionName=function_name)
        return True
    except lambda_client.exceptions.ResourceNotFoundException:
        return False


def _wait_for_function_active(lambda_client, function_name, max_attempts=15):
    """
    Lambda 함수가 활성 상태가 될 때까지 대기
    
    Lambda 함수 생성/업데이트 후 즉시 호출 가능한 상태가 되지 않을 수 있으므로
    'Active' 상태가 될 때까지 폴링하며 대기합니다.
    
    Args:
        lambda_client: AWS Lambda 클라이언트
        function_name (str): 대기할 Lambda 함수명
        max_attempts (int): 최대 시도 횟수 (기본값: 15회, 총 30초)
        
    Raises:
        Exception: 함수 활성화 실패 또는 타임아웃 시
        
    Note:
        - 각 시도마다 2초씩 대기
        - 'Failed' 상태 감지 시 즉시 예외 발생
        - 최대 30초(15회 × 2초) 대기
    """
    for attempt in range(max_attempts):
        try:
            # Lambda 함수 상태 조회
            response = lambda_client.get_function(FunctionName=function_name)
            state = response['Configuration']['State']
            
            if state == 'Active':
                # 함수가 활성화됨 - 정상 완료
                return
            elif state == 'Failed':
                # 함수 활성화 실패 - 즉시 예외 발생
                reason = response['Configuration'].get('StateReason', 'Unknown error')
                raise Exception(f"Lambda 함수 활성화 실패: {reason}")
            
            # 아직 활성화되지 않음 - 2초 대기 후 재시도
            time.sleep(2)
            
        except Exception as e:
            # 마지막 시도에서 실패하면 예외 발생
            if attempt == max_attempts - 1:
                raise Exception(f"Lambda 함수 상태 확인 실패: {str(e)}")
            time.sleep(2)
    
    # 최대 시도 횟수 초과 - 타임아웃
    raise Exception("Lambda 함수 활성화 타임아웃")

def save_deployment_info(function_arn):
    """
    배포 정보를 JSON 파일로 저장
    
    배포된 Lambda 함수의 정보를 JSON 파일로 저장하여
    다른 스크립트(Gateway 배포 등)에서 참조할 수 있도록 합니다.
    
    Args:
        function_arn (str): 배포된 Lambda 함수의 ARN
        
    Returns:
        str: 저장된 JSON 파일의 경로
        
    Note:
        - 파일명: lambda_deployment_info.json
        - 저장 위치: 현재 스크립트와 같은 디렉토리
        - 기존 파일이 있으면 덮어씀
    """
    current_dir = Path(__file__).parent
    
    # 배포 정보 딕셔너리 구성
    deployment_info = {
        "function_name": Config.FUNCTION_NAME,    # Lambda 함수명
        "function_arn": function_arn,             # Lambda 함수 ARN (Gateway에서 사용)
        "region": Config.REGION,                  # AWS 리전
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")  # 배포 시각
    }
    
    # JSON 파일로 저장
    info_file = current_dir / "lambda_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    return str(info_file)


def main():
    """
    메인 실행 함수
    
    Portfolio Architect Lambda 함수의 전체 배포 프로세스를 관리합니다.
    배포 성공 시 함수 ARN을 반환하고, 실패 시 예외를 발생시킵니다.
    
    Returns:
        str: 배포된 Lambda 함수의 ARN
        
    Raises:
        Exception: 배포 과정에서 발생한 모든 예외
        
    Process:
        1. 배포 시작 메시지 출력
        2. Lambda 함수 배포 실행
        3. 배포 정보 JSON 파일 저장
        4. 성공/실패 메시지 출력
    """
    try:
        # 배포 시작 헤더 출력
        print("=" * 50)
        print(f"🚀 Portfolio Architect Lambda 배포 시작")
        
        # Lambda 함수 배포 실행
        function_arn = deploy_lambda_function()
        
        # 배포 정보를 JSON 파일로 저장 (다른 스크립트에서 참조용)
        info_file = save_deployment_info(function_arn)
        
        # 배포 성공 메시지 출력
        print("=" * 50)
        print("🎉 배포 성공!")
        print(f"📄 배포 정보: {info_file}")
       
        return function_arn
        
    except Exception as e:
        # 배포 실패 메시지 출력 후 예외 재발생
        print("=" * 50)
        print(f"❌ 배포 실패: {str(e)}")
        raise


if __name__ == "__main__":
    main()
