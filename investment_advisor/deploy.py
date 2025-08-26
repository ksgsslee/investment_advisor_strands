"""
deploy.py
Investment Advisor AgentCore Runtime 배포 스크립트

Multi-Agent 패턴 기반 투자 자문 시스템을 AWS 서버리스 환경에 배포합니다.
3개의 독립적인 에이전트를 순차 호출하고 Memory에 결과를 저장하는 시스템입니다.

주요 기능:
- 다른 에이전트 ARN 자동 로드 및 환경변수 주입
- IAM 역할 자동 생성 및 권한 설정 (Memory 포함)
- Docker 이미지 빌드 및 ECR 배포
- 배포 상태 실시간 모니터링
"""

import sys
import os
import time
import json
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime

# shared 모듈 경로 추가
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))

# 공통 유틸리티 import
from runtime_utils import create_agentcore_runtime_role

# ================================
# 설정 상수
# ================================

class Config:
    """AgentCore Runtime 배포 설정 상수"""
    AGENT_NAME = "investment_advisor"
    ENTRYPOINT_FILE = "investment_advisor.py"
    REQUIREMENTS_FILE = "requirements.txt"
    MAX_DEPLOY_MINUTES = 15
    STATUS_CHECK_INTERVAL = 30
    REGION = "us-west-2"

# ================================
# 유틸리티 함수들
# ================================

def load_agent_arns():
    """
    다른 에이전트들의 배포 정보 로드
    
    Investment Advisor가 호출할 3개 에이전트의 ARN을 로드합니다.
    모든 에이전트가 먼저 배포되어 있어야 합니다.
    
    Returns:
        dict: 각 에이전트의 ARN 정보
        
    Raises:
        FileNotFoundError: 필수 에이전트 배포 정보가 없을 때
    """
    print("📋 다른 에이전트 배포 정보 로드 중...")
    
    base_path = Path(__file__).parent.parent
    agent_arns = {}
    
    # 필수 에이전트 목록
    required_agents = [
        ("financial_analyst", "Financial Analyst"),
        ("portfolio_architect", "Portfolio Architect"), 
        ("risk_manager", "Risk Manager")
    ]
    
    missing_agents = []
    for agent_dir, agent_name in required_agents:
        info_file = base_path / agent_dir / "deployment_info.json"
        
        if not info_file.exists():
            missing_agents.append(agent_name)
        else:
            with open(info_file, 'r') as f:
                deployment_info = json.load(f)
                agent_arns[agent_dir] = deployment_info["agent_arn"]
                print(f"✅ {agent_name}: {deployment_info['agent_arn']}")
    
    if missing_agents:
        raise FileNotFoundError(
            f"다음 에이전트들이 먼저 배포되어야 합니다: {', '.join(missing_agents)}\n"
            "각 에이전트 폴더에서 'python deploy.py'를 실행하세요."
        )
    
    return agent_arns

def create_iam_role():
    """
    Investment Advisor용 특별 IAM 역할 생성 (다른 에이전트 호출 권한 포함)
    
    Returns:
        str: 생성된 IAM 역할 ARN
    """
    print("🔐 Investment Advisor 전용 IAM 역할 생성 중...")
    
    # 기본 AgentCore Runtime용 IAM 역할 생성
    role_info = create_agentcore_runtime_role(Config.AGENT_NAME, Config.REGION)
    role_arn = role_info['Role']['Arn']
    
    # Investment Advisor 전용 추가 권한 정책 생성
    print("🔐 다른 에이전트 호출 권한 추가 중...")
    
    import boto3
    iam_client = boto3.client('iam')
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    role_name = f'agentcore-runtime-{Config.AGENT_NAME}-role'
    
    # 다른 에이전트 호출을 위한 추가 정책
    additional_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "InvestmentAdvisorAgentCalls",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeAgentRuntime",
                    "bedrock-agentcore:GetAgentRuntime"
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/financial_analyst-*",
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/portfolio_architect-*",
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/risk_manager-*"
                ]
            }
        ]
    }
    
    try:
        iam_client.put_role_policy(
            PolicyDocument=json.dumps(additional_policy),
            PolicyName="InvestmentAdvisorAgentCallsPolicy",
            RoleName=role_name
        )
        print("✅ 다른 에이전트 호출 권한 추가 완료")
    except Exception as e:
        print(f"⚠️ 추가 권한 설정 오류: {e}")
    
    print(f"✅ Investment Advisor IAM 역할 준비 완료: {role_arn}")
    return role_arn

def configure_runtime(role_arn):
    """
    AgentCore Runtime 구성
    
    Args:
        role_arn (str): Runtime 실행용 IAM 역할 ARN
        
    Returns:
        Runtime: 구성된 Runtime 객체
    """
    print("🔧 Runtime 구성 중...")
    current_dir = Path(__file__).parent
    
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / Config.ENTRYPOINT_FILE),
        execution_role=role_arn,
        auto_create_ecr=True,
        requirements_file=str(current_dir / Config.REQUIREMENTS_FILE),
        region=Config.REGION,
        agent_name=Config.AGENT_NAME
    )
    
    print("✅ Runtime 구성 완료")
    return runtime

