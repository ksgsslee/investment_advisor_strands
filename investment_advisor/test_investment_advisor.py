"""
test_investment_advisor.py

Investment Advisor 테스트 코드
환경변수 없이 JSON 파일 기반으로 테스트
"""

import asyncio
import json
from pathlib import Path
from investment_advisor import InvestmentAdvisor, AgentClient

def test_agent_client_loading():
    """Agent ARN과 Memory ID 로딩 테스트"""
    print("🧪 Agent Client 로딩 테스트")
    
    try:
        # AgentClient 초기화 (JSON 파일에서 로드)
        agent_client = AgentClient()
        
        print(f"✅ Financial Analyst ARN: {agent_client.arns['financial']}")
        print(f"✅ Portfolio Architect ARN: {agent_client.arns['portfolio']}")
        print(f"✅ Risk Manager ARN: {agent_client.arns['risk']}")
        print(f"✅ Memory ID: {agent_client.memory_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent Client 로딩 실패: {e}")
        return False

async def test_investment_consultation():
    """투자 상담 테스트"""
    print("\n🧪 투자 상담 테스트")
    
    try:
        # Investment Advisor 초기화
        advisor = InvestmentAdvisor()
        
        # 테스트 입력 데이터
        test_input = {
            "total_investable_amount": 50000000,  # 5천만원
            "age": 35,
            "stock_investment_experience_years": 10,
            "target_amount": 70000000,  # 7천만원
            "investment_purpose": "단기 수익 추구",
            "preferred_sectors": ["ETF (분산 투자)", "성장주 (기술/바이오)"]
        }
        
        print(f"📝 테스트 입력: {json.dumps(test_input, ensure_ascii=False, indent=2)}")
        print("\n🚀 투자 상담 시작...")
        
        # 실시간 스트리밍 테스트
        async for event in advisor.run_consultation(test_input):
            event_type = event.get("type", "unknown")
            
            if event_type == "thinking":
                # AI 사고 과정 출력
                thinking_data = event.get("data", "")
                if thinking_data.strip():
                    print(f"💭 {thinking_data}")
            
            else:
                # 기타 이벤트 출력
                print(f"📢 {event}")
        
        print("\n✅ 투자 상담 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 투자 상담 테스트 실패: {e}")
        return False

def check_deployment_files():
    """배포 파일 존재 여부 확인"""
    print("🧪 배포 파일 확인")
    
    current_dir = Path(__file__).parent
    base_dir = current_dir.parent
    
    required_files = [
        base_dir / "financial_analyst" / "deployment_info.json",
        base_dir / "portfolio_architect" / "deployment_info.json", 
        base_dir / "risk_manager" / "deployment_info.json",
        current_dir / "agentcore_memory" / "deployment_info.json"
    ]
    
    all_exist = True
    for file_path in required_files:
        if file_path.exists():
            print(f"✅ {file_path.name} 존재")
            
            # 파일 내용 간단 확인
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if "agent_arn" in data:
                        print(f"   📋 Agent ARN: {data['agent_arn'][:50]}...")
                    elif "memory_id" in data:
                        print(f"   📋 Memory ID: {data['memory_id']}")
            except Exception as e:
                print(f"   ⚠️ 파일 읽기 오류: {e}")
        else:
            print(f"❌ {file_path.name} 없음")
            all_exist = False
    
    return all_exist

async def main():
    """메인 테스트 함수"""
    print("🎯 Investment Advisor 테스트 시작\n")
    
    # 1. 배포 파일 확인
    if not check_deployment_files():
        print("\n❌ 필요한 배포 파일이 없습니다. 먼저 각 에이전트를 배포하세요.")
        return
    
    print("\n" + "="*50)
    
    # 2. Agent Client 로딩 테스트
    if not test_agent_client_loading():
        print("\n❌ Agent Client 로딩 실패")
        return
    
    print("\n" + "="*50)
    
    # 3. 투자 상담 테스트 (실제 API 호출)
    user_input = input("\n실제 투자 상담 테스트를 진행하시겠습니까? (y/N): ")
    if user_input.lower() == 'y':
        await test_investment_consultation()
    else:
        print("📋 투자 상담 테스트 건너뜀")
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())