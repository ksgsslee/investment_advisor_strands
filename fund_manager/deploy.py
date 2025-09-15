"""
deploy.py

Fund Manager AgentCore Runtime 배포 스크립트
"""

import sys
import time
import json
from pathlib import Path
from bedrock_agentcore_starter_toolkit import Runtime

# 공통 설정 및 shared 모듈 경로 추가
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))
sys.path.insert(0, str(root_path / "shared"))

from config import Config as GlobalConfig
from runtime_utils import create_agentcore_runtime_role

class Config:
    """Fund Manager 배포 설정"""
    REGION = GlobalConfig.REGION
    AGENT_NAME = GlobalConfig.FUND_MANAGER_NAME

def load_agent_arns():
    """다른 에이전트들의 배포 정보 로드"""
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

def load_memory_info():
    """AgentCore Memory 배포 정보 로드"""
    print("🧠 AgentCore Memory 배포 정보 로드 중...")
    
    info_file = Path(__file__).parent / "agentcore_memory" / "deployment_info.json"
    
    if not info_file.exists():
        raise FileNotFoundError(
            "AgentCore Memory가 먼저 배포되어야 합니다.\n"
            "다음 명령을 실행하세요: cd agentcore_memory && python deploy_agentcore_memory.py"
        )
    
    with open(info_file, 'r') as f:
        memory_info = json.load(f)
        memory_id = memory_info["memory_id"]
        print(f"✅ Memory ID: {memory_id}")
        return memory_id

def create_iam_role_with_agent_permissions():
    """Fund Manager용 IAM 역할 생성 (다른 에이전트 호출 권한 포함)"""
    print("🔐 Fund Manager IAM 역할 생성 중...")
    
    # 기본 AgentCore Runtime 역할 생성
    iam_role = create_agentcore_runtime_role(Config.AGENT_NAME, Config.REGION)
    iam_role_name = iam_role['Role']['RoleName']
    
    # 다른 에이전트 호출 권한 추가
    _add_agent_call_permissions(iam_role_name)
    
    return iam_role['Role']['Arn'], iam_role_name

def _add_agent_call_permissions(role_name):
    """다른 에이전트 호출 권한을 IAM 역할에 추가"""
    print("🔐 다른 에이전트 호출 권한 추가 중...")
    
    import boto3
    iam_client = boto3.client('iam')
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    additional_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeAgentRuntime",
                    "bedrock-agentcore:GetAgentRuntime"
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/financial_analyst-*",
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/portfolio_architect-*",
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/risk_manager-*",
                    f"arn:aws:bedrock-agentcore:{Config.REGION}:{account_id}:runtime/fund_manager-*"
                ]
            }
        ]
    }
    
    try:
        iam_client.put_role_policy(
            PolicyDocument=json.dumps(additional_policy),
            PolicyName="FundManagerAgentCallsPolicy",
            RoleName=role_name
        )
        print("✅ 다른 에이전트 호출 권한 추가 완료")
    except Exception as e:
        print(f"⚠️ 추가 권한 설정 오류: {e}")

def deploy_fund_manager(agent_arns, memory_id):
    """Fund Manager Runtime 배포"""
    print("🎯 Fund Manager 배포 중...")
    
    # IAM 역할 생성 (권한 포함)
    role_arn, iam_role_name = create_iam_role_with_agent_permissions()
    
    # Runtime 구성
    current_dir = Path(__file__).parent
    runtime = Runtime()
    runtime.configure(
        entrypoint=str(current_dir / "fund_manager.py"),
        execution_role=role_arn,
        auto_create_ecr=True,
        requirements_file=str(current_dir / "requirements.txt"),
        region=Config.REGION,
        agent_name=Config.AGENT_NAME
    )
    
    # 환경변수 설정
    env_vars = {
        "FINANCIAL_ANALYST_ARN": agent_arns["financial_analyst"],
        "PORTFOLIO_ARCHITECT_ARN": agent_arns["portfolio_architect"],
        "RISK_MANAGER_ARN": agent_arns["risk_manager"],
        "FUND_MEMORY_ID": memory_id,
        "AWS_REGION": Config.REGION
    }
    
    # 배포 실행
    launch_result = runtime.launch(auto_update_on_conflict=True, env_vars=env_vars)
    
    # 배포 완료 대기
    for i in range(30):  # 최대 15분 대기
        try:
            status = runtime.status().endpoint['status']
            print(f"📊 상태: {status} ({i*30}초 경과)")
            if status in ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']:
                break
        except Exception as e:
            print(f"⚠️ 상태 확인 오류: {e}")
        time.sleep(30)
    
    if status != 'READY':
        raise Exception(f"배포 실패: {status}")
    
    # ECR 리포지토리 이름 추출
    ecr_repo_name = None
    if hasattr(launch_result, 'ecr_uri') and launch_result.ecr_uri:
        ecr_repo_name = launch_result.ecr_uri.split('/')[-1].split(':')[0]
    
    return {
        "agent_arn": launch_result.agent_arn,
        "agent_id": launch_result.agent_id,
        "region": Config.REGION,
        "iam_role_name": iam_role_name,
        "ecr_repo_name": ecr_repo_name
    }

def save_deployment_info(fund_manager_info, agent_arns):
    """배포 정보 저장"""
    deployment_info = {
        "agent_name": Config.AGENT_NAME,
        "agent_arn": fund_manager_info["agent_arn"],
        "agent_id": fund_manager_info["agent_id"],
        "region": Config.REGION,
        "iam_role_name": fund_manager_info["iam_role_name"],
        "ecr_repo_name": fund_manager_info.get("ecr_repo_name"),
        "dependent_agents": agent_arns,
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = Path(__file__).parent / "deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    return str(info_file)

def main():
    try:
        print("🎯 Fund Manager Runtime 배포")
        
        # 다른 에이전트 ARN 로드
        agent_arns = load_agent_arns()
        
        # AgentCore Memory 정보 로드
        memory_id = load_memory_info()
        
        # Fund Manager 배포
        fund_manager_info = deploy_fund_manager(agent_arns, memory_id)
        
        # 배포 정보 저장
        info_file = save_deployment_info(fund_manager_info, agent_arns)
        
        print(f"\n🎉 배포 완료!")
        print(f"📄 배포 정보: {info_file}")
        print(f"🔗 Fund Manager ARN: {fund_manager_info['agent_arn']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 배포 실패: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())