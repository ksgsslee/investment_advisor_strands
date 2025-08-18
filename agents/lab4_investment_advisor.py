"""
Lab 4: Investment Advisor with Multi-Agent Pattern
투자 어드바이저 + Multi-Agent 패턴 구현 (Graph 패턴 사용)
"""
import json
from typing import Dict, Any
from strands import Agent
from strands.multiagent import GraphBuilder
from strands.models.anthropic import AnthropicModel
from config import MODELS, ANTHROPIC_API_KEY

# Lab 1, 2, 3 import
from agents.lab1_financial_analyst import FinancialAnalyst
from agents.lab2_portfolio_architect import PortfolioArchitect
from agents.lab3_risk_manager import RiskManager


class ReportGenerator:
    """최종 투자 보고서 생성 에이전트"""
    def __init__(self):
        self.model = AnthropicModel(
            model_id=MODELS["report_generator"]["model"],
            api_key=ANTHROPIC_API_KEY,
            temperature=MODELS["report_generator"]["temperature"],
            max_tokens=MODELS["report_generator"]["max_tokens"]
        )
        
        self.agent = Agent(
            name="report_generator",
            model=self.model,
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        return """당신은 전문적인 재테크 어드바이저입니다. 주어진 정보를 바탕으로 투자 포트폴리오 분석 보고서를 작성해야 합니다.

위의 모든 정보를 종합적으로 분석하여 다음 형식을 엄격히 준수하여 분석 보고서를 작성해 주세요.

### 투자 포트폴리오 분석 보고서
#### 1. 고객 프로필 분석
- 이름: [고객명]
- 주소: [주소]
- 연락처: [연락처]
- [사용자 정보]
#### 2. 기본 포트폴리오 구성
##### 자산 배분
- [ETF 티커] ([ETF 설명]): [배분 비율]%
##### 배분 전략 근거
- [배분 전략에 대한 설명]
#### 3. 시나리오별 대응 전략
##### 시나리오: [시나리오 1]
조정된 자산 배분:
- [ETF 티커]: [새로운 비율]% ([변화량])
대응 전략:
- [대응 전략]
#### 4. 주의사항 및 권고사항
- [주의사항 및 권고사항]
#### 5. 결론
[포트폴리오 전략에 대한 종합적인 결론 및 권고사항]

작성 시 다음 사항을 고려하세요:
1. 투자의 위험성을 명확히 언급하세요.
2. 고객의 특정 상황에 맞는 맞춤형 조언을 제공하세요.
3. 보고서 끝에 간단한 법적 면책 조항을 포함하세요."""
    
    def generate_report(self, user_input: Dict[str, Any], financial_analysis: Dict[str, Any], 
                       portfolio_result: Dict[str, Any], risk_analysis: Dict[str, Any]) -> str:
        """최종 투자 보고서 생성"""
        try:
            # 모든 정보를 종합하여 프롬프트 구성
            prompt = f"""다음 정보를 바탕으로 투자 포트폴리오 분석 보고서를 작성해주세요:

사용자 정보:
{json.dumps(user_input, ensure_ascii=False, indent=2)}

재무 분석 결과:
{json.dumps(financial_analysis, ensure_ascii=False, indent=2)}

제안된 포트폴리오 구성:
{json.dumps(portfolio_result, ensure_ascii=False, indent=2)}

포트폴리오 조정 가이드:
{json.dumps(risk_analysis, ensure_ascii=False, indent=2)}

위의 모든 정보를 종합하여 전문적인 투자 보고서를 작성해주세요."""
            
            result = self.agent(prompt)
            return str(result)
            
        except Exception as e:
            return f"보고서 생성 중 오류가 발생했습니다: {str(e)}"


class InvestmentAdvisor:
    """투자 어드바이저 메인 클래스 (Multi-Agent Graph 패턴)"""
    
    def __init__(self):
        # 각 Lab의 에이전트 초기화
        self.financial_analyst = FinancialAnalyst()
        self.portfolio_architect = PortfolioArchitect()
        self.risk_manager = RiskManager()
        self.report_generator = ReportGenerator()
        
        # Graph 구성
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Multi-Agent Graph 구성"""
        builder = GraphBuilder()
        
        # 각 단계를 노드로 추가 (실제로는 함수를 래핑한 에이전트로 구성)
        # 현재 Strands Agent에서는 함수를 직접 노드로 사용할 수 없으므로
        # 각 단계를 순차적으로 실행하는 방식으로 구현
        return None  # Graph 패턴은 추후 구현
    
    def _reflection_success_condition(self, state) -> bool:
        """Reflection 성공 조건 확인"""
        try:
            result = state.results.get("financial_analysis")
            if result and hasattr(result, 'result'):
                return result.result.get('is_valid', False)
            return False
        except:
            return False
    
    def process_investment_request(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        투자 요청 전체 처리 (Multi-Agent 패턴)
        현재는 순차 실행으로 구현, 추후 Graph 패턴으로 개선 예정
        """
        try:
            # Step 1: 재무 분석 (Reflection 패턴)
            print("Step 1: 재무 분석 수행 중...")
            financial_result = self.financial_analyst.analyze(user_input)
            
            # Reflection 검증 실패 시 종료
            if not financial_result.get('is_valid', False):
                return {
                    "status": "validation_failed",
                    "message": "재무 분석 검증에 실패했습니다.",
                    "financial_analysis": financial_result,
                    "error": financial_result.get('reflection_result', '')
                }
            
            # Step 2: 포트폴리오 설계 (Tool Use 패턴)
            print("Step 2: 포트폴리오 설계 수행 중...")
            portfolio_result = self.portfolio_architect.design_portfolio(
                financial_result['analysis']
            )
            
            if portfolio_result['status'] != 'success':
                return {
                    "status": "portfolio_error",
                    "message": "포트폴리오 설계에 실패했습니다.",
                    "financial_analysis": financial_result,
                    "portfolio_result": portfolio_result,
                    "error": portfolio_result.get('error', '')
                }
            
            # Step 3: 리스크 분석 (Planning 패턴)
            print("Step 3: 리스크 분석 수행 중...")
            risk_result = self.risk_manager.analyze_risk(portfolio_result)
            
            if risk_result['status'] != 'success':
                return {
                    "status": "risk_analysis_error",
                    "message": "리스크 분석에 실패했습니다.",
                    "financial_analysis": financial_result,
                    "portfolio_result": portfolio_result,
                    "risk_result": risk_result,
                    "error": risk_result.get('error', '')
                }
            
            # Step 4: 최종 보고서 생성
            print("Step 4: 최종 보고서 생성 중...")
            final_report = self.report_generator.generate_report(
                user_input,
                financial_result['analysis'],
                portfolio_result['portfolio'],
                risk_result['risk_analysis']
            )
            
            return {
                "status": "success",
                "message": "투자 분석이 성공적으로 완료되었습니다.",
                "financial_analysis": financial_result,
                "portfolio_result": portfolio_result,
                "risk_result": risk_result,
                "final_report": final_report
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"투자 분석 중 오류가 발생했습니다: {str(e)}",
                "error": str(e)
            }


# 테스트용 함수
def test_investment_advisor():
    """테스트 함수"""
    advisor = InvestmentAdvisor()
    
    test_input = {
        "total_investable_amount": 50000000,
        "age": 35,
        "stock_investment_experience_years": 10,
        "target_amount": 70000000
    }
    
    result = advisor.process_investment_request(test_input)
    print("=== Lab 4: Investment Advisor Result ===")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    
    if result['status'] == 'success':
        print("\n=== Final Report ===")
        print(result['final_report'])
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    return result


if __name__ == "__main__":
    test_investment_advisor()