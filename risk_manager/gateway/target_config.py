"""
target_config.py
Gateway Target 설정

Risk Manager Gateway에서 사용할 MCP 도구 스키마를 정의합니다.
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
                    # ETF 뉴스 조회 도구
                    {
                        "name": "get_product_news",
                        "description": "Retrieve latest news information for selected ETF ticker symbol. Returns recent news articles with titles, summaries, and publication dates for risk analysis and market sentiment evaluation.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "ticker": {
                                    "type": "string",
                                    "description": "ETF ticker symbol to retrieve news for (e.g., 'QQQ', 'SPY', 'GLD')"
                                }
                            },
                            "required": ["ticker"]
                        }
                    },
                    
                    # 거시경제 지표 조회 도구  
                    {
                        "name": "get_market_data",
                        "description": "Get major macroeconomic indicators data including US Dollar Index, Treasury yields, VIX volatility index, and crude oil prices. Returns real-time market data for economic scenario planning and risk assessment.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                ]
            }
        }
    }
}