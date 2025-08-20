"""
deploy.py
Financial Analyst AgentCore Runtime 배포 스크립트

개인 재무 분석 AI 에이전트를 AWS 서버리스 환경에 배포합니다.
Reflection 패턴을 활용하여 분석 결과의 품질을 보장하는 기능을 제공합니다.

주요 기능:
- IAM 역할 자동 생성 및 권한 설정
- Docker 이미지 빌드 및 ECR 배포
- 배포 상태 실시간 모니터링
- 배포 정보 자동 저장
"""

import sys
import os
import time
import json
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime

# 공통 utils 모듈 import
utils_path = str(Path(__file__).parent.parent)
sys.path.append(utils_path)
from utils import create_agentcore_role

# ================================
# 설정 상수
# ================================

class Config:
    """AgentCore Runtime 배포 설정 상수"""
    AGENT_NAME = "financial_analyst"
    ENTRYPOINT_FILE = "financial_analyst.py"
    REQUIREMENTS_FILE = "requirements.txt"
    MAX_DEPLOY_MINUTES = 15
    STATUS_CHECK_INTERVAL = 30
    REGION = "us-west-2"

# ================================
# 유틸리티 함수들
# ================================


def create_iam_role():
    """
    AgentCore Runtime용 IAM 역할 생성
    
    Runtime이 AWS 서비스에 접근할 수 있도록 하는 IAM 역할을 생성합니다.
    공통 utils의 함수를 재사용하여 일관된 권한을 부여합니다.
    
    Returns:
        str: 생성된 IAM 역할 ARN
        
    Note:
        - Bedrock, Lambda 접근 권한 포함
        - 기존 역할이 있으면 재사용
    """
    print("🔐 IAM 역할 생성 중...")
    
    # AgentCore Runtime용 IAM 역할 생성
    role_info = create_agentcore_role(Config.AGENT_NAME, Config.REGION)
    role_arn = role_info['Role']['Arn']
    
    print(f"✅ IAM 역할 준비 완료: {role_arn}")
    return role_arn

def configure_runtime(role_arn):
    """
    AgentCore Runtime 구성
    
    배포에 필요한 Runtime 설정을 구성합니다.
    
    Args:
        role_arn (str): Runtime 실행용 IAM 역할 ARN
        
    Returns:
        Runtime: 구성된 Runtime 객체
        
    Note:
        - ECR 자동 생성 활성화
        - requirements.txt 기반 의존성 설치
    """
    print("🔧 Runtime 구성 중...")
    current_dir = Path(__file__).parent
    
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / Config.ENTRYPOINT_FILE),    # financial_analyst.py
        execution_role=role_arn,                                 # IAM 실행 역할
        auto_create_ecr=True,                                   # ECR 자동 생성
        requirements_file=str(current_dir / Config.REQUIREMENTS_FILE),  # 의존성 파일
        region=Config.REGION,                                   # AWS 리전
        agent_name=Config.AGENT_NAME                           # Agent 이름
    )
    
    print("✅ Runtime 구성 완료")
    return runtime

def deploy_and_wait(runtime):
    """
    Runtime 배포 및 상태 대기
    
    Runtime을 AWS에 배포하고 완료될 때까지 상태를 모니터링합니다.
    
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
    
    # 배포 시작
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

def save_deployment_info(agent_arn):
    """
    Runtime 배포 정보 저장
    
    배포된 Runtime의 정보를 JSON 파일로 저장합니다.
    다른 시스템에서 Runtime을 호출할 때 참조할 수 있습니다.
    
    Args:
        agent_arn (str): 배포된 Agent ARN
        
    Returns:
        str: 저장된 JSON 파일 경로
        
    Note:
        - 파일명: deployment_info.json
        - Agent ARN, 리전 등 포함
        - 배포 시각 기록
    """
    print("📄 배포 정보 저장 중...")
    
    current_dir = Path(__file__).parent
    deployment_info = {
        "agent_name": Config.AGENT_NAME,
        "agent_arn": agent_arn,
        "region": Config.REGION,
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = current_dir / "deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"✅ 배포 정보 저장: {info_file}")
    return str(info_file)

# ================================
# 배포 검증 함수들
# ================================

def validate_prerequisites():
    """
    배포 전 필수 조건 검증
    
    Runtime 배포에 필요한 모든 파일과 의존성을 확인합니다.
    
    Returns:
        bool: 모든 조건이 충족되면 True
        
    Raises:
        FileNotFoundError: 필수 파일이 없을 때
        
    Checks:
        - financial_analyst.py (엔트리포인트)
        - requirements.txt (의존성 파일)
    """
    print("🔍 배포 전 필수 조건 검증 중...")
    
    current_dir = Path(__file__).parent
    required_files = [Config.ENTRYPOINT_FILE, Config.REQUIREMENTS_FILE]
    missing_files = [f for f in required_files if not (current_dir / f).exists()]
    
    if missing_files:
        raise FileNotFoundError(f"필수 파일 누락: {', '.join(missing_files)}")
    
    print("✅ 필수 파일 확인 완료")
    return True

# ================================
# 메인 실행 함수
# ================================

def main():
    """
    메인 배포 함수
    
    Financial Analyst Runtime의 전체 배포 프로세스를 관리합니다.
    개인 재무 분석 AI 에이전트를 AWS 서버리스 환경에서 실행할 수 있도록 배포합니다.
    
    Returns:
        int: 성공 시 0, 실패 시 1
        
    Process:
        1. 필수 조건 검증 (파일 존재 확인)
        2. IAM 역할 생성 (Runtime 실행 권한)
        3. Runtime 구성 (Docker, ECR, 의존성)
        4. 배포 및 대기 (상태 모니터링)
        5. 배포 정보 저장 (다른 시스템에서 참조용)
        
    Note:
        - 최대 15분 배포 대기
        - 30초 간격으로 상태 체크
        - 자동 업데이트 지원 (기존 배포 덮어쓰기)
    """
    try:
        print("=" * 60)
        print("🎯 Financial Analyst Runtime 배포")
        print(f"📍 Agent명: {Config.AGENT_NAME}")
        print(f"🌍 리전: {Config.REGION}")
        print(f"⏱️ 최대 대기시간: {Config.MAX_DEPLOY_MINUTES}분")
        print("=" * 60)
        
        # 1. 필수 조건 검증
        validate_prerequisites()
        
        # 2. IAM 역할 생성
        role_arn = create_iam_role()
        
        # 3. Runtime 구성
        runtime = configure_runtime(role_arn)
        
        # 4. 배포 및 대기
        success, agent_arn, status = deploy_and_wait(runtime)
        
        if success:
            # 5. 배포 정보 저장
            info_file = save_deployment_info(agent_arn)
            
            print("=" * 60)
            print("🎉 배포 성공!")
            print(f"🔗 Agent ARN: {agent_arn}")
            print(f"📄 배포 정보: {info_file}")
            print("=" * 60)
            
            print("\n📋 다음 단계:")
            print("1. Streamlit 앱 실행: streamlit run app.py")
            print("2. 직접 테스트: python test.py")
            print("3. Agent ARN으로 직접 호출")
            
            return 0
        else:
            print("=" * 60)
            print(f"❌ 배포 실패: {status}")
            print("💡 문제 해결 방법:")
            print("1. IAM 권한 확인")
            print("2. Docker 설치 상태 확인")
            print("3. 로그 확인 후 재시도")
            print("=" * 60)
            return 1
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ 배포 오류: {str(e)}")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())