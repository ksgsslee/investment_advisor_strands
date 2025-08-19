"""
Gateway Target 설정

MCP 도구 스키마 정의
"""

TARGET_CONFIGURATION = {
    "mcp": {
        "lambda": {
            "lambdaArn": "",
            "toolSchema": {
                "inlinePayload": [
                    # ETF 상품 목록 조회 도구
                    {
                        "name": "get_available_products",
                        "description": "Retrieve list of available ETF products for portfolio construction",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    
                    # ETF 가격 데이터 조회 도구
                    {
                        "name": "get_product_data",
                        "description": "Get recent price data for selected ETF ticker symbol",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "ticker": {
                                    "type": "string",
                                    "description": "ETF ticker symbol to retrieve price data for"
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