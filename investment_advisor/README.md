# Investment Advisor

**Multi-Agent + AgentCore Memory 기반 투자 자문 시스템**

3개의 전문 AI 에이전트가 협업하여 종합적인 투자 분석을 제공하고, AgentCore Memory를 통해 상담 히스토리를 자동으로 관리하는 엔터프라이즈급 투자 자문 시스템입니다.

## 🎯 핵심 기능

### Multi-Agent 협업 시스템
- **전문 에이전트 협업**: Financial Analyst → Portfolio Architect → Risk Manager
- **Strands Agents as Tools**: 각 에이전트를 도구로 활용하는 깔끔한 아키텍처
- **실시간 스트리밍**: AI 사고 과정을 실시간으로 시각화

### AgentCore Memory 통합
- **Short-term Memory**: 각 에이전트의 최종 리포트를 상세하게 저장 (7일 보존)
- **Long-term Memory**: 매니지드 SUMMARY 전략이 자동으로 요약 생성 및 영구 보존
- **에이전트별 네임스페이스**: `investment/{actorId}/long_term` 구조로 분리
- **자동 요약 처리**: 수동 요약 없이 AgentCore가 자동으로 장기 보존용 요약 생성

### 종합 투자 분석
- **완전 자동화**: 사용자 입력만으로 전체 투자 자문 프로세스 완료
- **전문적 분석**: 재무 분석 → 포트폴리오 설계 → 리스크 관리의 체계적 접근
- **실행 가능한 결과**: 구체적이고 바로 실행 가능한 투자 가이드 제공

## 🏗️ 시스템 아키텍처

### 간단한 순차 호출 구조
```python
class InvestmentAdvisor:
    async def run_comprehensive_analysis_async(self, user_input, user_id=None):
        # 1단계: Financial Analyst 호출
        financial_result = self.agent_caller.call_financial_analyst(user_input)
        
        # 2단계: Portfolio Architect 호출
        portfolio_result = self.agent_caller.call_portfolio_architect(financial_result)
        
        # 3단계: Risk Manager 호출
        risk_result = self.agent_caller.call_risk_manager(portfolio_result)
        
        # 4단계: 통합 리포트 생성
        final_report = self.report_agent(integrated_data)
        
        # 5단계: Memory에 저장
        session_id = save_to_memory(user_input, integrated_data, final_report, user_id)
        
        return final_report, session_id
```

### 에이전트별 역할
| 순서 | 에이전트 | 패턴 | 역할 | 입력 | 출력 |
|------|---------|------|------|------|------|
| **1단계** | Financial Analyst | Reflection | 재무 분석 및 위험 성향 평가 | 사용자 기본 정보 | 위험 성향, 목표 수익률 |
| **2단계** | Portfolio Architect | Tool Use | 실시간 데이터 기반 포트폴리오 설계 | 재무 분석 결과 | 포트폴리오 배분, 투자 전략 |
| **3단계** | Risk Manager | Planning | 뉴스 기반 리스크 분석 및 시나리오 플래닝 | 포트폴리오 설계 | 2개 시나리오별 조정 전략 |
| **4단계** | Report Generator | - | 통합 리포트 생성 | 모든 에이전트 결과 | 종합 투자 리포트 |
| **5단계** | Memory Storage | - | 상담 히스토리 저장 | 통합 데이터 | 세션 ID |

## 🚀 배포 및 실행

### 사전 요구사항
모든 개별 에이전트가 먼저 배포되어 있어야 합니다:

```bash
# 1. Financial Analyst 배포
cd ../financial_analyst
python deploy.py

# 2. Portfolio Architect 배포  
cd ../portfolio_architect
python deploy.py

# 3. Risk Manager 배포
cd ../risk_manager
python lambda_layer/deploy_lambda_layer.py
python lambda/deploy_lambda.py
python gateway/deploy_gateway.py
python deploy.py
```

### Investment Advisor 배포

```bash
# 1. Investment Advisor 배포
python deploy.py

# 2. 배포 확인
cat deployment_info.json
```

### Streamlit 앱 실행

```bash
# 의존성 설치
pip install streamlit boto3 plotly pandas

# 웹 애플리케이션 실행
streamlit run app.py
```

## 📊 사용 방법

