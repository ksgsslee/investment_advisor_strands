"""
investment_advisor.py
Multi-Agent Investment Advisor - Sequential Agent Pattern

3개의 전문 에이전트가 순차적으로 협업하여 종합적인 투자 분석을 제공합니다.
Sequential Multi-Agent 패턴을 활용하여 체계적인 투자 상담을 수행합니다.

주요 기능:
- Multi-Agent 패턴: 3개 전문 에이전트 순차 호출
- Sequential Processing: 각 단계별 순차 처리
- 실시간 스트리밍: 분석 과정 실시간 시각화
- 구조화된 결과: JSON 형태의 체계적인 분석 결과
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any
from strands import Agent
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import boto3

# ================================
# 전역 설정
# ================================

app = BedrockAgentCoreApp()

class Config:
    """Investment Advisor 설정 상수"""
    # 보고서 작성자 모델 설정
    REPORT_MODEL_ID = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    REPORT_TEMPERATURE = 0.1
    REPORT_MAX_TOKENS = 4000
    
    REGION = "us-west-2"

# ================================
# 유틸리티 함수들
# ================================

def extract_json_from_streaming(response_stream):
    """
    스트리밍 응답에서 JSON 결과 추출
    
    Args:
        response_stream: AgentCore 스트리밍 응답
        
    Returns:
        dict: 추출된 결과 데이터
    """
    try:
        for line in response_stream.iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    if event_data.get("type") == "streaming_complete":
                        return event_data
                except json.JSONDecodeError:
                    continue
        return None
    except Exception as e:
        print(f"스트리밍 처리 오류: {e}")
        return None

def extract_json_from_text(text_content):
    """
    텍스트에서 JSON 데이터를 추출하는 함수
    
    Args:
        text_content (str): JSON이 포함된 텍스트
        
    Returns:
        dict: 파싱된 JSON 데이터 또는 None
    """
    if isinstance(text_content, dict):
        return text_content
    
    if not isinstance(text_content, str):
        return None
    
    # JSON 블록 찾기
    start_idx = text_content.find('{')
    end_idx = text_content.rfind('}') + 1
    
    if start_idx != -1 and end_idx != -1:
        try:
            json_str = text_content[start_idx:end_idx]
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    return None

# ================================
# 외부 에이전트 호출 클라이언트
# ================================

class AgentClient:
    """외부 에이전트 호출을 위한 클라이언트 클래스"""
    
    def __init__(self):
        self.agentcore_client = None
        self.agent_arns = {}
    
    def _initialize_clients(self):
        """에이전트 클라이언트 초기화 (환경변수 우선, 파일 백업)"""
        if self.agentcore_client is None:
            self.agentcore_client = boto3.client('bedrock-agentcore', region_name=Config.REGION)
            
            # 환경변수에서 Agent ARN 로드 (Runtime 환경)
            financial_arn = os.getenv("FINANCIAL_ANALYST_ARN")
            portfolio_arn = os.getenv("PORTFOLIO_ARCHITECT_ARN") 
            risk_arn = os.getenv("RISK_MANAGER_ARN")
            
            if financial_arn and portfolio_arn and risk_arn:
                # Runtime 환경: 환경변수 사용
                self.agent_arns = {
                    "financial_analyst": financial_arn,
                    "portfolio_architect": portfolio_arn,
                    "risk_manager": risk_arn
                }
                print("✅ 환경변수에서 Agent ARN 로드 완료")
            else:
                # 로컬 환경: 파일에서 로드
                try:
                    base_path = Path(__file__).parent.parent
                    
                    with open(base_path / "financial_analyst" / "deployment_info.json") as f:
                        self.agent_arns["financial_analyst"] = json.load(f)["agent_arn"]
                    
                    with open(base_path / "portfolio_architect" / "deployment_info.json") as f:
                        self.agent_arns["portfolio_architect"] = json.load(f)["agent_arn"]
                    
                    with open(base_path / "risk_manager" / "deployment_info.json") as f:
                        self.agent_arns["risk_manager"] = json.load(f)["agent_arn"]
                    
                    print("✅ 파일에서 Agent ARN 로드 완료")
                except Exception as e:
                    raise RuntimeError(f"Agent ARN 로드 실패: {e}")
    
    def _call_agent(self, agent_name, payload_key, data):
        """공통 에이전트 호출 로직"""
        try:
            self._initialize_clients()
            
            # 데이터를 문자열로 변환
            if isinstance(data, dict):
                input_data = json.dumps(data, ensure_ascii=False)
            else:
                input_data = str(data)
            
            response = self.agentcore_client.invoke_agent_runtime(
                agentRuntimeArn=self.agent_arns[agent_name],
                qualifier="DEFAULT",
                payload=json.dumps({payload_key: input_data if payload_key != "input_data" else data})
            )
            
            result = extract_json_from_streaming(response["response"])
            
            if result is None:
                return {"error": f"{agent_name} 결과를 가져올 수 없습니다"}
            
            return result
            
        except Exception as e:
            print(f"{agent_name} 호출 실패: {e}")
            return {"error": str(e)}
    
    def call_financial_analyst(self, user_input):
        """재무 분석사 에이전트 호출"""
        return self._call_agent("financial_analyst", "input_data", user_input)
    
    def call_portfolio_architect(self, financial_analysis):
        """포트폴리오 설계사 에이전트 호출"""
        return self._call_agent("portfolio_architect", "financial_analysis", financial_analysis)
    
    def call_risk_manager(self, portfolio_data):
        """리스크 관리자 에이전트 호출"""
        return self._call_agent("risk_manager", "portfolio_data", portfolio_data)

# 전역 클라이언트 인스턴스
agent_client = AgentClient()

# ================================
# 메인 투자 자문 클래스
# ================================

class InvestmentAdvisor:
    """
    Multi-Agent 투자 자문 시스템 - Sequential Pattern
    
    3개의 전문 에이전트가 순차적으로 협업하여 종합적인 투자 분석을 제공합니다.
    Sequential Multi-Agent 패턴을 활용하여 체계적인 투자 상담을 수행합니다.
    """
    
    def __init__(self):
        """
        투자 자문 시스템 초기화
        
        투자 보고서 작성 AI 에이전트를 생성하고 종합 분석 보고서 작성을 위한 시스템 프롬프트를 설정합니다.
        """
        self._create_report_agent()
    
    def _create_report_agent(self):
        """투자 보고서 작성 AI 에이전트 생성"""
        self.report_agent = Agent(
            name="investment_report_writer",
            model=BedrockModel(
                model_id=Config.REPORT_MODEL_ID,
                temperature=Config.REPORT_TEMPERATURE,
                max_tokens=Config.REPORT_MAX_TOKENS
            ),
            system_prompt=self._get_report_prompt()
        )
        
    def _get_report_prompt(self) -> str:
        """
        투자 보고서 작성 AI 에이전트용 시스템 프롬프트 생성
        
        Returns:
            str: 투자 보고서 작성자 역할과 작업 지침이 포함된 프롬프트
        """
        return """당신은 투자 보고서 작성 전문가입니다. 고객의 투자 정보와 3개 전문 에이전트의 분석 결과를 종합하여 실행 가능한 투자 가이드 보고서를 작성해야 합니다.

