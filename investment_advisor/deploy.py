"""
deploy.py
Investment Advisor Orchestrator 배포 스크립트

Agents as Tools 패턴을 활용한 투자 자문 오케스트레이터를 AWS AgentCore Runtime에 배포합니다.
기존에 배포된 전문 에이전트들(Financial Analyst, Portfolio Architect, Risk Manager)의 
ARN을 환경변수로 설정하여 도구로 활용합니다.
"""

import json
import os
import sys
import boto3
import time
from pathlib import Path

# ================================
# 설정 및 초기화
# ================================

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
REGION = "us-west-2"

# AWS 클라이언트 초기화
agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)
iam_client = boto3.client('iam', region_name=REGION)

def load_specialist_agents_info():
    """
    기존에 배포된 전문 에이전트들의 배포 정보를 로드
    
    Returns:
        dict: 전문 에이전트들의 ARN 정보
    """
    agents_info = {}
    
    # Financial Analyst 정보 로드
    financial_analyst_info_file = PROJECT_ROOT / "financial_analyst" / "deployment_info.json"
    if financial_analyst_info_file.exists():
        with open(financial_analyst_info_file, 'r') as f:
            info = json.load(f)
            agents_info["FINANCIAL_ANALYST_ARN"] = info["agent_arn"]
            print(f"✅ Financial Analyst ARN: {info['agent_arn']}")
    else:
        print("❌ Financial Analyst 배포 정보를 찾을 수 없습니다.")
        return None
    
    # Portfolio Architect 정보 로드  
    portfolio_architect_info_file = PROJECT_ROOT / "portfolio_architect" / "deployment_info.json"
    if portfolio_architect_info_file.exists():
        with open(portfolio_architect_info_file, 'r') as f:
            info = json.load(f)
            agents_info["PORTFOLIO_ARCHITECT_ARN"] = info["agent_arn"]
            print(f"✅ Portfolio Architect ARN: {info['agent_arn']}")
    else:
        print("❌ Portfolio Architect 배포 정보를 찾을 수 없습니다.")
        return None
    
    # Risk Manager 정보 로드
    risk_manager_info_file = PROJECT_ROOT / "risk_manager" / "deployment_info.json"  
    if risk_manager_info_file.exists():
        with open(risk_manager_info_file, 'r') as f:
            info = json.load(f)
            agents_info["RISK_MANAGER_ARN"] = info["agent_arn"]
            print(f"✅ Risk Manager ARN: {info['agent_arn']}")
    else:
        print("❌ Risk Manager 배포 정보를 찾을 수 없습니다.")
        return None
    
    return agents_info

