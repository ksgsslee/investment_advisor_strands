"""
investment_advisor.py
Strands Agents as Tools 기반 Investment Advisor (간단 버전)

배포된 3개 에이전트를 @tool로 래핑하고 오케스트레이터가 조정하는 간단한 구조
"""

import json
import time
import boto3
from pathlib import Path
from datetime import datetime
from strands import Agent, tool
from strands.models.bedrock import BedrockModel

# ================================
# 설정
# ================================

REGION = "us-west-2"

# 전역 변수
agentcore_client = None
agent_arns = {}
memory_storage = {}

# ================================
# 간단한 유틸리티 함수들
# ================================

def extract_json_from_streaming(response_stream):
    """스트리밍 응답에서 JSON 결과 추출 (간단 버전)"""
    try:
        all_text = ""
        
        for line in response_stream.iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    
                    # text_chunk에서 텍스트 누적
                    if event_data.get("type") == "text_chunk":
                        all_text += event_data.get("data", "")
                    
                    # streaming_complete에서 최종 결과 시도
                    elif event_data.get("type") == "streaming_complete":
                        # 여러 필드에서 결과 찾기
                        for field in ["analysis_data", "portfolio_result", "risk_result"]:
                            if field in event_data:
                                return json.loads(event_data[field])
                        
                        # 누적된 텍스트에서 JSON 추출
                        if all_text:
                            return extract_json_from_text(all_text)
                            
                except json.JSONDecodeError:
                    continue
        
        # 마지막으로 누적된 텍스트에서 JSON 시도
        if all_text:
            return extract_json_from_text(all_text)
            
        return None
        
    except Exception as e:
        print(f"스트리밍 처리 오류: {e}")
        return None

def extract_json_from_text(text):
    """텍스트에서 JSON 추출 (간단 버전)"""
    if not text:
        return None
        
    try:
        # JSON 블록 찾기
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
    except:
        pass
    
    return None

def initialize_system():
    """시스템 초기화"""
    global agentcore_client, agent_arns
    
    if agentcore_client is None:
        agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)
        
        # ARN 로드
        base_path = Path(__file__).parent.parent
        
        # Financial Analyst
        with open(base_path / "financial_analyst" / "deployment_info.json") as f:
            agent_arns["financial_analyst"] = json.load(f)["agent_arn"]
        
        # Portfolio Architect
        with open(base_path / "portfolio_architect" / "deployment_info.json") as f:
            agent_arns["portfolio_architect"] = json.load(f)["agent_arn"]
        
        # Risk Manager
        with open(base_path / "risk_manager" / "deployment_info.json") as f:
            agent_arns["risk_manager"] = json.load(f)["agent_arn"]
        
        print("✅ 모든 에이전트 ARN 로드 완료")

# ================================
# @tool 데코레이터로 에이전트들을 도구로 래핑
# ================================

