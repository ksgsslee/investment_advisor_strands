"""
deploy_agentcore_memory.py

AgentCore Memory 배포 스크립트
Investment Advisor용 Memory 생성 및 배포 정보 저장
"""

import json
import time
from pathlib import Path
from bedrock_agentcore.memory import MemoryClient

class Config:
    REGION = "us-west-2"
    MEMORY_NAME = "InvestmentAdvisor_Memory"

def deploy_memory():
    """AgentCore Memory 생성"""
    print("🧠 AgentCore Memory 생성 중...")
    
    memory_client = MemoryClient(region_name=Config.REGION)
    
    try:
        # 기존 메모리 확인
        memories = memory_client.list_memories()
        existing_memory = next((m for m in memories if m['id'].startswith(Config.MEMORY_NAME)), None)
        
        if existing_memory:
            memory_id = existing_memory['id']
            print(f"✅ 기존 메모리 사용: {memory_id}")
        else:
            # 새 메모리 생성 - SUMMARY 전략으로 Long-term 자동 요약
            from bedrock_agentcore.memory.constants import StrategyType
            
            memory = memory_client.create_memory_and_wait(
                name=Config.MEMORY_NAME,
                description="Investment Advisor - Session-based conversation summary",
                strategies=[
                    {
                        StrategyType.SUMMARY.value: {
                            "name": "InvestmentSessionSummary",
                            "description": "Auto-summarizes entire investment consultation session",
                            "namespaces": ["investment/session/{sessionId}"]
                        }
                    }
                ],
                event_expiry_days=7,   # Short-term 보존 기간
                max_wait=300,
                poll_interval=10
            )
            memory_id = memory['id']
            print(f"✅ 새 메모리 생성: {memory_id}")
        
        return memory_id
        
    except Exception as e:
        print(f"❌ 메모리 생성 실패: {e}")
        raise

def save_deployment_info(memory_id):
    """배포 정보 저장"""
    deployment_info = {
        "memory_id": memory_id,
        "memory_name": Config.MEMORY_NAME,
        "region": Config.REGION,
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    info_file = Path(__file__).parent / "deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    return str(info_file)

def main():
    try:
        print("🧠 AgentCore Memory 배포 시작")
        
        # Memory 생성
        memory_id = deploy_memory()
        
        # 배포 정보 저장
        info_file = save_deployment_info(memory_id)
        
        print(f"\n🎉 배포 완료!")
        print(f"📄 배포 정보: {info_file}")
        print(f"🧠 Memory ID: {memory_id}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 배포 실패: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())