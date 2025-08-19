"""
Lambda Layer 배포 스크립트

yfinance 등 외부 라이브러리를 포함한 Lambda Layer를 배포합니다.
50MB 이상의 Layer는 S3를 통해 배포합니다.
"""

import boto3
import json
import time
import os
from pathlib import Path


# 설정 상수
class Config:
    """Layer 배포 설정"""
    LAYER_NAME = "layer-yfinance"
    REGION = "us-west-2"
    RUNTIME = "python3.12"
    ZIP_FILENAME = "yfinance.zip"
    DESCRIPTION = "Portfolio Architect dependencies - yfinance, pandas, numpy"
    S3_BUCKET_PREFIX = "layer-yfinance"



def get_or_create_s3_bucket():
    """
    Layer 업로드용 S3 버킷 조회 또는 생성
    
    Returns:
        str: S3 버킷명
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
        
    except s3_client.exceptions.NoSuchBucket:
        # 버킷이 없으면 생성
        print(f"📦 S3 버킷 생성 중: {bucket_name}")
        
        if Config.REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': Config.REGION}
            )
        
        print(f"✅ S3 버킷 생성 완료: {bucket_name}")
        return bucket_name
        
    except Exception as e:
        print(f"❌ S3 버킷 처리 실패: {str(e)}")
        raise


def upload_to_s3(zip_file_path, bucket_name):
    """
    Layer ZIP 파일을 S3에 업로드
    
    Args:
        zip_file_path (str): ZIP 파일 경로
        bucket_name (str): S3 버킷명
        
    Returns:
        str: S3 객체 URL
    """
    s3_client = boto3.client('s3', region_name=Config.REGION)
    object_key = Config.ZIP_FILENAME
    
    print(f"📤 S3 업로드 중: {bucket_name}/{object_key}")
    
    # 파일 업로드
    s3_client.upload_file(zip_file_path, bucket_name, object_key)
    
    # S3 URL 생성
    s3_url = f"s3://{bucket_name}/{object_key}"
    print(f"✅ S3 업로드 완료: {s3_url}")
    
    return s3_url


def deploy_lambda_layer():
    """
    Lambda Layer 배포 (S3 지원)
    
    Returns:
        str: 배포된 Layer ARN
        
    Note:
        - 모든 크기의 Layer를 S3를 통해 안정적으로 배포
    """
    print(f"🚀 Lambda Layer 배포 시작: {Config.LAYER_NAME}")
    
    lambda_client = boto3.client('lambda', region_name=Config.REGION)
    # 현재 디렉토리에서 ZIP 파일 찾기
    current_dir = Path(__file__).parent
    zip_file = current_dir / Config.ZIP_FILENAME
    
    # ZIP 파일 존재 확인
    if not zip_file.exists():
        raise FileNotFoundError(
            f"Layer ZIP 파일을 찾을 수 없습니다: {zip_file}\n"
            "yfinance.zip 파일을 현재 디렉토리에 넣어주세요."
        )
    
    # 파일 크기 확인
    file_size = zip_file.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    print(f"📦 Layer ZIP 파일: {zip_file} ({file_size_mb:.1f}MB)")
    
    try:
        # S3를 통한 업로드 (모든 크기 지원)
        print("📤 S3를 통한 업로드 중...")
        
        # S3 버킷 조회/생성
        bucket_name = get_or_create_s3_bucket()
        
        # S3에 업로드
        s3_url = upload_to_s3(str(zip_file), bucket_name)
        
        # S3에서 Layer 배포
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
        
        print(f"ℹ️ S3 버킷 유지: {bucket_name} (재사용 가능)")
        
        layer_arn = response['LayerArn']
        layer_version_arn = response['LayerVersionArn']
        version = response['Version']
        
        print(f"✅ Layer 배포 완료!")
        print(f"🔗 Layer ARN: {layer_arn}")
        print(f"📋 Version ARN: {layer_version_arn}")
        print(f"🔢 Version: {version}")
        
        return layer_version_arn
        
    except Exception as e:
        print(f"❌ Layer 배포 실패: {str(e)}")
        raise


def save_layer_info(layer_version_arn):
    """
    Layer 배포 정보를 JSON 파일로 저장
    
    Args:
        layer_version_arn (str): Layer Version ARN
        
    Returns:
        str: 저장된 JSON 파일 경로
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
    
    return str(info_file)


def main():
    """메인 실행 함수"""
    try:
        print("=" * 50)
        print("📦 Portfolio Architect Lambda Layer 배포")
        print("=" * 50)
        
        # Layer 배포
        layer_version_arn = deploy_lambda_layer()
        
        # 배포 정보 저장
        info_file = save_layer_info(layer_version_arn)
        
        print("=" * 50)
        print("🎉 Layer 배포 성공!")
        print(f"📄 배포 정보: {info_file}")
        print("=" * 50)
        
        print("\n📋 다음 단계:")
        print("1. Lambda 함수에 Layer 연결")
        print("2. Lambda 함수 재배포")
        
        return layer_version_arn
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ Layer 배포 실패: {str(e)}")
        print("=" * 50)
        raise


if __name__ == "__main__":
    main()