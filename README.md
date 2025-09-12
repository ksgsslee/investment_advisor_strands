# 🤖 AI 투자 어드바이저

**AWS Bedrock AgentCore**를 활용한 Multi-Agent 투자 자문 시스템

## 🎯 시스템 개요

개인 맞춤형 투자 포트폴리오를 제안하는 4개의 전문 AI 에이전트가 협업하는 엔터프라이즈급 투자 자문 시스템입니다.

## 🏗️ 전체 시스템 아키텍처

![전체 시스템 아키텍처](static/investment_advisor.png)

### 📋 전체 워크플로우

```
사용자 입력 → Financial Analyst → Portfolio Architect → Risk Manager → Investment Advisor → 최종 보고서
```

1. **사용자가 투자 정보 입력** (나이, 투자금액, 목표금액, 경험 등)
2. **Financial Analyst**가 재무 상황 분석 및 위험 성향 평가
3. **Portfolio Architect**가 실시간 ETF 데이터로 포트폴리오 설계
4. **Risk Manager**가 뉴스/시장 데이터로 리스크 시나리오 분석
5. **Investment Advisor**가 모든 결과를 통합하여 최종 투자 가이드 생성

## 🏗️ 에이전트별 상세 구조

### Lab 1: Financial Analyst
**역할**: 개인 재무 상황 분석 및 위험 성향 평가

```mermaid
graph LR
    INPUT[👤 사용자 입력<br/>나이, 투자경험<br/>투자금액, 목표금액] --> RUNTIME[🤖 Financial Analyst<br/>AgentCore Runtime]
    RUNTIME --> CALC[🧮 Calculator 도구<br/>수익률 계산]
    CALC --> RUNTIME
    RUNTIME --> OUTPUT[📊 출력<br/>위험성향, 목표수익률<br/>추천 투자섹터]
    
    style RUNTIME fill:#e1f5fe
    style CALC fill:#f0f4c3
```

**구조**:
- **AgentCore Runtime**: 서버리스 에이전트 호스팅
- **도구**: Calculator (정확한 수익률 계산)
- **AI 모델**: OpenAI GPT-OSS 120B

**처리 과정**:
1. 사용자 입력 데이터 분석 (나이, 투자경험, 투자금액, 목표금액)
2. Calculator 도구로 필요 연간 수익률 계산: `((목표금액/투자금액)-1)*100`
3. 나이와 경험을 고려한 위험 성향 평가 (보수적/중립적/공격적)
4. 개인 성향에 맞는 투자 섹터 추천

**출력**:
```json
{
  "risk_profile": "공격적",
  "required_annual_return_rate": 40.0,
  "key_sectors": ["성장주", "기술주", "글로벌 주식"],
  "summary": "40% 목표 수익률 달성을 위한 공격적 투자 전략 필요"
}
```

### Lab 2: Portfolio Architect
**역할**: 실시간 ETF 데이터 기반 최적 포트폴리오 설계

```mermaid
graph LR
    INPUT[📊 재무분석 결과<br/>위험성향, 목표수익률<br/>추천 섹터] --> RUNTIME[🤖 Portfolio Architect<br/>AgentCore Runtime]
    RUNTIME --> AUTH[🔐 Cognito JWT<br/>인증]
    AUTH --> MCP[🔧 MCP Server Runtime<br/>yfinance 연동]
    MCP --> YFINANCE[📊 yfinance API<br/>실시간 ETF 데이터]
    YFINANCE --> MCP
    MCP --> RUNTIME
    RUNTIME --> OUTPUT[📈 출력<br/>포트폴리오 배분<br/>성과 평가]
    
    style RUNTIME fill:#f3e5f5
    style MCP fill:#e8f5e8
```

**구조**:
- **AgentCore Runtime**: 메인 포트폴리오 설계 에이전트
- **MCP Server Runtime**: yfinance API 연동 (별도 Runtime으로 배포)
- **도구**: `analyze_etf_performance`, `calculate_correlation`
- **인증**: Cognito JWT OAuth2 (Runtime 간 직접 통신)

