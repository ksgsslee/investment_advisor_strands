"""
config.py

전체 프로젝트 공통 설정
모든 배포 스크립트에서 사용하는 공통 설정값들을 관리합니다.
"""

class Config:
    """전체 프로젝트 공통 설정"""
    
    # AWS 리전 설정 (모든 에이전트에서 공통 사용)
    REGION = "us-west-2"
    
    # 에이전트별 이름 설정
    FINANCIAL_ANALYST_NAME = "financial_analyst"
    PORTFOLIO_ARCHITECT_NAME = "portfolio_architect"
    RISK_MANAGER_NAME = "risk_manager"
    FUND_MANAGER_NAME = "fund_manager"
    
    # MCP Server 설정
    MCP_SERVER_NAME = "mcp_server"
    
    # Gateway 설정
    GATEWAY_NAME = "gateway-risk-manager"
    TARGET_NAME = "target-risk-manager"
    
    # Lambda 설정
    LAMBDA_FUNCTION_NAME = "lambda-agentcore-risk-manager"
    LAMBDA_LAYER_NAME = "layer-yfinance"
    
    # Memory 설정
    MEMORY_NAME = "FundManager_Memory"
