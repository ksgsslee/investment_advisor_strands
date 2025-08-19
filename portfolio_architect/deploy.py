"""
Portfolio Architect AgentCore Runtime 배포 스크립트

Gateway 정보를 자동으로 로드하여 AgentCore Runtime을 배포합니다.
"""
import sys
import os
import time
import json
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime


# 설정 상수
class Config:
    """Runtime 배포 설정"""
    AGENT_NAME = "portfolio-architect"
    ENTRYPOINT_FILE = "portfolio_architect.py"
    REQUIREMENTS_FILE = "requirements.txt"
    MAX_DEPLOY_MINUTES = 15
    STATUS_CHECK_INTERVAL = 30
    REGION = "us-west-2"


def load_gateway_info():
    """Gateway 배포 정보 로드"""
    current_dir = Path(__file__).parent
    gateway_dir = current_dir / "gateway"
    info_file = gateway_dir / "gateway_deployment_info.json"
    
    if not info_file.exists():
        raise FileNotFoundError(
            f"Gateway 배포 정보를 찾을 수 없습니다: {info_file}\n"
            "먼저 'python gateway/deploy_gateway.py'를 실행하세요."
        )
    
    with open(info_file, 'r') as f:
        gateway_info = json.load(f)
    
    print(f"📋 Gateway 정보 로드: {gateway_info['gateway_url']}")
    return gateway_info


def create_iam_role():
    """AgentCore Runtime용 IAM 역할 생성"""
    # gateway utils 사용
    sys.path.append(str(Path(__file__).parent / "gateway"))
    from utils import create_agentcore_gateway_role
    
    role_info = create_agentcore_gateway_role(Config.AGENT_NAME, Config.REGION)
    return role_info['Role']['Arn']


def configure_runtime(role_arn):
    """Runtime 구성"""
    print("🔧 Runtime 구성 중...")
    current_dir = Path(__file__).parent
    
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / Config.ENTRYPOINT_FILE),
        execution_role=role_arn,
        auto_create_ecr=True,
        requirements_file=str(current_dir / Config.REQUIREMENTS_FILE),
        region=Config.REGION,
        agent_name=Config.AGENT_NAME,
    )
    return runtime


def deploy_and_wait(runtime):
    """배포 및 상태 대기"""
    print("🚀 Runtime 배포 중...")
    launch_result = runtime.launch(auto_update_on_conflict=True)
    
    end_statuses = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
    max_checks = (Config.MAX_DEPLOY_MINUTES * 60) // Config.STATUS_CHECK_INTERVAL
    
    for i in range(max_checks):
        status = runtime.status().endpoint['status']
        print(f"📊 상태: {status} ({i+1}/{max_checks})")
        
        if status in end_statuses:
            break
        time.sleep(Config.STATUS_CHECK_INTERVAL)
    
    success = status == 'READY'
    return success, launch_result.agent_arn if success else "", status


def save_deployment_info(agent_arn, gateway_info):
    """배포 정보 저장"""
    current_dir = Path(__file__).parent
    deployment_info = {
        "agent_name": Config.AGENT_NAME,
        "agent_arn": agent_arn,
        "region": Config.REGION,
        "gateway_url": gateway_info['gateway_url'],
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = current_dir / "runtime_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    return str(info_file)


def main():
    """메인 배포 함수"""
    try:
        print("=" * 60)
        print("🎯 Portfolio Architect Runtime 배포 시작")
        print("=" * 60)
        
        # 필수 파일 확인
        current_dir = Path(__file__).parent
        required_files = [Config.ENTRYPOINT_FILE, Config.REQUIREMENTS_FILE]
        missing_files = [f for f in required_files if not (current_dir / f).exists()]
        
        if missing_files:
            print(f"❌ 필수 파일 누락: {', '.join(missing_files)}")
            return 1
        
        # Gateway 정보 로드
        gateway_info = load_gateway_info()
        
        # IAM 역할 생성
        role_arn = create_iam_role()
        
        # Runtime 구성 및 배포
        runtime = configure_runtime(role_arn)
        success, agent_arn, status = deploy_and_wait(runtime)
        
        if success:
            # 배포 정보 저장
            info_file = save_deployment_info(agent_arn, gateway_info)
            
            print("=" * 60)
            print("🎉 Runtime 배포 성공!")
            print(f"🔗 Agent ARN: {agent_arn}")
            print(f"📄 배포 정보: {info_file}")
            print("=" * 60)
            return 0
        else:
            print("=" * 60)
            print(f"❌ Runtime 배포 실패: {status}")
            print("=" * 60)
            return 1
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ 배포 오류: {str(e)}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())