**처리 과정**:
1. Financial Analyst 결과를 바탕으로 5개 후보 ETF 선정
2. 각 ETF에 대해 몬테카를로 시뮬레이션 (1000회) 실행
3. ETF 간 상관관계 매트릭스 계산 (분산투자 효과 측정)
4. 수익률과 분산투자 효과를 고려하여 최적 3개 ETF 선정
5. 투자 비중 결정 및 포트폴리오 평가 (수익성/리스크관리/분산투자 점수)

**출력**:
```json
{
  "portfolio_allocation": {"QQQ": 50, "SPY": 30, "GLD": 20},
  "reason": "기술주 중심 성장 전략...",
  "portfolio_scores": {
    "profitability": {"score": 8, "reason": "목표 수익률 달성 가능성 높음"},
    "risk_management": {"score": 7, "reason": "적정 변동성 수준"},
    "diversification": {"score": 9, "reason": "낮은 상관관계로 우수한 분산투자"}
  }
}
```

### Lab 3: Risk Manager
**역할**: 뉴스 및 거시경제 데이터 기반 리스크 시나리오 분석

```mermaid
graph LR
    INPUT[📈 포트폴리오 결과<br/>ETF 배분<br/>성과 평가] --> RUNTIME[🤖 Risk Manager<br/>AgentCore Runtime]
    RUNTIME --> GATEWAY[🌉 AgentCore Gateway<br/>Lambda → MCP 변환]
    GATEWAY --> AUTH[🔐 Cognito JWT<br/>인증]
    AUTH --> LAMBDA[⚡ Lambda 함수<br/>데이터 조회 x3]
    LAMBDA --> LAYER[📦 Lambda Layer<br/>yfinance 라이브러리]
    LAYER --> YFINANCE[📊 yfinance API<br/>뉴스/시장/지정학적 데이터]
    YFINANCE --> LAYER
    LAYER --> LAMBDA
    LAMBDA --> GATEWAY
    GATEWAY --> RUNTIME
    RUNTIME --> OUTPUT[⚠️ 출력<br/>2개 리스크 시나리오<br/>포트폴리오 조정 전략]
    
    style RUNTIME fill:#e8f5e8
    style GATEWAY fill:#fff3e0
    style LAMBDA fill:#fce4ec
```

**구조**:
- **AgentCore Gateway**: Lambda 함수를 MCP 도구로 노출
- **Lambda Layer**: yfinance 라이브러리 패키징
- **Lambda 함수**: 뉴스/시장/지정학적 데이터 조회
- **도구**: `get_product_news`, `get_market_data`, `get_geopolitical_indicators`

**처리 과정**:
1. 포트폴리오 ETF별 최신 뉴스 5개 수집 및 분석
2. 주요 거시경제 지표 7개 실시간 조회 (금리, 달러지수, VIX, 원유, 금, S&P500)
3. 지역별 ETF 5개 조회 (중국, 신흥국, 유럽, 일본, 한국)
4. 3가지 데이터를 종합하여 2개 핵심 경제 시나리오 도출
5. 각 시나리오별 포트폴리오 조정 전략 수립

**출력**:
```json
{
  "scenario1": {
    "name": "테크 주도 경기 회복",
    "probability": "35%",
    "allocation_management": {"QQQ": 70, "SPY": 25, "GLD": 5},
    "reason": "기술 섹터 성장에 더 많이 노출하여 수익 극대화"
  },
  "scenario2": {
    "name": "인플레이션 지속과 경기 둔화", 
    "probability": "25%",
    "allocation_management": {"QQQ": 40, "SPY": 40, "GLD": 20},
    "reason": "안전자산 비중 확대로 리스크 헤지 강화"
  }
}
```

### Lab 4: Investment Advisor
**역할**: 3개 에이전트 결과 통합 및 장기 메모리 관리

