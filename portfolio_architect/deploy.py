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
    """
    Gateway 배포 정보 로드
    
    Runtime 배포에 필요한 Gateway 정보를 JSON 파일에서 로드합니다.
    Gateway가 먼저 배포되어 있어야 합니다.
    
    Returns:
        dict: Gateway 배포 정보 (gateway_url, client_id 등)
        
    Raises:
        FileNotFoundError: Gateway 배포 정보 파일이 없을 때
    """
    print("📋 Gateway 배포 정보 로드 중...")
    
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
    
    print(f"✅ Gateway URL: {gateway_info['gateway_url']}")
    return gateway_info


def create_iam_role():
    """
    AgentCore Runtime용 IAM 역할 생성
    
    Runtime이 AWS 서비스에 접근할 수 있도록 하는 IAM 역할을 생성합니다.
    Gateway utils의 함수를 재사용하여 일관된 권한을 부여합니다.
    
    Returns:
        str: 생성된 IAM 역할 ARN
        
    Note:
        - Bedrock, Lambda, Gateway 접근 권한 포함
        - 기존 역할이 있으면 재사용
    """
    print("🔐 IAM 역할 생성 중...")
    
    # 공통 utils 모듈 import
    utils_path = str(Path(__file__).parent.parent)
    sys.path.append(utils_path)
    from utils import create_agentcore_role
    
    # AgentCore Runtime용 IAM 역할 생성
    role_info = create_agentcore_role(Config.AGENT_NAME, Config.REGION)
    role_arn = role_info['Role']['Arn']
    
    print(f"✅ IAM 역할 준비 완료: {role_arn}")
    return role_arn


def configure_runtime(role_arn):
    """
    AgentCore Runtime 구성
    
    배포에 필요한 Runtime 설정을 구성합니다.
    Docker 이미지 빌드 및 ECR 업로드 설정을 포함합니다.
    
    Args:
        role_arn (str): Runtime 실행용 IAM 역할 ARN
        
    Returns:
        Runtime: 구성된 Runtime 객체
        
    Note:
        - ECR 자동 생성 활성화
        - requirements.txt 기반 의존성 설치
        - 서버리스 환경에서 실행
    """
    print("🔧 Runtime 구성 중...")
    current_dir = Path(__file__).parent
    
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / Config.ENTRYPOINT_FILE),    # portfolio_architect.py
        execution_role=role_arn,                                 # IAM 실행 역할
        auto_create_ecr=True,                                   # ECR 자동 생성
        requirements_file=str(current_dir / Config.REQUIREMENTS_FILE),  # 의존성 파일
        region=Config.REGION,                                   # AWS 리전
        agent_name=Config.AGENT_NAME,                          # Agent 이름
    )
    
    print("✅ Runtime 구성 완료")
    return runtime


def deploy_and_wait(runtime):
    """
    Runtime 배포 및 상태 대기
    
    Runtime을 AWS에 배포하고 완료될 때까지 상태를 모니터링합니다.
    Docker 이미지 빌드, ECR 업로드, 서비스 생성 등이 포함됩니다.
    
    Args:
        runtime (Runtime): 구성된 Runtime 객체
        
    Returns:
        tuple: (성공 여부, Agent ARN, 최종 상태)
        
    Note:
        - 최대 15분 대기 (30초 간격으로 체크)
        - 기존 배포가 있으면 자동 업데이트
        - READY 상태가 되면 배포 완료
    """
    print("🚀 Runtime 배포 시작...")
    print("   - Docker 이미지 빌드")
    print("   - ECR 업로드")
    print("   - 서비스 생성/업데이트")
    
    # 배포 시작 (기존 배포 충돌 시 자동 업데이트)
    launch_result = runtime.launch(auto_update_on_conflict=True)
    
    # 배포 완료 상태 목록
    end_statuses = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
    max_checks = (Config.MAX_DEPLOY_MINUTES * 60) // Config.STATUS_CHECK_INTERVAL
    
    print(f"⏳ 배포 상태 모니터링 중... (최대 {Config.MAX_DEPLOY_MINUTES}분)")
    
    for i in range(max_checks):
        try:
            status = runtime.status().endpoint['status']
            elapsed_time = (i + 1) * Config.STATUS_CHECK_INTERVAL
            print(f"📊 상태: {status} ({elapsed_time//60}분 {elapsed_time%60}초 경과)")
            
            if status in end_statuses:
                break
                
        except Exception as e:
            print(f"⚠️ 상태 확인 오류: {str(e)}")
            
        time.sleep(Config.STATUS_CHECK_INTERVAL)
    
    success = status == 'READY'
    agent_arn = launch_result.agent_arn if success else ""
    
    if success:
        print("✅ Runtime 배포 완료!")
    else:
        print(f"❌ Runtime 배포 실패: {status}")
    
    return success, agent_arn, status


