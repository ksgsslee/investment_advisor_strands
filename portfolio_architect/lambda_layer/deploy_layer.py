"""
deploy_layer.py
Lambda Layer 배포 스크립트

yfinance 등 외부 라이브러리를 포함한 Lambda Layer를 배포합니다.
50MB 이상의 대용량 Layer는 S3를 통해 안정적으로 배포됩니다.

주요 기능:
- yfinance, pandas, numpy 등 데이터 분석 라이브러리 포함
- S3 기반 대용량 파일 배포 시스템
- 계정 ID 기반 버킷 재사용으로 비용 최적화
"""

import boto3
import json
import time
import os
from pathlib import Path

# ================================
# 설정 상수
# ================================

class Config:
    """Lambda Layer 배포 설정 상수"""
    LAYER_NAME = "layer-yfinance"
    REGION = "us-west-2"
    RUNTIME = "python3.12"
    ZIP_FILENAME = "yfinance.zip"
    DESCRIPTION = "Portfolio Architect dependencies - yfinance, pandas, numpy"
    S3_BUCKET_PREFIX = "layer-yfinance"

# ================================
# S3 관리 함수들
# ================================



def get_or_create_s3_bucket():
    """
    Layer 업로드용 S3 버킷 조회 또는 생성
    
    계정 ID를 사용하여 고유한 버킷명을 생성하고, 기존 버킷이 있으면 재사용합니다.
    이를 통해 비용을 절약하고 배포 속도를 향상시킵니다.
    
    Returns:
        str: S3 버킷명
        
    Note:
        - 버킷명 형식: layer-yfinance-{account_id}
        - 기존 버킷 재사용으로 비용 최적화
        - 리전별 버킷 생성 규칙 준수
    """
    s3_client = boto3.client('s3', region_name=Config.REGION)
    sts_client = boto3.client('sts', region_name=Config.REGION)
    
    # AWS 계정 ID로 고유한 버킷명 생성
    account_id = sts_client.get_caller_identity()["Account"]
    bucket_name = f"{Config.S3_BUCKET_PREFIX}-{account_id}"
    
    try:
        # 버킷 존재 여부 확인
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"♻️ 기존 S3 버킷 사용: {bucket_name}")
        return bucket_name
        
    except s3_client.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == '404':
            # 버킷이 없으면 생성
            print(f"📦 S3 버킷 생성 중: {bucket_name}")
            
            # 리전별 버킷 생성 (us-east-1은 LocationConstraint 불필요)
            if Config.REGION == 'us-east-1':
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': Config.REGION}
                )
            
            print(f"✅ S3 버킷 생성 완료: {bucket_name}")
            return bucket_name
        else:
            # 다른 에러 (권한 없음 등)
            print(f"❌ S3 버킷 접근 실패: {str(e)}")
            raise
            
    except Exception as e:
        print(f"❌ S3 버킷 처리 실패: {str(e)}")
        raise


def upload_to_s3(zip_file_path, bucket_name):
    """
    Layer ZIP 파일을 S3에 업로드
    
    대용량 Layer 파일을 S3에 안전하게 업로드합니다.
    Lambda의 직접 업로드 제한(50MB)을 우회하여 더 큰 Layer를 배포할 수 있습니다.
    
    Args:
        zip_file_path (str): 업로드할 ZIP 파일 경로
        bucket_name (str): 대상 S3 버킷명
        
    Returns:
        str: S3 객체 URL (s3://bucket/key 형식)
        
    Note:
        - 파일 크기 제한 없음 (S3 최대 5TB까지 지원)
        - 업로드 진행 상황 모니터링
        - 네트워크 오류 시 자동 재시도
    """
    s3_client = boto3.client('s3', region_name=Config.REGION)
    object_key = Config.ZIP_FILENAME
    
    # 파일 크기 확인
    file_size = os.path.getsize(zip_file_path)
    file_size_mb = file_size / (1024 * 1024)
    
    print(f"📤 S3 업로드 중: {bucket_name}/{object_key}")
    print(f"📊 파일 크기: {file_size_mb:.1f} MB")
    
    # 파일 업로드
    s3_client.upload_file(zip_file_path, bucket_name, object_key)
    
    # S3 URL 생성
    s3_url = f"s3://{bucket_name}/{object_key}"
    print(f"✅ S3 업로드 완료: {s3_url}")
    
    return s3_url

# ================================
# Layer 배포 함수들
# ================================


