"""
Lambda 함수 배포 스크립트
"""

import boto3
import zipfile
import json
import os
import time

def create_lambda_zip():
    """Lambda 함수 코드를 ZIP 파일로 패키징"""
    zip_filename = 'lambda_function.zip'
    
    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
        zip_file.write('lambda_function.py')
    
    return zip_filename

def create_lambda_role():
    """Lambda 실행 역할 생성"""
    iam = boto3.client('iam')
    role_name = 'agentcore-portfolio-architect-role'
    
    # 신뢰 정책
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # 역할 생성
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Lambda execution role for portfolio architect'
        )
        role_arn = response['Role']['Arn']
        
        # 기본 Lambda 실행 정책 연결
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        print(f"Created role: {role_arn}")
        return role_arn
        
    except iam.exceptions.EntityAlreadyExistsException:
        # 이미 존재하는 경우 ARN 반환
        response = iam.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        print(f"Using existing role: {role_arn}")
        return role_arn

def deploy_lambda_function(function_name, region):
    """Lambda 함수 배포"""
    lambda_client = boto3.client('lambda', region_name=region)

    # ZIP 파일 생성
    zip_filename = create_lambda_zip()
    
    # IAM 역할 생성
    role_arn = create_lambda_role()
    
    # ZIP 파일 읽기
    with open(zip_filename, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    try:
        # Lambda 함수 생성
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.12',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='Portfolio architect Lambda function for MCP Gateway',
            Timeout=30,
            MemorySize=128
        )
        
        function_arn = response['FunctionArn']
        print(f"Created Lambda function: {function_arn}")
        
    except lambda_client.exceptions.ResourceConflictException:
        # 이미 존재하는 경우 업데이트
        print("Function already exists, updating...")
        
        # 함수 코드 업데이트
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        # 함수 정보 가져오기
        response = lambda_client.get_function(FunctionName=function_name)
        function_arn = response['Configuration']['FunctionArn']
        print(f"Updated Lambda function: {function_arn}")
    
    # ZIP 파일 정리
    os.remove(zip_filename)
    
    # 함수가 활성화될 때까지 대기
    print("Waiting for function to be active...")
    time.sleep(10)
    
    return function_arn

if __name__ == "__main__":
    print("🚀 Deploying Lambda function...")
    
    function_name = 'agentcore-portfolio-architect'
    function_arn = deploy_lambda_function(function_name, "us-west-2")
    
    print(f"✅ Lambda function deployed successfully!")
    print(f"Function ARN: {function_arn}")
