"""
target_config.py

Gateway Target 설정
Risk Manager Gateway에서 사용할 MCP 도구 스키마를 정의합니다.
"""

TARGET_CONFIGURATION = {
    "mcp": {
        "lambda": {
            "lambdaArn": "",  # 배포 시 자동으로 Lambda ARN이 주입됩니다
            "toolSchema": {
                "inlinePayload": [
                    # ETF 뉴스 조회 도구
                    {
                        "name": "get_product_news",
                        "description": "선택한 ETF 티커의 최신 뉴스 정보를 조회합니다. 리스크 분석과 시장 심리 평가를 위해 제목, 요약, 발행일이 포함된 최근 뉴스 기사들을 반환합니다.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "ticker": {
                                    "type": "string",
                                    "description": "뉴스를 조회할 ETF 티커 심볼 (예: 'QQQ', 'SPY', 'GLD')"
                                }
                            },
                            "required": ["ticker"]
                        }
                    },
                    
                    # 거시경제 지표 조회 도구  
                    {
                        "name": "get_market_data",
                        "description": "미국 달러 지수, 국채 수익률, VIX 변동성 지수, 원유 가격 등 주요 거시경제 지표 데이터를 조회합니다. 경제 시나리오 계획 수립과 리스크 평가를 위한 실시간 시장 데이터를 반환합니다.",
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