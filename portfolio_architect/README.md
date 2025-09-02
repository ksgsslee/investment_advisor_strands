# Portfolio Architect

AI 포트폴리오 설계사 - MCP Server 연동으로 실시간 ETF 데이터 기반 포트폴리오 설계

## 🏗️ 아키텍처

```
Portfolio Architect Agent → MCP Server → yfinance → ETF 데이터
                          ↑
                    Cognito JWT Auth
```

## 🚀 배포 및 실행

### 전체 시스템 배포
```bash
python deploy.py
```

### Streamlit 앱 실행
```bash
streamlit run app.py
```

### 시스템 정리
```bash
python cleanup.py
```

## 🎯 핵심 기능

- **Tool Use 패턴**: MCP Server를 통한 실시간 ETF 데이터 조회
- **30개 ETF 지원**: 배당주, 성장주, 가치주, 리츠, 채권, 원자재 등
- **맞춤형 설계**: 위험 성향과 목표 수익률 기반 포트폴리오 최적화
- **실시간 스트리밍**: AI 분석 과정 실시간 시각화

## 📊 지원 ETF 카테고리

- **배당주** (4개): SCHD, VYM, NOBL, DVY
- **성장주** (6개): QQQ, XLK, ARKK, XLV, ARKG, SOXX
- **가치주** (4개): VTV, VBR, IWD, VTEB
- **리츠** (3개): VNQ, VNQI, SCHH
- **ETF** (5개): SPY, VTI, VOO, IVV, ITOT
- **해외주식** (4개): VEA, VWO, VXUS, EFA
- **채권** (3개): BND, AGG, TLT
- **원자재** (3개): GLD, SLV, DBC

## 📋 입출력 형식

### 입력 (Financial Analyst 결과)
```json
{
  "risk_profile": "공격적",
  "risk_profile_reason": "35세, 10년 경험",
  "required_annual_return_rate": 40.0,
  "return_rate_reason": "1년 내 40% 수익률 필요"
}
```

### 출력 (포트폴리오 제안)
```json
{
  "portfolio_allocation": {"QQQ": 50, "SPY": 30, "ARKK": 20},
  "strategy": "공격적 성장 전략",
  "reason": "기술주 중심 고성장 포트폴리오"
}
```

## 🔧 주요 개선사항

- **단순한 아키텍처**: Gateway + Lambda → MCP Server
- **원클릭 배포**: 전체 시스템 한 번에 배포
- **비용 효율적**: 중간 계층 제거
- **가독성 향상**: 과도한 주석 제거, 코드 간소화
- **정리 자동화**: cleanup.py로 JSON 기반 정리 정보 저장