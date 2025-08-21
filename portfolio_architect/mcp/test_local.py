"""
test_local.py
로컬 MCP 서버 테스트 클라이언트

MCP 서버를 로컬에서 테스트하기 위한 클라이언트입니다.
"""

import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    """로컬 MCP 서버 테스트"""
    mcp_url = "http://localhost:8000/mcp"
    headers = {}
    
    print("🔄 로컬 MCP 서버 연결 중...")
    print(f"📍 URL: {mcp_url}")
    
    try:
        async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                print("✅ MCP 세션 초기화 완료")
                
                # 사용 가능한 도구 목록 조회
                await session.initialize()
                tool_result = await session.list_tools()
                
                print("\n📋 사용 가능한 도구:")
                print("=" * 50)
                for tool in tool_result.tools:
                    print(f"🔧 {tool.name}")
                    print(f"   설명: {tool.description}")
                    if hasattr(tool, 'inputSchema') and tool.inputSchema:
                        properties = tool.inputSchema.get('properties', {})
                        if properties:
                            print(f"   파라미터: {list(properties.keys())}")
                    print()
                
                # 도구 테스트
                print("🧪 도구 테스트:")
                print("=" * 50)
                
                # 1. ETF 상품 목록 조회
                print("\n1️⃣ get_available_products 테스트...")
                try:
                    products_result = await session.call_tool(
                        name="get_available_products",
                        arguments={}
                    )
                    products_data = eval(products_result.content[0].text)
                    print(f"   ✅ {len(products_data)}개 ETF 상품 조회 완료")
                    print(f"   📋 예시: {list(products_data.items())[:3]}")
                except Exception as e:
                    print(f"   ❌ 오류: {e}")
                
                # 2. 특정 ETF 가격 데이터 조회
                print("\n2️⃣ get_product_data('QQQ') 테스트...")
                try:
                    price_result = await session.call_tool(
                        name="get_product_data",
                        arguments={"ticker": "QQQ"}
                    )
                    price_data = eval(price_result.content[0].text)
                    if "error" in price_data:
                        print(f"   ❌ 오류: {price_data['error']}")
                    else:
                        qqq_data = price_data.get("QQQ", {})
                        print(f"   ✅ QQQ 데이터 {len(qqq_data)}일 조회 완료")
                        # 최근 3일 데이터 표시
                        recent_dates = sorted(qqq_data.keys())[-3:]
                        for date in recent_dates:
                            print(f"   📈 {date}: ${qqq_data[date]}")
                except Exception as e:
                    print(f"   ❌ 오류: {e}")
                
                print("\n✅ 로컬 테스트 완료!")
                
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        print("\n💡 해결 방법:")
        print("1. 터미널에서 'python server.py' 실행")
        print("2. 서버가 완전히 시작될 때까지 대기")
        print("3. 다시 테스트 실행")

if __name__ == "__main__":
    asyncio.run(main())