def save_deployment_info(agent_arn, gateway_info):
    """
    Runtime 배포 정보 저장
    
    배포된 Runtime의 정보를 JSON 파일로 저장합니다.
    다른 시스템에서 Runtime을 호출할 때 참조할 수 있습니다.
    
    Args:
        agent_arn (str): 배포된 Agent ARN
        gateway_info (dict): Gateway 정보
        
    Returns:
        str: 저장된 JSON 파일 경로
        
    Note:
        - 파일명: runtime_deployment_info.json
        - Agent ARN, Gateway URL 등 포함
        - 배포 시각 기록
    """
    print("📄 배포 정보 저장 중...")
    
    current_dir = Path(__file__).parent
    deployment_info = {
        "agent_name": Config.AGENT_NAME,
        "agent_arn": agent_arn,
        "region": Config.REGION,
        "gateway_url": gateway_info['gateway_url'],
        "gateway_id": gateway_info.get('gateway_id'),
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = current_dir / "runtime_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"✅ 배포 정보 저장: {info_file}")
    return str(info_file)


def validate_prerequisites():
    """
    배포 전 필수 조건 검증
    
    Returns:
        bool: 모든 조건이 충족되면 True
        
    Raises:
        FileNotFoundError: 필수 파일이 없을 때
    """
    print("🔍 배포 전 필수 조건 검증 중...")
    
    current_dir = Path(__file__).parent
    required_files = [Config.ENTRYPOINT_FILE, Config.REQUIREMENTS_FILE]
    missing_files = [f for f in required_files if not (current_dir / f).exists()]
    
    if missing_files:
        raise FileNotFoundError(f"필수 파일 누락: {', '.join(missing_files)}")
    
    print("✅ 필수 파일 확인 완료")
    return True


def main():
    """
    메인 배포 함수
    
    Portfolio Architect Runtime의 전체 배포 프로세스를 관리합니다.
    
    Returns:
        int: 성공 시 0, 실패 시 1
        
    Process:
        1. 필수 조건 검증
        2. Gateway 정보 로드
        3. IAM 역할 생성
        4. Runtime 구성
        5. 배포 및 대기
        6. 배포 정보 저장
    """
    try:
        print("=" * 60)
        print("🎯 Portfolio Architect Runtime 배포")
        print(f"📍 Agent명: {Config.AGENT_NAME}")
        print(f"🌍 리전: {Config.REGION}")
        print("=" * 60)
        
        # 1. 필수 조건 검증
        validate_prerequisites()
        
        # 2. Gateway 정보 로드
        gateway_info = load_gateway_info()
        
        # 3. IAM 역할 생성
        role_arn = create_iam_role()
        
        # 4. Runtime 구성
        runtime = configure_runtime(role_arn)
        
        # 5. 배포 및 대기
        success, agent_arn, status = deploy_and_wait(runtime)
        
        if success:
            # 6. 배포 정보 저장
            info_file = save_deployment_info(agent_arn, gateway_info)
            
            print("=" * 60)
            print("🎉 배포 성공!")
            print(f"🔗 Agent ARN: {agent_arn}")
            print(f"📄 배포 정보: {info_file}")
            print("=" * 60)
            
            print("\n📋 다음 단계:")
            print("1. Streamlit 앱 실행: streamlit run app.py")
            print("2. 또는 Agent ARN으로 직접 호출")
            
            return 0
        else:
            print("=" * 60)
            print(f"❌ 배포 실패: {status}")
            print("=" * 60)
            return 1
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ 배포 오류: {str(e)}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())