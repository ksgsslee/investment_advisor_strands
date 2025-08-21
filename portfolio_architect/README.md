# Portfolio Architect (MCP Server 버전)

실시간 시장 데이터를 분석하여 맞춤형 투자 포트폴리오를 설계하는 AI 에이전트입니다. **Tool Use 패턴**을 활용하여 **MCP Server**를 통해 외부 데이터와 연동하고, **AWS Bedrock AgentCore Runtime** 기반으로 서버리스 환경에서 실행됩니다.

## 🏗️ 새로운 아키텍처 (단순화됨)

### 전체 시스템 구조
```
Portfolio Architect Agent → MCP Server → yfinance → ETF 데이터
                          ↑
                    Cognito JWT Auth
```

### 프로젝트 구조
```
portfolio_architect/
├── mcp/                          # MCP Server 관련 파일들
│   ├── __init__.py              # MCP 패키지 초기화
│   ├── server.py                # ETF 데이터 MCP Server
│   ├── requirements.txt         # MCP Server 의존성
│   ├── deploy.py               # MCP Server 배포 스크립트
│   ├── test_local.py           # 로컬 MCP Server 테스트
│   ├── test_remote.py          # 원격 MCP Server 테스트
│   └── mcp_deployment_info.json # MCP Server 배포 정보 (자동 생성)
├── portfolio_architect.py       # Portfolio Architect Agent
├── deploy.py                    # 전체 시스템 배포 스크립트
├── app.py                      # Streamlit 웹 애플리케이션
├── requirements.txt            # Portfolio Architect 의존성
├── __init__.py                 # 패키지 초기화
├── .bedrock_agentcore.yaml     # AgentCore 설정 (자동 생성)
├── Dockerfile                  # Runtime 컨테이너 (자동 생성)
└── deployment_info.json        # 전체 배포 정보 (자동 생성)
```

## 🚀 배포 및 실행

### 1. 전체 시스템 배포 (원클릭)
```bash
# 모든 컴포넌트를 순차적으로 배포
python deploy.py
```

**배포 과정:**
1. **MCP Server 배포** (`mcp/deploy.py` 호출)
   - Cognito 인증 설정
   - IAM 역할 생성
   - MCP Server Runtime 배포
   - AWS Parameter Store/Secrets Manager에 정보 저장
   - `mcp_deployment_info.json` 파일 생성

2. **Portfolio Architect 배포**
   - MCP Server 배포 정보 로드 (`mcp_deployment_info.json` 참조)
   - IAM 역할 생성
   - Portfolio Architect Runtime 배포
   - 전체 시스템 배포 정보 저장 (`deployment_info.json`)

### 2. MCP Server만 별도 배포 (선택사항)
```bash
cd mcp
python deploy.py
```

### 3. 로컬 MCP Server 테스트 (선택사항)
```bash
# 터미널 1: MCP Server 로컬 실행
cd mcp
python server.py

# 터미널 2: 로컬 테스트
cd mcp
python test_local.py
```

### 4. 원격 MCP Server 테스트
```bash
cd mcp
python test_remote.py
```

### 5. Streamlit 앱 실행
```bash
# 웹 애플리케이션 실행
streamlit run app.py
```

## 🎯 핵심 기능

### 맞춤형 포트폴리오 설계
- **개인화 분석**: Financial Analyst 결과를 기반으로 한 맞춤형 설계
- **위험 성향 반영**: 5단계 위험 성향에 따른 자산 배분 최적화
- **목표 수익률 고려**: 필요 수익률 달성을 위한 전략적 포트폴리오 구성

### 실시간 시장 데이터 활용
- **MCP Server 연동**: Model Context Protocol을 통한 ETF 데이터 조회
- **실시간 가격**: 최신 시장 가격 데이터 기반 의사결정
- **30개 ETF 지원**: 다양한 카테고리의 투자 상품 지원

### 분산 투자 전략
- **3종목 분산**: 리스크 분산을 위한 최적 3종목 선택
- **비율 최적화**: 각 자산별 투자 비율 정밀 계산
- **리밸런싱**: 시장 상황에 따른 포트폴리오 조정 제안

## 🔧 지원하는 ETF 상품 (30개)

### 📈 주요 지수 ETF (5개)
- **SPY**: SPDR S&P 500 ETF
- **QQQ**: Invesco QQQ ETF (나스닥 100)
- **VTI**: Vanguard Total Stock Market ETF
- **VOO**: Vanguard S&P 500 ETF
- **IVV**: iShares Core S&P 500 ETF

### 🌍 국제/신흥국 ETF (5개)
- **VEA**: Vanguard FTSE Developed Markets ETF
- **VWO**: Vanguard FTSE Emerging Markets ETF
- **VXUS**: Vanguard Total International Stock ETF
- **EFA**: iShares MSCI EAFE ETF
- **EEM**: iShares MSCI Emerging Markets ETF