```mermaid
graph TB
    INPUT[👤 사용자 입력<br/>투자 정보] --> RUNTIME[🤖 Investment Advisor<br/>AgentCore Runtime]
    RUNTIME --> LANGGRAPH[📊 LangGraph 워크플로우<br/>순차 실행 관리]
    
    LANGGRAPH --> FA[💰 Financial Analyst<br/>Runtime 호출]
    FA --> LANGGRAPH
    LANGGRAPH --> PA[📈 Portfolio Architect<br/>Runtime 호출]
    PA --> LANGGRAPH
    LANGGRAPH --> RM[⚠️ Risk Manager<br/>Runtime 호출]
    RM --> LANGGRAPH
    
    LANGGRAPH --> MEMORY[🧠 AgentCore Memory<br/>SUMMARY 전략]
    MEMORY --> STORAGE[💾 장기 보존<br/>상담 히스토리 자동 요약]
    
    LANGGRAPH --> OUTPUT[📋 최종 출력<br/>종합 투자 가이드<br/>실시간 스트리밍]
    
    style RUNTIME fill:#fff3e0
    style LANGGRAPH fill:#e1f5fe
    style MEMORY fill:#fce4ec
```

**구조**:
- **LangGraph**: 3개 에이전트 순차 실행 워크플로우
- **AgentCore Memory**: SUMMARY 전략으로 상담 히스토리 자동 요약
- **에이전트 호출**: 다른 3개 에이전트의 Runtime을 직접 호출

**처리 과정**:
1. **LangGraph 워크플로우 시작**: 사용자 입력으로 상태 초기화
2. **순차 에이전트 실행**:
   - `financial_node` → Financial Analyst Runtime 호출
   - `portfolio_node` → Portfolio Architect Runtime 호출  
   - `risk_node` → Risk Manager Runtime 호출
3. **실시간 스트리밍**: 각 에이전트의 사고 과정과 도구 사용을 실시간 표시
4. **메모리 저장**: 각 에이전트 결과를 세션별 대화 이벤트로 저장
5. **자동 요약**: SUMMARY 전략이 전체 상담 세션을 자동 요약하여 장기 보존

**메모리 구조**:
- **Short-term**: 각 에이전트 결과를 세션별 대화로 저장 (7일)
- **Long-term**: SUMMARY 전략이 전체 세션을 자동 요약 (영구 보존)
- **네임스페이스**: `investment/session/{sessionId}` 구조

## � 기술 적 구현 세부사항

### AgentCore 서비스 활용

**1. Runtime (Agent) - 에이전트 호스팅**
- 각 AI 에이전트를 독립적인 서버리스 함수로 배포
- 자동 스케일링 및 고가용성 보장
- ECR 컨테이너 이미지 기반 배포

**2. Runtime (MCP Server) - 데이터 서버 호스팅**
- yfinance 기반 ETF 데이터 조회 서버를 서버리스로 배포
- MCP 프로토콜로 AI 도구화
- 실시간 금융 데이터 제공

**3. Gateway - Lambda 함수를 MCP 변환**
- Lambda 함수를 AI가 사용할 수 있는 MCP 도구로 변환 (Risk Manager에서 사용)
- Cognito JWT 인증으로 보안 강화
- 복잡한 Lambda 인프라를 간단한 AI 도구로 추상화

**4. Memory - 장기 메모리 및 개인화**
- SUMMARY 전략으로 상담 세션 자동 요약
- 사용자별 투자 히스토리 장기 보존
- 개인화된 투자 서비스 제공 기반

**5. Observability - 모니터링 및 추적**
- 각 에이전트의 성능 및 사용량 모니터링
- 실시간 로그 및 메트릭 수집
- 시스템 최적화를 위한 인사이트 제공

### 데이터 흐름

