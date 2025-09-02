"""
deploy_lambda_layer.py

Lambda Layer 배포 스크립트
yfinance 라이브러리 포함 Lambda Layer 배포
"""

import boto3
import json
import time
import os
from pathlib import Path

class Config:
    """Lambda Layer 배포 설정"""
    REGION = "us-west-2"
    LAYER_NAME = "layer-yfinance"

def setup_s3_bucket():
    """S3 버킷 설정"""
    print("📦 S3 버킷 설정 중...")
    s3_client = boto3.client('s3', region_name=Config.REGION)
    sts_client = boto3.client('sts', region_name=Config.REGION)
    
    account_id = sts_client.get_caller_identity()["Account"]
    bucket_name = f"{Config.LAYER_NAME}-{account_id}"
    
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return bucket_name
        
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            if Config.REGION == 'us-east-1':
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': Config.REGION}
                )
            return bucket_name
        else:
            raise

def upload_layer_zip(zip_file_path, bucket_name):
    """Layer ZIP 파일 S3 업로드"""
    s3_client = boto3.client('s3', region_name=Config.REGION)
    object_key = f"{Config.LAYER_NAME}.zip"
    
    s3_client.upload_file(zip_file_path, bucket_name, object_key)
    return object_key

def create_lambda_layer(bucket_name, s3_key):
    """Lambda Layer 생성"""
    print("🔧 Lambda Layer 생성 중...")
    lambda_client = boto3.client('lambda', region_name=Config.REGION)
    
    response = lambda_client.publish_layer_version(
        LayerName=Config.LAYER_NAME,
        Content={
            'S3Bucket': bucket_name,
            'S3Key': s3_key
        },
        CompatibleRuntimes=["python3.12"],
        CompatibleArchitectures=['x86_64']
    )
    
    return {
        'layer_arn': response['LayerArn'],
        'layer_version_arn': response['LayerVersionArn'],
        'version': response['Version']
    }

def save_deployment_info(result):
    """배포 정보 저장"""
    info_file = Path(__file__).parent / "layer_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(result, f, indent=2)
    return str(info_file)

def main():
    try:
        print("🚀 yfinance Lambda Layer 배포")
        
        # ZIP 파일 확인
        current_dir = Path(__file__).parent
        zip_file = current_dir / f"{Config.LAYER_NAME}.zip"
        
        if not zip_file.exists():
            raise FileNotFoundError(
                f"Layer ZIP 파일을 찾을 수 없습니다: {zip_file}\n"
                f"{Config.LAYER_NAME}.zip 파일을 현재 디렉토리에 넣어주세요."
            )
        
        # S3 버킷 설정
        bucket_name = setup_s3_bucket()
        
        # ZIP 파일 업로드
        s3_key = upload_layer_zip(str(zip_file), bucket_name)
        
        # Lambda Layer 생성
        layer_result = create_lambda_layer(bucket_name, s3_key)
        
        # 배포 결과 구성
        result = {
            'layer_name': Config.LAYER_NAME,
            'layer_arn': layer_result['layer_arn'],
            'layer_version_arn': layer_result['layer_version_arn'],
            'version': layer_result['version'],
            'region': Config.REGION,
            'runtime': "python3.12",
            'deployed_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 배포 정보 저장
        info_file = save_deployment_info(result)
        
        print(f"\n🎉 Lambda Layer 배포 완료!")
        print(f"🔗 Layer Version ARN: {result['layer_version_arn']}")
        print(f"📄 배포 정보: {info_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Lambda Layer 배포 실패: {e}")
        raise

if __name__ == "__main__":
    main()