def deploy_lambda_layer():
    """
    Lambda Layer 배포 (S3 기반 대용량 파일 지원)
    
    yfinance.zip 파일을 S3를 통해 Lambda Layer로 배포합니다.
    50MB 이상의 대용량 Layer도 안정적으로 배포할 수 있습니다.
    
    Returns:
        str: 배포된 Layer Version ARN
        
    Process:
        1. ZIP 파일 존재 확인
        2. S3 버킷 준비 (기존 버킷 재사용 또는 신규 생성)
        3. S3에 ZIP 파일 업로드
        4. S3에서 Lambda Layer 생성
        5. 배포 정보 반환
        
    Note:
        - S3를 통한 배포로 크기 제한 없음
        - 계정별 고유 버킷으로 충돌 방지
        - 기존 버킷 재사용으로 비용 최적화
    """
    print(f"🚀 Lambda Layer 배포 시작: {Config.LAYER_NAME}")
    
    lambda_client = boto3.client('lambda', region_name=Config.REGION)
    
    # ZIP 파일 존재 확인
    current_dir = Path(__file__).parent
    zip_file = current_dir / Config.ZIP_FILENAME
    
    if not zip_file.exists():
        raise FileNotFoundError(
            f"Layer ZIP 파일을 찾을 수 없습니다: {zip_file}\n"
            "yfinance.zip 파일을 현재 디렉토리에 넣어주세요."
        )

    try:
        # S3를 통한 업로드 (대용량 파일 지원)
        print("📤 S3를 통한 배포 진행...")
        
        # S3 버킷 준비 (기존 버킷 재사용 또는 신규 생성)
        bucket_name = get_or_create_s3_bucket()
        
        # ZIP 파일을 S3에 업로드
        s3_url = upload_to_s3(str(zip_file), bucket_name)
        
        # S3에서 Lambda Layer 생성
        print(f"🔨 Lambda Layer 생성 중...")
        response = lambda_client.publish_layer_version(
            LayerName=Config.LAYER_NAME,
            Description=Config.DESCRIPTION,
            Content={
                'S3Bucket': bucket_name,
                'S3Key': Config.ZIP_FILENAME
            },
            CompatibleRuntimes=[Config.RUNTIME],
            CompatibleArchitectures=['x86_64']
        )
        
        # 배포 결과 정보
        layer_arn = response['LayerArn']
        layer_version_arn = response['LayerVersionArn']
        version = response['Version']
        
        print(f"✅ Layer 배포 완료!")
        print(f"🔗 Layer ARN: {layer_arn}")
        print(f"📋 Version ARN: {layer_version_arn}")
        print(f"🔢 Version: {version}")
        print(f"ℹ️ S3 버킷 유지: {bucket_name} (재사용 가능)")
        
        return layer_version_arn
        
    except Exception as e:
        print(f"❌ Layer 배포 실패: {str(e)}")
        raise

# ================================
# 배포 정보 관리
# ================================


def save_layer_info(layer_version_arn):
    """
    Layer 배포 정보를 JSON 파일로 저장
    
    다른 컴포넌트(Lambda 함수 등)에서 Layer 정보를 참조할 수 있도록
    배포 결과를 JSON 파일로 저장합니다.
    
    Args:
        layer_version_arn (str): 배포된 Layer Version ARN
        
    Returns:
        str: 저장된 JSON 파일 경로
        
    Note:
        - 파일명: layer_deployment_info.json
        - Lambda 배포 시 자동으로 참조됨
    """
    current_dir = Path(__file__).parent
    layer_info = {
        "layer_name": Config.LAYER_NAME,
        "layer_version_arn": layer_version_arn,
        "region": Config.REGION,
        "runtime": Config.RUNTIME,
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = current_dir / "layer_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(layer_info, f, indent=2)
    
    print(f"� 배포 정o보 저장: {info_file}")
    return str(info_file)

# ================================
# 메인 실행 함수
# ================================

def main():
    """
    메인 실행 함수
    
    Portfolio Architect Lambda Layer의 전체 배포 프로세스를 관리합니다.
    
    Returns:
        str: 배포된 Layer Version ARN
        
    Raises:
        Exception: 배포 과정에서 오류 발생 시
    """
    try:
        print("=" * 50)
        print("📦 Portfolio Architect Lambda Layer 배포")
        print(f"📍 Layer명: {Config.LAYER_NAME}")
        print(f"🌍 리전: {Config.REGION}")
        print("=" * 50)
        
        # Layer 배포 실행
        layer_version_arn = deploy_lambda_layer()
        
        # 배포 정보 저장
        info_file = save_layer_info(layer_version_arn)
        
        print("=" * 50)
        print("🎉 Layer 배포 성공!")
        print(f"📋 Layer Version ARN: {layer_version_arn}")
        print(f"📄 배포 정보: {info_file}")
        print("=" * 50)

        return layer_version_arn
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ Layer 배포 실패: {str(e)}")
        print("=" * 50)
        raise

if __name__ == "__main__":
    main()