입력 데이터는 다음과 같은 JSON 형식으로 제공됩니다:
{
"user_input": {
    "total_investable_amount": <총 투자 가능 금액>,
    "age": <나이>,
    "stock_investment_experience_years": <주식 투자 경험 연수>,
    "target_amount": <1년 후 목표 금액>
},
"financial_analysis": <재무 분석사 결과>,
"portfolio_design": <포트폴리오 설계사 결과>,
"risk_analysis": <리스크 관리자 결과>
}

다음 구조로 종합 투자 보고서를 작성하세요:

## 📋 투자 상담 종합 보고서

### 1. 고객 프로필 요약
- 투자 가능 금액, 나이, 경험, 목표 등 핵심 정보 요약

### 2. 재무 분석 결과
- 위험 성향 평가 및 근거
- 필요 연간 수익률 및 달성 가능성

### 3. 추천 포트폴리오
- 자산 배분 비율 및 근거
- 추천 투자 상품 및 전략

### 4. 리스크 관리 전략
- 주요 위험 요소 및 대응 방안
- 시나리오별 손실 가능성

### 5. 실행 가이드
- 단계별 투자 실행 계획
- 주의사항 및 모니터링 포인트

### 6. 결론 및 권고사항
- 핵심 메시지 및 다음 단계

보고서는 고객이 바로 실행할 수 있도록 구체적이고 실용적으로 작성하세요.
전문 용어는 쉽게 설명하고, 숫자와 데이터는 명확하게 제시하세요.