```
사용자 입력
    ↓
Investment Advisor (LangGraph 오케스트레이션)
    ↓
Financial Analyst (Runtime + OpenAI GPT-OSS 120B)
    ↓ (위험성향, 목표수익률)
Portfolio Architect (Runtime + MCP Server + Claude 4.0 Sonnet)
    ↓ (포트폴리오 배분)
Risk Manager (Runtime + Gateway + Claude 3.7 Sonnet)
    ↓ (리스크 시나리오)
Investment Advisor (Memory 저장 + 최종 통합)
    ↓
최종 투자 가이드 + 자동 요약 저장
```

## 🚀 빠른 시작

### 1. 환경 설정
```bash
git clone <repository-url>
cd investment_advisor_strands
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
aws configure
```

### 2. 전체 배포 (권장)
```bash
python deploy_all.py
```

### 3. 웹 앱 실행
```bash
cd investment_advisor && streamlit run app.py
```
브라우저에서 `http://localhost:8501` 접속

### 4. 전체 정리
```bash
python cleanup_all.py
```

## 🎯 사용 시나리오

### 시나리오 1: 전체 시스템 체험 (권장)
1. `python deploy_all.py` - 전체 시스템 배포
2. `cd investment_advisor && streamlit run app.py` - 통합 웹앱 실행
3. 투자 정보 입력 후 4개 에이전트의 협업 과정 실시간 확인
4. 상담 히스토리에서 자동 요약된 과거 상담 기록 확인

### 시나리오 2: 개별 에이전트 학습
1. `cd financial_analyst && python deploy.py && streamlit run app.py`
2. 재무 분석 과정과 Calculator 도구 사용 확인
3. `cd ../portfolio_architect` - 포트폴리오 설계 과정 학습
4. `cd ../risk_manager` - 리스크 분석 과정 학습

### 시나리오 3: 개발 및 커스터마이징
1. 각 에이전트 폴더의 `README.md` 참조하여 상세 구조 파악
2. 개별 배포 및 테스트로 기능 확인 (`deployment_info.json` 파일로 배포 상태 확인)
3. 코드 수정 후 개별 재배포 (각 폴더의 `deploy.py` 실행)
4. 통합 웹앱에서 전체 워크플로우 테스트
5. `shared/` 폴더의 공통 유틸리티 함수 활용하여 새로운 에이전트 개발

## 📊 실제 사용 예시

### 입력 예시
```
투자 가능 금액: 5천만원 (0.5억)
1년 후 목표 금액: 7천만원 (0.7억)  
나이: 35세
투자 경험: 10년
투자 목적: 단기 수익 추구
관심 분야: 성장주, 기술주
```

### 처리 과정 (실시간 스트리밍으로 확인 가능)

**1단계: Financial Analyst**
- Calculator 도구 실행: `((70000000/50000000)-1)*100 = 40%`
- 위험 성향 평가: "35세, 10년 경험 → 공격적"
- 추천 섹터: ["성장주", "기술주", "글로벌 주식"]

**2단계: Portfolio Architect**  
- 5개 후보 ETF 선정: QQQ, SPY, VTI, ARKK, GLD
- 각 ETF 몬테카를로 시뮬레이션 (1000회)
- 상관관계 분석 후 최적 3개 선정: QQQ(50%), SPY(30%), GLD(20%)

**3단계: Risk Manager**
- QQQ, SPY, GLD 뉴스 분석
- 거시경제 지표 확인 (금리, VIX, 달러지수 등)
- 2개 시나리오 도출: "테크 회복(35%)" vs "경기 둔화(25%)"

**4단계: Investment Advisor**
- 3개 결과 통합하여 최종 투자 가이드 생성
- AgentCore Memory에 전체 상담 세션 자동 요약 저장

### 최종 결과
- **포트폴리오**: QQQ 50%, SPY 30%, GLD 20%
- **예상 수익률**: 연 25-45% (시나리오별)
- **리스크 대응**: 경기 둔화 시 GLD 비중 확대 권장
- **상담 기록**: 자동으로 요약되어 장기 보존

## 🔧 기술 스택 및 아키텍처