### 1. 새로운 투자 상담
1. **사용자 ID 입력**: 히스토리 저장을 위한 식별자
2. **투자자 정보 입력**: 나이, 투자 경험, 투자 금액, 목표 금액
3. **종합 분석 실행**: Graph 패턴으로 3개 에이전트 순차 실행
4. **통합 리포트 확인**: AI가 생성한 종합 투자 리포트 검토

### 2. 상담 히스토리 조회
1. **사용자 ID 입력**: 조회할 사용자 식별자
2. **히스토리 목록**: 과거 상담 이력을 시간순으로 표시
3. **상세 보기**: 개별 상담의 상세 내용 확인
4. **태그 및 요약**: 빠른 식별을 위한 태그 및 요약 정보

## 📋 입력/출력 명세

### 입력 데이터
```json
{
  "total_investable_amount": 50000000,    // 총 투자 가능 금액 (원)
  "age": 35,                             // 나이
  "stock_investment_experience_years": 10, // 주식 투자 경험 (년)
  "target_amount": 70000000              // 1년 후 목표 금액 (원)
}
```

### 최종 리포트 구조
```json
{
  "report_title": "35세 공격적 투자자 - QQQ 중심 포트폴리오",
  "executive_summary": "고성장 기술주 중심의 공격적 투자 전략으로 40% 목표 수익률 달성을 위한 포트폴리오",
  "client_profile": {
    "risk_tolerance": "공격적",
    "investment_goal": "1년 내 40% 수익률 달성",
    "target_return": "40%"
  },
  "recommended_strategy": {
    "portfolio_allocation": {"QQQ": 60, "SPY": 30, "GLD": 10},
    "investment_rationale": "기술주 중심의 성장 전략",
    "expected_outcome": "높은 변동성 하에서 목표 수익률 달성 가능"
  },
  "risk_management": {
    "key_risks": ["기술주 변동성", "금리 인상 리스크"],
    "scenario_planning": {시나리오별 대응 전략},
    "monitoring_points": ["나스닥 지수", "금리 동향"]
  },
  "action_plan": {
    "immediate_actions": ["QQQ 60% 매수", "SPY 30% 매수", "GLD 10% 매수"],
    "review_schedule": "월 1회",
    "success_metrics": ["포트폴리오 수익률", "변동성 지표"]
  },
  "disclaimer": "투자에는 원금 손실 위험이 있습니다."
}
```

### Memory 저장 데이터

#### Short-term Memory (상세 결과 - 7일 보존)
```json
{
  "agent_type": "financial",
  "timestamp": "2024-08-25T12:00:00Z",
  "input": "투자 상담 요청: {...}",
  "detailed_result": "상세한 재무 분석 결과 전문...",
  "session_id": "session_20240825_120000"
}
```

#### Long-term Memory (매니지드 자동 요약 - 영구 보존)
```
AgentCore SUMMARY 전략이 자동으로 생성:
- 네임스페이스: investment/investment_financial/long_term
- 요약 내용: AI가 자동으로 핵심 내용 추출 및 요약
- 보존 기간: 영구 (전략에 따라 관리)
```

## 🔧 고급 설정

### 에이전트 호출 최적화
각 에이전트는 `streaming_complete` 이벤트에 최종 결과를 포함하여 효율적인 데이터 추출이 가능합니다:

```python
class ExternalAgentCaller:
    def call_financial_analyst(self, user_input):
        """Financial Analyst 호출 - streaming_complete에서 최종 결과 추출"""
        try:
            response = self.agentcore_client.invoke_agent_runtime(
                agentRuntimeArn=self.financial_analyst_arn,
                qualifier="DEFAULT",
                payload=json.dumps({"input_data": user_input})
            )
            
            # 공통 유틸리티로 streaming_complete에서 최종 결과 추출
            result = extract_final_result_from_streaming(response["response"])
            
            if result is None:
                raise Exception("유효한 결과를 받지 못했습니다.")
            
            return result
            
        except Exception as e:
            raise Exception(f"Financial Analyst 호출 실패: {str(e)}")
```

### 공통 JSON 유틸리티 활용
`shared/json_utils.py`에서 제공하는 공통 함수들을 활용합니다:

```python
from json_utils import extract_final_result_from_streaming, extract_json_from_text

# 스트리밍 응답에서 최종 결과 추출
result = extract_final_result_from_streaming(response_stream)

# 텍스트에서 JSON 추출
json_data = extract_json_from_text(text_content)
```

### 리포트 생성 프롬프트 수정
`get_report_prompt()` 함수에서 리포트 형식을 커스터마이징할 수 있습니다.

### 순차 호출 최적화
순차 호출 성능을 위한 최적화 방법:

```python
# 각 단계별 진행 상황 스트리밍
async for event in advisor.run_comprehensive_analysis_async(user_input, user_id):
    if event["type"] == "step_start":
        print(f"시작: {event['message']}")
    elif event["type"] == "step_complete":
        print(f"완료: {event['step']}")
    elif event["type"] == "analysis_complete":
        print("전체 분석 완료!")
```

### Memory 검색 최적화
메모리 조회 방법:

```python
# Short-term: 세션별 상세 결과 조회
short_term_results = memory_client.get_events(
    memory_id=memory_id,
    session_id=session_id  # 동일한 세션 ID 사용
)

# Long-term: 매니지드 SUMMARY 조회
long_term_summaries = memory_client.search(
    memory_id=memory_id,
    query="investment analysis summary",
    namespace="investment/investment_*/long_term"
)
```

## 🔍 모니터링 및 디버깅

### 로그 확인
```bash
# Runtime 로그 확인
aws logs tail /aws/lambda/investment-advisor-runtime --follow

# 각 에이전트별 로그 확인
aws logs tail /aws/lambda/financial-analyst-runtime --follow
aws logs tail /aws/lambda/portfolio-architect-runtime --follow
aws logs tail /aws/lambda/risk-manager-runtime --follow
```

### 성능 메트릭
- **전체 실행 시간**: 평균 60-120초 (순차 호출)
- **호출 오버헤드**: 최소 (직접 호출)
- **Memory 저장 시간**: 평균 2-5초
- **성공률**: 95%+ (모든 에이전트가 정상 배포된 경우)
- **비용**: 요청당 약 $0.15-0.30 (모든 에이전트 + 리포트 생성 + Memory 저장)

### 실행 상태 모니터링
```python
# 각 단계별 상태 확인
async for event in advisor.run_comprehensive_analysis_async(user_input, user_id):
    print(f"Type: {event['type']}")
    print(f"Message: {event.get('message', '')}")
    if event['type'] == 'analysis_complete':
        print(f"Session ID: {event.get('session_id')}")
        print(f"Final Report: {event.get('final_report')}")
```

### 문제 해결
1. **에이전트 호출 실패**: 개별 에이전트 배포 상태 확인
2. **Memory 저장 실패**: IAM 권한 및 Memory 설정 확인
3. **리포트 생성 실패**: 입력 데이터 형식 및 프롬프트 확인

## 📁 프로젝트 구조

```
investment_advisor/
├── investment_advisor.py    # 메인 Graph 기반 에이전트
├── deploy.py               # AgentCore Runtime 배포 스크립트
├── app.py                  # Streamlit 웹 애플리케이션 (히스토리 포함)
├── requirements.txt        # Python 의존성
├── deployment_info.json    # 배포 정보 (자동 생성)
└── README.md              # 이 파일
```

## 🎉 주요 장점

✅ **간단한 순차 호출**: 복잡한 Graph 없이 직관적이고 이해하기 쉬운 구조  
✅ **완전한 자동화**: 사용자 입력만으로 전체 투자 자문 프로세스 완료  
✅ **전문적인 리포트**: AI가 생성하는 은행급 투자 리포트  
✅ **히스토리 관리**: 모든 상담 내용을 체계적으로 저장 및 관리  
✅ **확장 가능**: 새로운 에이전트나 단계 쉽게 추가 가능  
✅ **독립적 운영**: 각 에이전트가 독립적으로 배포되어 유지보수 용이  
✅ **실시간 모니터링**: 각 단계별 진행 상황을 실시간으로 확인  
✅ **디버깅 용이**: 각 단계별 결과를 명확히 추적 가능  

이제 Investment Advisor는 **간단한 순차 호출**과 **AgentCore Memory**를 활용한 직관적이고 안정적인 통합 투자 자문 시스템으로, 개별 에이전트들의 장점을 모두 결합하여 전문적인 투자 서비스를 제공합니다!