출력 형식:
- 마크다운 형식으로 작성
- 이모지를 적절히 활용하여 가독성 향상
- 추가적인 JSON이나 코드 블록은 포함하지 마세요"""

    async def run_consultation_async(self, user_input):
        """
        실시간 스트리밍 투자 상담 수행 (Sequential Multi-Agent 패턴)
        
        3개의 전문 에이전트가 순차적으로 협업하여 종합적인 투자 분석을 제공합니다.
        분석 과정과 결과를 스트리밍 이벤트로 실시간 전송합니다.
        
        Args:
            user_input (dict): 고객 투자 정보
                - total_investable_amount: 총 투자 가능 금액
                - age: 나이
                - stock_investment_experience_years: 주식 투자 경험 년수
                - target_amount: 1년 후 목표 금액
            
        Yields:
            dict: 스트리밍 이벤트
                - type: 이벤트 타입 (data, step_complete, streaming_complete, error)
                - message: 진행 상황 메시지
                - data: 각 단계별 분석 결과
                - final_result: 최종 종합 결과 (실행 가능한 투자 가이드 포함)
        """
        try:
            # 1단계: 재무 분석 수행
            yield {
                "type": "data", 
                "message": "🔍 재무 분석사가 위험 성향과 목표 수익률을 계산 중입니다."
            }
            
            financial_analyst_response = agent_client.call_financial_analyst(user_input)
            if "error" in financial_analyst_response:
                yield {"type": "error", "error": f"재무 분석 실패: {financial_analyst_response['error']}"}
                return
                
            reflection_result = financial_analyst_response['reflection_result'].lower()
            financial_result = financial_analyst_response['analysis_data']
            
            # Reflection 검증 확인
            if reflection_result != "yes":
                yield {"type": "error", "error": f"재무 분석 검증 실패: {financial_result}"}
                return

            yield {
                "type": "step_complete",
                "step_name": "financial_analyst",
                "data": financial_result
            }

            # 2단계: 포트폴리오 설계 수행
            yield {
                "type": "data", 
                "message": "📊 포트폴리오 설계사가 최적 자산 배분을 계산 중입니다."
            }
                            
            portfolio_architect_response = agent_client.call_portfolio_architect(financial_result)
            if "error" in portfolio_architect_response:
                yield {"type": "error", "error": f"포트폴리오 설계 실패: {portfolio_architect_response['error']}"}
                return
                
            portfolio_result = extract_json_from_text(portfolio_architect_response['portfolio_result'])
            
            yield {
                "type": "step_complete",
                "step_name": "portfolio_architect",
                "data": portfolio_result
            }

            # 3단계: 리스크 분석 수행
            yield {
                "type": "data", 
                "message": "⚠️ 리스크 관리자가 시나리오별 위험도를 분석 중입니다."
            }
            
            risk_manager_response = agent_client.call_risk_manager(portfolio_result)
            if "error" in risk_manager_response:
                yield {"type": "error", "error": f"리스크 분석 실패: {risk_manager_response['error']}"}
                return
                
            risk_result = extract_json_from_text(risk_manager_response['risk_result'])
            
            yield {
                "type": "step_complete",
                "step_name": "risk_manager",
                "data": risk_result
            }

            # 4단계: 종합 보고서 작성
            yield {
                "type": "data", 
                "message": "📝 투자 보고서 작성자가 종합 분석 보고서를 작성 중입니다."
            }
            
            # 모든 분석 결과를 종합하여 보고서 작성
            comprehensive_data = {
                "user_input": user_input,
                "financial_analysis": financial_result,
                "portfolio_design": portfolio_result,
                "risk_analysis": risk_result
            }
            
            try:
                comprehensive_data_str = json.dumps(comprehensive_data, ensure_ascii=False)
                report_response = self.report_agent(comprehensive_data_str)
                final_report = report_response.message['content'][0]['text']
                
                yield {
                    "type": "step_complete",
                    "step_name": "종합 보고서 작성",
                    "data": {"final_report": final_report}
                }
                
            except Exception as e:
                yield {"type": "error", "error": f"보고서 작성 실패: {str(e)}"}
                return
            
            # 분석 완료 신호 (최종 결과 포함)
            yield {
                "type": "streaming_complete",
                "final_result": {
                    "financial_analysis": financial_result,
                    "portfolio_design": portfolio_result,
                    "risk_analysis": risk_result,
                    "final_report": final_report
                }
            }

        except Exception as e:
            yield {"type": "error", "error": str(e), "status": "error"}

# ================================
# AgentCore Runtime 엔트리포인트
# ================================

# 전역 인스턴스 (지연 초기화)
advisor = None

@app.entrypoint
async def investment_advisor_entrypoint(payload):
    """
    AgentCore Runtime 엔트리포인트
    
    AWS AgentCore Runtime 환경에서 호출되는 메인 함수입니다.
    3개의 전문 에이전트를 순차적으로 호출하여 종합적인 투자 분석을 제공합니다.
    
    Args:
        payload (dict): 요청 페이로드
            - input_data: 고객 투자 정보
    
    Yields:
        dict: 스트리밍 응답 이벤트들
    
    Environment Variables:
        - FINANCIAL_ANALYST_ARN: Financial Analyst Agent ARN
        - PORTFOLIO_ARCHITECT_ARN: Portfolio Architect Agent ARN
        - RISK_MANAGER_ARN: Risk Manager Agent ARN
        - AWS_REGION: AWS 리전 (기본값: us-west-2)
    
    Note:
        - 지연 초기화로 첫 호출 시에만 InvestmentAdvisor 인스턴스 생성
        - 실시간 스트리밍으로 분석 과정 전송
        - Sequential Multi-Agent 패턴으로 3개 에이전트 순차 협업
        - 구조화된 JSON 형태의 분석 결과 제공
    """
    global advisor
    
    # Runtime 환경에서 지연 초기화
    if advisor is None:
        advisor = InvestmentAdvisor()

    # 고객 정보 추출 및 투자 상담 실행
    user_input = payload.get("input_data")
    async for chunk in advisor.run_consultation_async(user_input):
        yield chunk

# ================================
# 직접 실행 시 Runtime 서버 시작
# ================================

if __name__ == "__main__":
    app.run()