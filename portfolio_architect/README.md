# Portfolio Architect

실시간 시장 데이터를 분석하여 맞춤형 투자 포트폴리오를 설계하는 AI 에이전트입니다. MCP(Model Context Protocol)를 통해 외부 데이터와 연동하여 데이터 기반 투자 전략을 제공합니다.

## 🎯 핵심 기능

### 맞춤형 포트폴리오 설계
- **개인화 분석**: Financial Analyst 결과를 기반으로 한 맞춤형 설계
- **위험 성향 반영**: 5단계 위험 성향에 따른 자산 배분 최적화
- **목표 수익률 고려**: 필요 수익률 달성을 위한 전략적 포트폴리오 구성

### 실시간 시장 데이터 활용
- **MCP 연동**: Model Context Protocol을 통한 외부 시스템 연결
- **실시간 가격**: 최신 시장 가격 데이터 기반 의사결정
- **다양한 자산**: ETF, 주식, 채권 등 다양한 투자 상품 지원

### 분산 투자 전략
- **3종목 분산**: 리스크 분산을 위한 최적 3종목 선택
- **비율 최적화**: 각 자산별 투자 비율 정밀 계산
- **리밸런싱**: 시장 상황에 따른 포트폴리오 조정 제안

### 투자 전략 및 근거 제시
- **전략 설명**: 포트폴리오 구성 전략의 명확한 설명
- **근거 제시**: 각 투자 결정의 논리적 근거 제공
- **리스크 분석**: 예상 리스크와 수익률 분석

## 🏗️ 아키텍처

### 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Streamlit UI]
        USER[사용자]
    end
    
    subgraph "AWS AgentCore Infrastructure"
        RUNTIME[AgentCore Runtime]
        GATEWAY[MCP Gateway]
        LAYER[Lambda Layer]
    end
    
    subgraph "Authentication"
        COGNITO[Cognito User Pool]
        OAUTH[OAuth2 Client]
    end
    
    subgraph "AI Agent Layer"
        AGENT[Portfolio Architect Agent<br/>Claude 3.5 Sonnet]
    end
    
    subgraph "MCP Tools"
        TOOL1[get_available_products]
        TOOL2[get_product_data]
    end
    
    subgraph "External Data"
        MARKET[Market Data API]
        PRODUCTS[Product Database]
    end
    
    USER --> UI
    UI --> RUNTIME
    RUNTIME --> AGENT
    AGENT --> GATEWAY
    GATEWAY --> COGNITO
    COGNITO --> OAUTH
    GATEWAY --> TOOL1
    GATEWAY --> TOOL2
    TOOL1 --> PRODUCTS
    TOOL2 --> MARKET
    LAYER --> GATEWAY
```

### MCP 연동 아키텍처

```mermaid
sequenceDiagram
    participant A as Agent
    participant G as MCP Gateway
    participant T as MCP Tools
    participant M as Market Data
    
    A->>G: OAuth2 인증
    G->>A: Access Token
    A->>G: get_available_products 호출
    G->>T: 도구 실행
    T->>M: 상품 목록 조회
    M->>T: 상품 데이터 반환
    T->>G: 결과 반환
    G->>A: 상품 목록 제공
    
    loop 선택된 상품들
        A->>G: get_product_data 호출
        G->>T: 도구 실행
        T->>M: 가격 데이터 조회
        M->>T: 실시간 가격 반환
        T->>G: 결과 반환
        G->>A: 가격 데이터 제공
    end
    
    A->>A: 포트폴리오 최적화
```

### Agentic AI 패턴: Tool Use Pattern

```mermaid
flowchart TD
    INPUT[재무 분석 결과 입력]
    ANALYZE[위험 성향 분석]
    TOOLS[MCP 도구 호출]
    PRODUCTS[상품 목록 조회]
    SELECT[3개 상품 선택]
    PRICES[실시간 가격 조회]
    OPTIMIZE[포트폴리오 최적화]
    OUTPUT[포트폴리오 결과]
    
    INPUT --> ANALYZE
    ANALYZE --> TOOLS
    TOOLS --> PRODUCTS
    PRODUCTS --> SELECT
    SELECT --> PRICES
    PRICES --> OPTIMIZE
    OPTIMIZE --> OUTPUT
