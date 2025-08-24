# Risk Manager 정리 가이드

## 🚀 사용법

```bash
cd risk_manager
python cleanup.py
```

## 🗑️ 삭제되는 리소스

### AWS 리소스
- **Lambda Layer**: yfinance 라이브러리 레이어 (먼저 삭제)
- **Lambda 함수**: 리스크 계산 함수
- **Risk Manager Runtime**: 메인 AI 에이전트
- **Cognito User Pool**: Gateway 인증용
- **ECR 리포지토리들**: Docker 이미지 저장소 2개
- **IAM 역할들**: 실행 권한 역할 3개

### 로컬 파일들
- `deployment_info.json`
- `gateway/gateway_deployment_info.json`
- `lambda/lambda_deployment_info.json`
- `lambda_layer/layer_deployment_info.json`
- Docker 관련 파일들 (Dockerfile, .dockerignore 등)

## 📋 예상 출력

```
🧹 risk_manager 전체 시스템 정리
==================================================
✅ main 배포 정보 로드
✅ gateway 배포 정보 로드
✅ lambda 배포 정보 로드

정말로 모든 리소스를 삭제하시겠습니까? (y/N): y

🚀 정리 시작...
🗑️ Lambda Layer 삭제 중...
  ✅ Lambda Layer: layer-yfinance-risk-manager
🗑️ Lambda 함수 삭제 중...
  ✅ Lambda 함수: agentcore-risk-manager
🗑️ Runtime 삭제 중...
  ✅ Main Runtime: risk_manager-abc123
🗑️ Cognito 리소스 삭제 중...
  ✅ User Pool: us-west-2_LFukDzqlL
🗑️ ECR 리포지토리 삭제 중...
  ✅ ECR: bedrock-agentcore-risk_manager
  ✅ ECR: bedrock-agentcore-gateway-risk-manager
🗑️ IAM 역할 삭제 중...
  ✅ IAM 역할: agentcore-runtime-risk_manager-role
  ✅ IAM 역할: agentcore-gateway-gateway-risk-manager-role
  ✅ IAM 역할: agentcore-lambda-risk-manager-role
🗑️ 생성된 파일들 정리 중...
  ✅ 삭제: deployment_info.json
  ✅ 삭제: gateway/gateway_deployment_info.json
  ✅ 삭제: lambda/lambda_deployment_info.json

🎉 정리 완료!

📋 정리된 항목:
• Lambda Layer
• Lambda 함수
• Risk Manager Runtime
• Cognito User Pool
• ECR 리포지토리들
• IAM 역할들
• 생성된 파일들
```

## ✨ 특징

- **간단하고 가독성 좋음**: 복잡한 예외 처리 없이 핵심 기능만
- **4개 시스템 통합 관리**: Layer + Lambda + Runtime + Gateway 한 번에 정리
- **Config 기반**: 하드코딩 없이 deploy.py의 설정 재사용
- **안전한 실행**: 실패해도 다음 단계 계속 진행

## ⚠️ 주의사항

- 모든 삭제 작업은 되돌릴 수 없습니다
- Cognito User Pool의 모든 사용자 데이터가 삭제됩니다
- 실패한 리소스는 AWS 콘솔에서 수동 삭제 필요