### 핵심 기술
- **AI Framework**: Strands Agents SDK + LangGraph
- **Infrastructure**: AWS Bedrock AgentCore (Runtime, Gateway, Memory, Observability)
- **LLM**: 
  - Financial Analyst: OpenAI GPT-OSS 120B
  - Portfolio Architect: Claude 4.0 Sonnet (global.anthropic.claude-sonnet-4-20250514-v1:0)
  - Risk Manager: Claude 3.7 Sonnet (us.anthropic.claude-3-7-sonnet-20250219-v1:0)
  - Investment Advisor: LangGraph 오케스트레이션 (LLM 없음, 다른 에이전트 호출)
- **Data Sources**: yfinance (실시간 ETF/뉴스/시장 데이터)
- **Authentication**: Cognito JWT OAuth2
- **UI**: Streamlit (실시간 스트리밍 지원)

### 배포 구조 다이어그램

```mermaid
graph LR
    subgraph "AWS 클라우드 리소스"
        subgraph "AgentCore 서비스"
            RT1[📦 Financial Analyst Runtime]
            RT2[📦 Portfolio Architect Runtime]
            RT3[📦 Risk Manager Runtime]
            RT4[📦 Investment Advisor Runtime]
            MCP[🔧 MCP Server Runtime]
            MEM[🧠 AgentCore Memory]
            GW[🌉 Gateway (Risk Manager용)]
        end
        
        subgraph "지원 서비스"
            LAM[⚡ Lambda 함수 x3]
            LAY[📦 Lambda Layer]
            COG[🔐 Cognito User Pool x2]
            ECR[📦 ECR Repository x5]
        end
    end
    
    RT1 --> ECR
    RT2 --> COG
    RT3 --> GW
    RT4 --> MEM
    COG --> MCP
    GW --> COG
    GW --> LAM
    LAM --> LAY
    MCP --> ECR
    
    style RT1 fill:#e1f5fe
    style RT2 fill:#f3e5f5
    style RT3 fill:#e8f5e8
    style RT4 fill:#fff3e0
    style MEM fill:#fce4ec
```

**총 배포 리소스**: 
- 🏗️ **AgentCore**: Runtime 5개 (Agent 4개 + MCP Server 1개) + Gateway 1개 + Memory 1개
- ⚡ **Lambda**: 함수 3개 + Layer 1개
- 🔐 **인증**: Cognito User Pool 2개
- 📦 **컨테이너**: ECR Repository 5개

### 보안 및 인증
- **Cognito JWT**: MCP Gateway 접근 제어
- **IAM 역할**: 각 서비스별 최소 권한 원칙
- **VPC**: 필요시 네트워크 격리 (선택사항)
- **암호화**: 전송 중/저장 중 데이터 암호화

## 📁 프로젝트 구조 및 개별 테스트