### 💰 채권/안전자산 ETF (5개)
- **BND**: Vanguard Total Bond Market ETF
- **AGG**: iShares Core U.S. Aggregate Bond ETF
- **TLT**: iShares 20+ Year Treasury Bond ETF
- **GLD**: SPDR Gold Shares
- **SLV**: iShares Silver Trust

### 🏢 섹터별 ETF (8개)
- **XLF**: Financial Select Sector SPDR Fund
- **XLK**: Technology Select Sector SPDR Fund
- **XLE**: Energy Select Sector SPDR Fund
- **XLV**: Health Care Select Sector SPDR Fund
- **XLI**: Industrial Select Sector SPDR Fund
- **XLP**: Consumer Staples Select Sector SPDR Fund
- **XLY**: Consumer Discretionary Select Sector SPDR Fund
- **VNQ**: Vanguard Real Estate Investment Trust ETF

### 🚀 혁신/성장 ETF (5개)
- **ARKK**: ARK Innovation ETF
- **ARKQ**: ARK Autonomous Technology & Robotics ETF
- **ARKW**: ARK Next Generation Internet ETF
- **ARKG**: ARK Genomic Revolution ETF
- **ARKF**: ARK Fintech Innovation ETF

### 💵 배당 ETF (2개)
- **SCHD**: Schwab US Dividend Equity ETF
- **VYM**: Vanguard High Dividend Yield ETF

## 📊 입력/출력 명세

### 입력 데이터 구조 (Financial Analyst 결과)
```json
{
  "risk_profile": "중립적",
  "risk_profile_reason": "35세 중년층으로 10년의 투자 경험을 보유하여 적정 수준의 위험 감수 가능",
  "required_annual_return_rate": 40.0,
  "return_rate_reason": "1년 내 40% 수익률 달성을 위해 공격적 투자 전략 필요"
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
  "strategy": "공격적 성장 전략: 높은 목표 수익률(40%) 달성을 위해 기술주 중심의 성장주 포트폴리오 구성",
  "reason": "QQQ(나스닥 기술주) 50% - 높은 성장 잠재력, SPY(S&P 500) 30% - 대형주 안정성, VTI(전체 시장) 20% - 추가 분산 효과"
}
```

## 🔄 기존 아키텍처와의 차이점

### 이전 (복잡함)
```
Portfolio Architect → MCP Gateway → Lambda Function → yfinance
                    ↑
              Cognito OAuth2 (복잡한 설정)
```

### 현재 (단순함)
```
Portfolio Architect → MCP Server → yfinance
                    ↑
              Cognito JWT Auth (간단한 설정)
```

### 주요 개선사항
1. **아키텍처 단순화**: Gateway + Lambda → MCP Server
2. **배포 과정 간소화**: 4단계 → 2단계 배포
3. **관리 포인트 감소**: 별도 Gateway 관리 불필요
4. **비용 최적화**: 중간 계층 제거로 비용 절감
5. **유지보수 용이**: 단일 MCP Server로 관리 간편
6. **폴더 구조 정리**: MCP 관련 파일들을 `mcp/` 폴더로 분리

## 🔗 연관 프로젝트

이 프로젝트는 **Financial Analyst**와 연동하여 완전한 투자 자문 시스템을 구성합니다:

1. **Financial Analyst** (Reflection 패턴) → 개인 재무 분석 및 위험 성향 평가
2. **Portfolio Architect** (Tool Use 패턴) → 실시간 데이터 기반 포트폴리오 설계

**통합 워크플로우:**
- Financial Analyst에서 JSON 형태의 재무 분석 결과 생성
- Portfolio Architect가 해당 결과를 입력받아 MCP Server 활용
- 30개 ETF 중 최적 3개 선택하여 포트폴리오 구성
- 실시간 가격 데이터 기반 투자 비율 최적화

---

## 🎉 주요 장점

✅ **단순한 아키텍처**: 복잡한 Gateway 제거로 관리 용이  
✅ **원클릭 배포**: 전체 시스템을 한 번에 배포  
✅ **비용 효율적**: 중간 계층 제거로 비용 절감  
✅ **확장 가능**: MCP Server에 새로운 도구 쉽게 추가  
✅ **테스트 용이**: 로컬/원격 테스트 도구 제공  
✅ **실시간 데이터**: yfinance를 통한 최신 ETF 가격 정보  
✅ **정리된 구조**: MCP 관련 파일들을 별도 폴더로 분리  

이제 Portfolio Architect는 더 간단하고 효율적인 MCP Server 기반 아키텍처로 동일한 기능을 제공하면서도 관리와 배포가 훨씬 쉬워졌습니다!