def deploy_and_wait(runtime, agent_arns):
    """
    Runtime 배포 및 상태 대기
    
    Runtime을 AWS에 배포하고 완료될 때까지 상태를 모니터링합니다.
    다른 에이전트 ARN을 환경변수로 설정하여 Runtime에서 사용할 수 있도록 합니다.
    
    Args:
        runtime (Runtime): 구성된 Runtime 객체
        agent_arns (dict): 다른 에이전트들의 ARN 정보
        
    Returns:
        tuple: (성공 여부, Agent ARN, 최종 상태)
    """
    print("🚀 Runtime 배포 시작...")
    print("   - Docker 이미지 빌드")
    print("   - ECR 업로드")
    print("   - 서비스 생성/업데이트")
    
    # 다른 에이전트 ARN을 환경변수로 설정
    env_vars = {
        "FINANCIAL_ANALYST_ARN": agent_arns["financial_analyst"],
        "PORTFOLIO_ARCHITECT_ARN": agent_arns["portfolio_architect"],
        "RISK_MANAGER_ARN": agent_arns["risk_manager"],
        "AWS_REGION": Config.REGION
    }
    
    # 배포 시작 (환경변수와 함께)
    launch_result = runtime.launch(auto_update_on_conflict=True, env_vars=env_vars)
    
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

def save_deployment_info(agent_arn, agent_arns):
    """
    Runtime 배포 정보 저장
    
    Args:
        agent_arn (str): 배포된 Agent ARN
        agent_arns (dict): 다른 에이전트들의 ARN 정보
        
    Returns:
        str: 저장된 JSON 파일 경로
    """
    print("📄 배포 정보 저장 중...")
    
    current_dir = Path(__file__).parent
    deployment_info = {
        "agent_name": Config.AGENT_NAME,
        "agent_arn": agent_arn,
        "region": Config.REGION,
        "dependent_agents": agent_arns,
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "description": "Multi-Agent 패턴 기반 통합 투자 자문 시스템 (Memory 포함)"
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
    
    Returns:
        bool: 모든 조건이 충족되면 True
        
    Raises:
        FileNotFoundError: 필수 파일이나 에이전트 배포 정보가 없을 때
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
    
    Investment Advisor Runtime의 전체 배포 프로세스를 관리합니다.
    Multi-Agent 패턴으로 3개 에이전트를 순차 호출하고 Memory에 결과를 저장하는
    통합 투자 자문 시스템을 AWS 서버리스 환경에 배포합니다.
    
    Returns:
        int: 성공 시 0, 실패 시 1
    """
    try:
        print("=" * 70)
        print("🎯 Investment Advisor Runtime 배포")
        print(f"📍 Agent명: {Config.AGENT_NAME}")
        print(f"🌍 리전: {Config.REGION}")
        print(f"⏱️ 최대 대기시간: {Config.MAX_DEPLOY_MINUTES}분")
        print("📋 주요 기능:")
        print("   - Multi-Agent 패턴으로 3개 에이전트 순차 실행")
        print("   - 통합 투자 리포트 생성")
        print("   - AgentCore Memory에 상담 히스토리 저장")
        print("=" * 70)
        
        # 1. 필수 조건 검증
        validate_prerequisites()
        
        # 2. 다른 에이전트 ARN 로드
        agent_arns = load_agent_arns()
        
        # 3. IAM 역할 생성
        role_arn = create_iam_role()
        
        # 4. Runtime 구성
        runtime = configure_runtime(role_arn)
        
        # 5. 배포 및 대기
        success, agent_arn, status = deploy_and_wait(runtime, agent_arns)
        
        if success:
            # 6. 배포 정보 저장
            info_file = save_deployment_info(agent_arn, agent_arns)
            
            print("=" * 70)
            print("🎉 배포 성공!")
            print(f"🔗 Agent ARN: {agent_arn}")
            print(f"📄 배포 정보: {info_file}")
            print("=" * 70)
            
            print("\n📋 다음 단계:")
            print("1. Streamlit 앱 실행: streamlit run app.py")
            print("2. 투자 상담 히스토리 확인")
            print("3. Multi-Agent 통합 분석 테스트")
            
            return 0
        else:
            print("=" * 70)
            print(f"❌ 배포 실패: {status}")
            print("💡 문제 해결 방법:")
            print("1. 모든 에이전트가 배포되었는지 확인")
            print("2. IAM 권한 확인")
            print("3. 로그 확인 후 재시도")
            print("=" * 70)
            return 1
        
    except Exception as e:
        print("=" * 70)
        print(f"❌ 배포 오류: {str(e)}")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())