@tool
def financial_analyst_tool(user_input_json: str, session_id: str) -> str:
    """재무 분석 전문가 - 위험 성향과 목표 수익률 계산"""
    try:
        initialize_system()
        print("🔍 Financial Analyst 호출 중...")
        
        user_input = json.loads(user_input_json)
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arns["financial_analyst"],
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": user_input})
        )
        
        result = extract_json_from_streaming(response["response"])
        
        if result:
            # 메모리에 저장
            if session_id not in memory_storage:
                memory_storage[session_id] = {}
            memory_storage[session_id]["financial_analysis"] = result
            
            print("✅ Financial Analyst 완료!")
            return json.dumps(result, ensure_ascii=False)
        else:
            print("❌ 결과를 받지 못했습니다")
            return json.dumps({"error": "결과를 받지 못했습니다"}, ensure_ascii=False)
            
    except Exception as e:
        print(f"❌ Financial Analyst 실패: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@tool
def portfolio_architect_tool(session_id: str) -> str:
    """포트폴리오 설계 전문가 - 맞춤형 투자 포트폴리오 설계"""
    try:
        initialize_system()
        print("📊 Portfolio Architect 호출 중...")
        
        # 메모리에서 재무 분석 결과 가져오기
        if session_id not in memory_storage or "financial_analysis" not in memory_storage[session_id]:
            print("❌ 재무 분석 결과가 없습니다")
            return json.dumps({"error": "재무 분석 결과가 없습니다"}, ensure_ascii=False)
        
        financial_result = memory_storage[session_id]["financial_analysis"]
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arns["portfolio_architect"],
            qualifier="DEFAULT",
            payload=json.dumps({"financial_analysis": financial_result})
        )
        
        result = extract_json_from_streaming(response["response"])
        
        if result:
            # 메모리에 저장
            memory_storage[session_id]["portfolio_design"] = result
            
            print("✅ Portfolio Architect 완료!")
            return json.dumps(result, ensure_ascii=False)
        else:
            print("❌ 결과를 받지 못했습니다")
            return json.dumps({"error": "결과를 받지 못했습니다"}, ensure_ascii=False)
            
    except Exception as e:
        print(f"❌ Portfolio Architect 실패: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@tool
def risk_manager_tool(session_id: str) -> str:
    """리스크 관리 전문가 - 시나리오별 리스크 분석 및 조정 전략"""
    try:
        initialize_system()
        print("⚠️ Risk Manager 호출 중...")
        
        # 메모리에서 포트폴리오 결과 가져오기
        if session_id not in memory_storage or "portfolio_design" not in memory_storage[session_id]:
            print("❌ 포트폴리오 설계 결과가 없습니다")
            return json.dumps({"error": "포트폴리오 설계 결과가 없습니다"}, ensure_ascii=False)
        
        portfolio_result = memory_storage[session_id]["portfolio_design"]
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arns["risk_manager"],
            qualifier="DEFAULT",
            payload=json.dumps({"portfolio_data": portfolio_result})
        )
        
        result = extract_json_from_streaming(response["response"])
        
        if result:
            # 메모리에 저장
            memory_storage[session_id]["risk_analysis"] = result
            
            print("✅ Risk Manager 완료!")
            return json.dumps(result, ensure_ascii=False)
        else:
            print("❌ 결과를 받지 못했습니다")
            return json.dumps({"error": "결과를 받지 못했습니다"}, ensure_ascii=False)
            
    except Exception as e:
        print(f"❌ Risk Manager 실패: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@tool
def get_memory_data(session_id: str) -> str:
    """메모리에서 모든 분석 결과 조회"""
    try:
        print("🔍 메모리에서 모든 분석 결과 조회 중...")
        
        if session_id in memory_storage:
            data = memory_storage[session_id]
            print("📋 모든 데이터 조회 완료!")
            return json.dumps(data, ensure_ascii=False)
        else:
            print("❌ 세션 데이터가 없습니다")
            return json.dumps({"error": "세션 데이터가 없습니다"}, ensure_ascii=False)
            
    except Exception as e:
        print(f"❌ 메모리 조회 실패: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

# ================================
# 오케스트레이터 에이전트
# ================================

class InvestmentAdvisor:
    """간단한 Strands Agents as Tools 기반 Investment Advisor"""
    
    def __init__(self):
        initialize_system()
        
        self.orchestrator = Agent(
            name="investment_advisor",
            model=BedrockModel(
                model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                temperature=0.2,
                max_tokens=4000
            ),
            tools=[
                financial_analyst_tool,
                portfolio_architect_tool,
                risk_manager_tool,
                get_memory_data
            ],
            system_prompt="""당신은 투자 자문 전문가입니다.

사용자의 투자 상담 요청을 받으면 다음 순서로 진행하세요:

1. 세션 ID 생성 (consultation_현재시간)
2. financial_analyst_tool(사용자입력JSON, 세션ID) 호출 - 재무 분석
3. portfolio_architect_tool(세션ID) 호출 - 포트폴리오 설계  
4. risk_manager_tool(세션ID) 호출 - 리스크 분석
5. get_memory_data(세션ID) 호출 - 모든 결과 조회
6. 종합 투자 리포트 생성

각 단계의 결과를 사용자에게 명확히 설명하고, 최종적으로 실행 가능한 투자 가이드를 제공하세요."""
        )
    
    async def run_consultation_async(self, user_input, user_id=None):
        """투자 상담 실행 (스트리밍)"""
        try:
            session_id = f"consultation_{int(time.time())}"
            
            print(f"\n🚀 투자 상담 시작 (세션: {session_id})")
            print("=" * 50)
            
            # 사용자 입력 준비
            consultation_input = {
                "user_input": user_input,
                "session_id": session_id,
                "user_id": user_id,
                "instruction": f"세션 ID '{session_id}'를 사용하여 투자 상담을 진행해주세요."
            }
            
            # 오케스트레이터 스트리밍 실행
            async for event in self.orchestrator.stream_async(json.dumps(consultation_input, ensure_ascii=False)):
                yield {
                    "session_id": session_id,
                    **event
                }
            
            print("=" * 50)
            print("🎉 투자 상담 완료!")
            
        except Exception as e:
            print(f"❌ 상담 실패: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "session_id": session_id if 'session_id' in locals() else None
            }
    
    def run_consultation(self, user_input, user_id=None):
        """투자 상담 실행 (동기 버전 - 호환성 유지)"""
        try:
            session_id = f"consultation_{int(time.time())}"
            
            print(f"\n🚀 투자 상담 시작 (세션: {session_id})")
            print("=" * 50)
            
            # 사용자 입력 준비
            consultation_input = {
                "user_input": user_input,
                "session_id": session_id,
                "user_id": user_id,
                "instruction": f"세션 ID '{session_id}'를 사용하여 투자 상담을 진행해주세요."
            }
            
            # 오케스트레이터 실행
            response = self.orchestrator(json.dumps(consultation_input, ensure_ascii=False))
            
            print("=" * 50)
            print("🎉 투자 상담 완료!")
            
            return {
                "status": "success",
                "session_id": session_id,
                "response": response.message['content'][0]['text'],
                "memory_data": memory_storage.get(session_id, {})
            }
            
        except Exception as e:
            print(f"❌ 상담 실패: {e}")
            return {"status": "error", "error": str(e)}

# ================================
# 메인 실행
# ================================

def main():
    """간단한 테스트"""
    print("🤖 Investment Advisor 테스트")
    print("=" * 40)
    
    advisor = InvestmentAdvisor()
    
    # 테스트 데이터
    user_input = {
        "total_investable_amount": 50000000,    # 5천만원
        "age": 35,                             # 35세
        "stock_investment_experience_years": 7,  # 7년 경험
        "target_amount": 65000000              # 6천5백만원 목표
    }
    
    print(f"📝 테스트 데이터: {user_input}")
    print()
    
    # 상담 실행
    result = advisor.run_consultation(user_input, "test_user")
    
    if result["status"] == "success":
        print(f"\n✅ 상담 성공!")
        print(f"세션 ID: {result['session_id']}")
        print(f"\n📋 AI 응답:")
        print(result["response"])
        
        # 결과 저장
        output_file = f"consultation_result_{result['session_id']}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 결과 저장: {output_file}")
        
    else:
        print(f"\n❌ 상담 실패: {result.get('error')}")

if __name__ == "__main__":
    main()