```
investment_advisor_strands/
├── 📂 financial_analyst/           # Lab 1: 재무 분석 (AgentCore Runtime)
│   ├── 📄 README.md               # 상세 설명 및 사용법
│   ├── 🚀 deploy.py               # 개별 배포
│   ├── 🌐 app.py                  # Streamlit 개별 테스트
│   └── 🤖 financial_analyst.py    # 메인 에이전트
│
├── 📂 portfolio_architect/         # Lab 2: 포트폴리오 설계 (AgentCore Runtime + MCP Server)
│   ├── 📄 README.md               # 상세 설명 및 사용법
│   ├── 🚀 deploy.py               # 개별 배포
│   ├── 🌐 app.py                  # Streamlit 개별 테스트
│   ├── 🤖 portfolio_architect.py  # 메인 에이전트
│   └── 📂 mcp_server/             # MCP Server (별도 Runtime)
│       ├── 🚀 deploy_mcp.py       # MCP Server 배포
│       └── 🔧 server.py           # ETF 데이터 조회 서버
│
├── 📂 risk_manager/               # Lab 3: 리스크 관리 (AgentCore Gateway)
│   ├── 📄 README.md               # 상세 설명 및 사용법
│   ├── 🚀 deploy.py               # 개별 배포 (4단계 통합)
│   ├── 🌐 app.py                  # Streamlit 개별 테스트
│   ├── 🤖 risk_manager.py         # 메인 에이전트
│   ├── 📂 lambda_layer/           # Lambda Layer (yfinance)
│   ├── 📂 lambda/                 # Lambda 함수 (데이터 조회)
│   └── 📂 gateway/                # MCP Gateway (Lambda → MCP 도구)
│
├── 📂 investment_advisor/         # Lab 4: 통합 자문 (AgentCore Memory)
│   ├── 📄 README.md               # 상세 설명 및 사용법
│   ├── 🚀 deploy.py               # 개별 배포
│   ├── 🌐 app.py                  # Streamlit 통합 웹앱 (메인)
│   ├── 🤖 investment_advisor.py   # LangGraph 기반 통합 에이전트
│   
│   └── 📂 agentcore_memory/       # AgentCore Memory
│       └── 🚀 deploy_agentcore_memory.py # Memory 배포
│
├── 📂 shared/                     # 공통 유틸리티
│   ├── runtime_utils.py           # Runtime 관련 공통 함수
│   ├── gateway_utils.py           # Gateway 관련 공통 함수
│   └── cognito_utils.py           # 인증 관련 공통 함수
│
├── 🚀 deploy_all.py               # 🎯 전체 시스템 한번에 배포
├── 🧹 cleanup_all.py              # 🎯 전체 시스템 한번에 정리
├── 📋 requirements.txt            # Python 의존성
└── 📄 README.md                   # 이 파일
```

### 🧪 개별 에이전트 테스트 방법

각 에이전트는 독립적으로 배포하고 테스트할 수 있습니다:

#### Lab 1: Financial Analyst
```bash
cd financial_analyst
python deploy.py                    # 배포
streamlit run app.py               # 개별 테스트 웹앱
```
- **기능**: 투자자 정보 입력 → 위험 성향 평가 → 목표 수익률 계산
- **도구**: Calculator로 정확한 수익률 계산 과정 확인

#### Lab 2: Portfolio Architect  
```bash
cd portfolio_architect
cd mcp_server && python deploy_mcp.py && cd ..  # MCP Server 먼저 배포
python deploy.py                    # 메인 에이전트 배포
streamlit run app.py               # 개별 테스트 웹앱
```
- **기능**: 재무 분석 결과 입력 → ETF 분석 → 포트폴리오 설계
- **구조**: Runtime 간 직접 MCP 통신 (Gateway 없음)
- **도구**: 몬테카를로 시뮬레이션 + 상관관계 분석 과정 실시간 확인

#### Lab 3: Risk Manager
```bash
cd risk_manager
# 4단계 순차 배포 (필수)
cd lambda_layer && python deploy_lambda_layer.py && cd ..
cd lambda && python deploy_lambda.py && cd ..
cd gateway && python deploy_gateway.py && cd ..
python deploy.py                    # Risk Manager Runtime 배포
streamlit run app.py               # 개별 테스트 웹앱
```
- **기능**: 포트폴리오 입력 → 뉴스/시장 데이터 분석 → 리스크 시나리오
- **도구**: 실시간 뉴스, 거시경제 지표, 지정학적 데이터 수집 과정 확인

#### Lab 4: Investment Advisor (통합 시스템)
```bash
cd investment_advisor
cd agentcore_memory && python deploy_agentcore_memory.py && cd ..  # Memory 먼저 배포
python deploy.py                    # 통합 에이전트 배포
streamlit run app.py               # 🎯 메인 통합 웹앱
```
- **기능**: 전체 워크플로우 실행 → 3개 에이전트 순차 호출 → 최종 투자 가이드
- **특징**: 실시간 스트리밍으로 모든 에이전트의 사고 과정 확인 + 상담 히스토리 관리

---

**🎯 AWS Bedrock AgentCore로 구현한 차세대 AI 투자 어드바이저!** 🚀