def create_iam_role():
    """
    Investment Advisor Orchestrator용 IAM 역할 생성
    
    Returns:
        str: 생성된 IAM 역할 ARN
    """
    role_name = "InvestmentAdvisorOrchestratorRole"
    
    # 신뢰 정책 (AgentCore가 이 역할을 assume할 수 있도록)
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # 권한 정책 (다른 AgentCore Runtime 호출 권한)
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{REGION}::foundation-model/*"
                ]
            },
            {
                "Effect": "Allow", 
                "Action": [
                    "bedrock-agentcore:InvokeAgentRuntime"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream", 
                    "logs:PutLogEvents"
                ],
                "Resource": f"arn:aws:logs:{REGION}:*:*"
            }
        ]
    }
    
    try:
        # IAM 역할 생성
        print(f"🔐 IAM 역할 생성 중: {role_name}")
        
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Investment Advisor Orchestrator를 위한 IAM 역할"
        )
        
        role_arn = response['Role']['Arn']
        print(f"✅ IAM 역할 생성 완료: {role_arn}")
        
        # 권한 정책 연결
        policy_name = "InvestmentAdvisorOrchestratorPolicy"
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy)
        )
        
        print(f"✅ 권한 정책 연결 완료: {policy_name}")
        
        # IAM 역할 전파 대기
        print("⏳ IAM 역할 전파 대기 중...")
        time.sleep(10)
        
        return role_arn
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"ℹ️ IAM 역할이 이미 존재합니다: {role_name}")
        response = iam_client.get_role(RoleName=role_name)
        return response['Role']['Arn']

def create_bedrock_agentcore_yaml(agents_info):
    """
    .bedrock_agentcore.yaml 설정 파일 생성
    
    Args:
        agents_info (dict): 전문 에이전트들의 ARN 정보
    """
    yaml_content = f"""# Investment Advisor Orchestrator AgentCore 설정
# Agents as Tools 패턴을 활용한 투자 자문 오케스트레이터

agent_name: investment-advisor-orchestrator
description: "AI 투자 자문 오케스트레이터 - 전문 에이전트들을 조율하여 완전한 투자 자문 서비스 제공"

# 런타임 설정
runtime:
  type: python
  version: "3.9"
  entry_point: investment_advisor.py
  handler: investment_advisor_orchestrator

# 환경변수 (전문 에이전트 ARN들)
environment:
  FINANCIAL_ANALYST_ARN: "{agents_info['FINANCIAL_ANALYST_ARN']}"
  PORTFOLIO_ARCHITECT_ARN: "{agents_info['PORTFOLIO_ARCHITECT_ARN']}"
  RISK_MANAGER_ARN: "{agents_info['RISK_MANAGER_ARN']}"
  AWS_REGION: "{REGION}"

# 리소스 설정
resources:
  memory: 1024
  timeout: 300

# 로깅 설정
logging:
  level: INFO
  
# 태그
tags:
  Project: "Investment Advisor System"
  Pattern: "Agents as Tools"
  Component: "Orchestrator"
"""
    
    yaml_file = CURRENT_DIR / ".bedrock_agentcore.yaml"
    with open(yaml_file, 'w') as f:
        f.write(yaml_content)
    
    print(f"✅ AgentCore 설정 파일 생성: {yaml_file}")

def create_dockerfile():
    """Dockerfile 생성"""
    dockerfile_content = """# Investment Advisor Orchestrator Dockerfile
FROM public.ecr.aws/lambda/python:3.9

# 작업 디렉토리 설정
WORKDIR ${LAMBDA_TASK_ROOT}

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY investment_advisor.py .

# 엔트리포인트 설정
CMD ["investment_advisor.investment_advisor_orchestrator"]
"""
    
    dockerfile_path = CURRENT_DIR / "Dockerfile"
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    print(f"✅ Dockerfile 생성: {dockerfile_path}")

def create_requirements_txt():
    """requirements.txt 생성"""
    requirements_content = """# Investment Advisor Orchestrator 의존성
strands>=0.1.0
bedrock-agentcore>=0.1.0
boto3>=1.34.0
"""
    
    requirements_path = CURRENT_DIR / "requirements.txt"
    with open(requirements_path, 'w') as f:
        f.write(requirements_content)
    
    print(f"✅ requirements.txt 생성: {requirements_path}")

def deploy_agent_runtime(role_arn):
    """
    Investment Advisor Orchestrator를 AgentCore Runtime에 배포
    
    Args:
        role_arn (str): IAM 역할 ARN
        
    Returns:
        str: 배포된 Agent ARN
    """
    agent_name = "investment-advisor-orchestrator"
    
    print(f"🚀 AgentCore Runtime 배포 시작: {agent_name}")
    
    try:
        # AgentCore Runtime 생성
        response = agentcore_client.create_agent_runtime(
            agentRuntimeName=agent_name,
            description="AI 투자 자문 오케스트레이터 - Agents as Tools 패턴 구현",
            runtimeRoleArn=role_arn,
            runtimeConfig={
                "sourceLocation": str(CURRENT_DIR),
                "environmentVariables": {
                    "AWS_REGION": REGION
                }
            }
        )
        
        agent_arn = response['agentRuntimeArn']
        print(f"✅ AgentCore Runtime 생성 완료: {agent_arn}")
        
        # 배포 상태 확인
        print("⏳ 배포 상태 확인 중...")
        max_attempts = 30
        
        for attempt in range(max_attempts):
            try:
                status_response = agentcore_client.get_agent_runtime(
                    agentRuntimeArn=agent_arn
                )
                
                status = status_response['agentRuntime']['status']
                print(f"📊 배포 상태 ({attempt + 1}/{max_attempts}): {status}")
                
                if status == 'ACTIVE':
                    print("✅ 배포 완료!")
                    break
                elif status in ['FAILED', 'STOPPED']:
                    print(f"❌ 배포 실패: {status}")
                    return None
                    
                time.sleep(10)
                
            except Exception as e:
                print(f"⚠️ 상태 확인 중 오류: {e}")
                time.sleep(5)
        else:
            print("⏰ 배포 시간 초과")
            return None
        
        return agent_arn
        
    except Exception as e:
        print(f"❌ AgentCore Runtime 배포 실패: {e}")
        return None

def save_deployment_info(agent_arn, agents_info):
    """
    배포 정보를 JSON 파일로 저장
    
    Args:
        agent_arn (str): 배포된 Agent ARN
        agents_info (dict): 전문 에이전트들의 ARN 정보
    """
    deployment_info = {
        "agent_arn": agent_arn,
        "region": REGION,
        "deployment_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "specialist_agents": agents_info,
        "pattern": "Agents as Tools",
        "description": "AI 투자 자문 오케스트레이터"
    }
    
    info_file = CURRENT_DIR / "deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 배포 정보 저장: {info_file}")

def main():
    """메인 배포 함수"""
    print("🎯 Investment Advisor Orchestrator 배포 시작")
    print("=" * 60)
    
    try:
        # 1. 전문 에이전트들의 배포 정보 로드
        print("\n📋 1단계: 전문 에이전트 정보 로드")
        agents_info = load_specialist_agents_info()
        if not agents_info:
            print("❌ 전문 에이전트들이 먼저 배포되어야 합니다.")
            print("다음 순서로 배포를 진행하세요:")
            print("1. cd financial_analyst && python deploy.py")
            print("2. cd portfolio_architect && python deploy.py") 
            print("3. cd risk_manager && python deploy.py")
            return
        
        # 2. IAM 역할 생성
        print("\n🔐 2단계: IAM 역할 생성")
        role_arn = create_iam_role()
        
        # 3. 설정 파일들 생성
        print("\n📝 3단계: 설정 파일 생성")
        create_bedrock_agentcore_yaml(agents_info)
        create_dockerfile()
        create_requirements_txt()
        
        # 4. AgentCore Runtime 배포
        print("\n🚀 4단계: AgentCore Runtime 배포")
        agent_arn = deploy_agent_runtime(role_arn)
        
        if not agent_arn:
            print("❌ 배포 실패")
            return
        
        # 5. 배포 정보 저장
        print("\n💾 5단계: 배포 정보 저장")
        save_deployment_info(agent_arn, agents_info)
        
        print("\n" + "=" * 60)
        print("🎉 Investment Advisor Orchestrator 배포 완료!")
        print(f"📍 Agent ARN: {agent_arn}")
        print(f"🌍 Region: {REGION}")
        print("\n📱 다음 단계:")
        print("   streamlit run app.py")
        
    except Exception as e:
        print(f"\n❌ 배포 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()