```

### Strands Agent 구성

#### Portfolio Architect Agent
- **역할**: 포트폴리오 설계 및 MCP 도구 활용
- **모델**: Claude 3.5 Sonnet
- **온도**: 0.3 (창의적 포트폴리오 설계를 위한 적정 수준)
- **도구**: MCP 클라이언트를 통한 외부 데이터 접근

#### MCP 도구 체인
- **도구 발견**: 런타임 시 사용 가능한 도구 자동 탐지
- **동적 호출**: 필요에 따른 도구 동적 실행
- **결과 통합**: 여러 도구 결과의 종합적 분석

### AgentCore 구성요소

#### Runtime
- **실행 환경**: AWS Lambda 기반 서버리스
- **환경변수**: MCP Gateway 연결 정보 자동 주입
- **확장성**: 동시 다중 요청 처리 가능

#### Gateway
- **프로토콜**: MCP (Model Context Protocol)
- **인증**: OAuth2 Client Credentials Flow
- **보안**: Cognito User Pool 기반 인증
- **API**: RESTful API를 통한 도구 노출

#### Lambda Layer
- **의존성**: MCP 클라이언트 라이브러리
- **재사용**: 여러 Lambda 함수에서 공유
- **버전 관리**: 의존성 버전 통합 관리

## 🚀 배포 및 실행

### 사전 요구사항
- AWS CLI 설정 및 인증
- Docker 설치 (Gateway 및 Runtime 빌드용)
- Python 3.9+ 환경
- Bedrock 모델 접근 권한
- 충분한 AWS 권한 (Lambda, API Gateway, Cognito, ECR 등)

### 1. Gateway 배포 (필수 선행)
```bash
cd gateway

# Gateway 인프라 배포 (10-15분 소요)
python deploy_gateway.py

# 배포 결과 확인
cat gateway_deployment_info.json
```

**Gateway 구성요소:**
- API Gateway: MCP 엔드포인트 노출
- Cognito User Pool: OAuth2 인증
- Lambda 함수: MCP 도구 실행
- ECR Repository: 컨테이너 이미지 저장

### 2. Lambda Layer 배포 (필수)
```bash
cd lambda_layer

# MCP 클라이언트 라이브러리 Layer 생성
python deploy_layer.py

# Layer 정보 확인
cat layer_deployment_info.json
```

**Layer 구성요소:**
- MCP 클라이언트 라이브러리
- HTTP 전송 프로토콜 구현
- 인증 헬퍼 함수

### 3. Runtime 배포
```bash
# Gateway 정보 자동 로드하여 Runtime 배포
python deploy.py

# 배포 상태 확인
cat deployment_info.json
```

**Runtime 구성요소:**
- Portfolio Architect Agent
- MCP 클라이언트 통합
- 환경변수 자동 설정

### 4. Streamlit 앱 실행
```bash
# 의존성 설치
pip install streamlit boto3

# 웹 애플리케이션 실행
streamlit run app.py
```

### 5. 통합 테스트
- Financial Analyst에서 재무 분석 수행
- 분석 결과를 Portfolio Architect에 입력
- 실시간 포트폴리오 설계 과정 확인
- MCP 도구 호출 및 결과 검증

## 📊 상세 입력/출력 명세

### 입력 데이터 구조 (Financial Analyst 결과)
```json
{
  "risk_profile": "중립적",
  "risk_profile_reason": "35세 중년층으로 10년의 투자 경험을 보유하여 적정 수준의 위험 감수 가능",
  "required_annual_return_rate": 40.0,
  "return_rate_reason": "1년 내 40% 수익률 달성을 위해 공격적 투자 전략 필요"
}
```

### MCP 도구 호출 과정
1. **get_available_products 호출**
   ```json
   {
     "products": ["QQQ", "SPY", "VTI", "ARKK", "IWM", "EFA", "BND", "GLD"]
   }
   ```

2. **3개 상품 선택 (AI 판단)**
   - 위험 성향과 목표 수익률 고려
   - 분산 투자 원칙 적용
   - 상관관계 분석

3. **get_product_data 동시 호출**
   ```json
   {
     "QQQ": {"price": 380.50, "change": "+1.2%", "volume": "45M"},
     "SPY": {"price": 445.20, "change": "+0.8%", "volume": "78M"},
     "VTI": {"price": 220.15, "change": "+0.9%", "volume": "32M"}
   }
   ```

### 출력 데이터 구조
```json
{
  "portfolio_allocation": {
    "QQQ": 50,    // 나스닥 기술주 ETF - 50%
    "SPY": 30,    // S&P 500 ETF - 30%
    "VTI": 20     // 전체 주식시장 ETF - 20%
  },
  "strategy": "공격적 성장 전략: 높은 목표 수익률(40%) 달성을 위해 기술주 중심의 성장주 포트폴리오 구성. QQQ를 주축으로 하여 기술주 상승장 수혜를 극대화하고, SPY와 VTI로 안정성 보완",
  "reason": "QQQ(나스닥 기술주) 50% - 높은 성장 잠재력으로 목표 수익률 달성 기여, SPY(S&P 500) 30% - 대형주 안정성으로 리스크 완충, VTI(전체 시장) 20% - 중소형주 포함으로 추가 분산 효과"
}
```

## 🔧 고급 설정 및 커스터마이징

### 모델 및 에이전트 설정
```python
# portfolio_architect.py에서 수정 가능

