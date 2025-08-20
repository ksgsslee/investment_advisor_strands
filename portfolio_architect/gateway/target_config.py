"""
target_config.py
Gateway Target 설정

Portfolio Architect Gateway에서 사용할 MCP 도구 스키마를 정의합니다.
Lambda 함수의 기능을 AI 에이전트가 사용할 수 있는 도구로 노출합니다.
"""

# ================================
# MCP 도구 스키마 설정
# ================================

TARGET_CONFIGURATION = {
    "mcp": {
        "lambda": {
            "lambdaArn": "",  # 배포 시 자동으로 Lambda ARN이 주입됩니다
            "toolSchema": {
                "inlinePayload": [
                    # ETF 상품 목록 조회 도구
                    {
                        "name": "get_available_products",
                        "description": "Retrieve list of available ETF products for portfolio construction. Returns a comprehensive list of ETF ticker symbols with descriptions for investment analysis.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    
                    # ETF 가격 데이터 조회 도구  
                    {
                        "name": "get_product_data",
                        "description": "Get recent price data for selected ETF ticker symbol. Returns historical price data for the past 3 months to analyze trends and performance.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "ticker": {
                                    "type": "string",
                                    "description": "ETF ticker symbol to retrieve price data for (e.g., 'QQQ', 'SPY', 'ARKK')"
                                }
                            },
                            "required": ["ticker"]
                        }
                    }
                ]
            }
        }
    }
}
