"""
deploy.py
AgentCore Runtime 배포 스크립트
"""

import sys
import os
import time
import json
from pathlib import Path
from boto3.session import Session
from bedrock_agentcore_starter_toolkit import Runtime

# 설정
class Config:
    AGENT_NAME = "financial_advisor"
    ENTRYPOINT_FILE = "financial_advisor.py"
    REQUIREMENTS_FILE = "requirements.txt"
    MAX_DEPLOY_MINUTES = 10
    STATUS_CHECK_INTERVAL = 30
    REGION = "us-west-2"

# 경로 설정
CURRENT_DIR = Path(__file__).parent.resolve()
sys.path.append(str(CURRENT_DIR.parent))
from utils import create_agentcore_role

def setup_environment():
    """환경 설정"""
    region = Config.REGION
    print(f"배포 시작: {Config.AGENT_NAME} ({region})")
    return region

def create_iam_role():
    """IAM 역할 생성"""
    role_info = create_agentcore_role(agent_name=Config.AGENT_NAME, region=Config.REGION)
    return role_info['Role']['Arn']

def configure_runtime(role_arn, region):
    """Runtime 구성"""
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(CURRENT_DIR / Config.ENTRYPOINT_FILE),
        execution_role=role_arn,
        auto_create_ecr=True,
        requirements_file=str(CURRENT_DIR / Config.REQUIREMENTS_FILE),
        region=region,
        agent_name=Config.AGENT_NAME,
    )
    return runtime

def deploy_and_wait(runtime):
    """배포 및 대기"""
    print("배포 중...")
    launch_result = runtime.launch(auto_update_on_conflict=True)
    
    end_statuses = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
    max_checks = (Config.MAX_DEPLOY_MINUTES * 60) // Config.STATUS_CHECK_INTERVAL
    
    for i in range(max_checks):
        status = runtime.status().endpoint['status']
        print(f"상태: {status}")
        if status in end_statuses:
            break
        time.sleep(Config.STATUS_CHECK_INTERVAL)
    
    success = status == 'READY'
    return success, launch_result.agent_arn if success else "", status

def deploy():
    """전체 배포 프로세스"""
    try:
        region = setup_environment()
        role_arn = create_iam_role()
        runtime = configure_runtime(role_arn, region)
        success, agent_arn, status = deploy_and_wait(runtime)
        
        if success:
            print(f"배포 완료: {agent_arn}")
            # 배포 정보 저장
            deployment_info = {
                "agent_arn": agent_arn,
                "region": region,
                "status": status
            }
            with open(CURRENT_DIR / "deployment_info.json", "w") as f:
                json.dump(deployment_info, f)
            return True
        else:
            print(f"배포 실패: {status}")
            return False
        
    except Exception as e:
        print(f"오류: {e}")
        return False

def main():
    """메인 함수"""
    required_files = [Config.ENTRYPOINT_FILE, Config.REQUIREMENTS_FILE]
    missing_files = [f for f in required_files if not (CURRENT_DIR / f).exists()]
    
    if missing_files:
        print(f"파일 누락: {', '.join(missing_files)}")
        return 1
    
    success = deploy()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())