class Config:
    MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    TEMPERATURE = 0.3      # 창의적 포트폴리오 설계를 위한 적정 수준
    MAX_TOKENS = 3000      # 상세한 분석을 위한 충분한 토큰
```

### MCP Gateway 설정
```python
# gateway/deploy_gateway.py에서 수정 가능

# 지원 투자 상품 확장
SUPPORTED_PRODUCTS = [
    "QQQ", "SPY", "VTI", "ARKK", "IWM",  # 주식 ETF
    "EFA", "EEM", "VWO",                  # 해외 ETF  
    "BND", "TLT", "HYG",                  # 채권 ETF
    "GLD", "SLV", "DBC"                   # 원자재 ETF
]

# API 응답 시간 설정
TIMEOUT_SECONDS = 30
```

### 포트폴리오 최적화 로직
- **위험 성향별 자산 배분**:
  - 매우 보수적: 채권 70%, 주식 30%
  - 보수적: 채권 50%, 주식 50%
  - 중립적: 채권 30%, 주식 70%
  - 공격적: 채권 10%, 주식 90%
  - 매우 공격적: 주식 100%

- **분산 투자 원칙**:
  - 최소 3개 이상 종목
  - 단일 종목 최대 60% 제한
  - 상관관계 고려한 종목 선택

## 🔍 모니터링 및 운영

### 성능 메트릭
- **응답 시간**: 평균 15-30초 (MCP 호출 포함)
- **성공률**: 95%+ (정상 입력 및 네트워크 상태 기준)
- **MCP 호출 성공률**: 98%+
- **비용**: 요청당 약 $0.05-0.15 (Gateway + Runtime)

### 로그 및 모니터링
```bash
# Runtime 로그 확인
aws logs tail /aws/lambda/portfolio-architect-runtime --follow

# Gateway 로그 확인  
aws logs tail /aws/lambda/mcp-gateway --follow

# API Gateway 메트릭 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=mcp-gateway
```

### 문제 해결 가이드

#### 배포 관련 문제
- **Gateway 배포 실패**: IAM 권한, Docker 설치 상태 확인
- **Layer 배포 실패**: Python 환경, 의존성 설치 확인
- **Runtime 배포 실패**: Gateway 선행 배포 여부 확인

#### 실행 시간 문제
- **MCP 연결 실패**: Gateway URL, 인증 정보 확인
- **도구 호출 오류**: 네트워크 연결, API 응답 시간 확인
- **포트폴리오 생성 실패**: 입력 데이터 형식, 모델 응답 확인

#### 성능 최적화
- **응답 시간 개선**: 병렬 도구 호출, 캐싱 활용
- **비용 최적화**: 불필요한 도구 호출 최소화
- **안정성 향상**: 재시도 로직, 오류 처리 강화

## 📁 상세 프로젝트 구조

```
portfolio_architect/
├── gateway/                    # MCP Gateway 구성요소
│   ├── deploy_gateway.py      # Gateway 배포 스크립트
│   ├── gateway_handler.py     # Lambda 핸들러
│   ├── mcp_tools.py          # MCP 도구 구현
│   ├── requirements.txt      # Gateway 의존성
│   ├── Dockerfile           # Gateway 컨테이너
│   └── gateway_deployment_info.json  # 배포 정보
├── lambda_layer/              # Lambda Layer 구성요소
│   ├── deploy_layer.py       # Layer 배포 스크립트
│   ├── requirements.txt      # Layer 의존성
│   └── layer_deployment_info.json    # Layer 정보
├── portfolio_architect.py     # 메인 에이전트 클래스
├── deploy.py                 # Runtime 배포 스크립트
├── app.py                    # Streamlit 웹 애플리케이션
├── requirements.txt          # Runtime 의존성
├── __init__.py              # 패키지 초기화
├── .bedrock_agentcore.yaml  # AgentCore 설정
├── Dockerfile               # Runtime 컨테이너
└── deployment_info.json     # Runtime 배포 정보
```

## 🔗 연관 프로젝트

이 프로젝트는 **Financial Analyst**와 연동하여 완전한 투자 자문 시스템을 구성합니다:

1. **Financial Analyst** → 개인 재무 분석 및 위험 성향 평가
2. **Portfolio Architect** → 분석 결과 기반 포트폴리오 설계

두 시스템을 순차적으로 사용하여 개인 맞춤형 투자 전략을 수립할 수 있습니다.