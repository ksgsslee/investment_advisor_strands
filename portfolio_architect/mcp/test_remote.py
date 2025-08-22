"""
test_remote.py
원격 MCP Server 테스트 클라이언트

AWS에 배포된 MCP Server를 테스트하기 위한 클라이언트입니다.
로컬 배포 정보 파일에서 bearer_token을 로드하여 인증에 사용합니다.
"""

import asyncio
import json
import sys
from pathlib import Path
from boto3.session import Session
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    """원격 MCP Server 테스트"""
    boto_session = Session()
    region = boto_session.region_name or "us-west-2"
    print(f"🌍 AWS 리전: {region}")
    
    try:
        # 로컬 배포 정보에서 bearer_token 로드
        print("📋 로컬 배포 정보에서 로드 중...")
        info_file = Path(__file__).parent / "mcp_deployment_info.json"
        
        if info_file.exists():
            with open(info_file, 'r') as f:
                local_info = json.load(f)
            agent_arn = local_info['agent_arn']
            bearer_token = local_info['bearer_token']  # 🔑 여기서 bearer_token 사용!
            print(f"✅ 로컬 정보 로드 완료: {agent_arn}")
        else:
            raise FileNotFoundError("로컬 배포 정보 파일 없음")
            
    except Exception as e:
        print(f"❌ 로컬 정보 로드 실패: {e}")
        print("\n💡 해결 방법:")
        print("1. 먼저 'python deploy.py' 실행")
        print("2. AWS 권한 확인")
        print("3. 리전 설정 확인")
        sys.exit(1)
    
    # MCP URL 구성
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    # 🔑 Bearer 토큰을 Authorization 헤더에 설정 (인증용!)
    headers = {
        "authorization": f"Bearer {bearer_token}",  # 🔑 여기서 bearer_token 사용!
        "Content-Type": "application/json"
    }
    
    print(f"\n🔄 MCP Server 연결 중...")
    print(f"📍 URL: {mcp_url}")
    print(f"🔑 Bearer Token: {bearer_token[:20]}...")  # 일부만 표시
    
    try:
        async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                print("✅ MCP 세션 초기화 완료")
                
                # 사용 가능한 도구 목록 조회
                await session.initialize()
                tool_result = await session.list_tools()
                
                print("\n📋 사용 가능한 도구:")
                print("=" * 60)
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
                print("=" * 60)
                
                # 1. ETF 상품 목록 조회
                print("\n1️⃣ get_available_products 테스트...")
                try:
                    products_result = await session.call_tool(
                        name="get_available_products",
                        arguments={}
                    )
                    products_text = products_result.content[0].text
                    products_data = eval(products_text)
                    print(f"   ✅ {len(products_data)}개 ETF 상품 조회 완료")
                    
                    # 카테고리별 상품 수 표시
                    categories = {
                        "주요 지수": ["SPY", "QQQ", "VTI", "VOO", "IVV"],
                        "국제/신흥국": ["VEA", "VWO", "VXUS", "EFA", "EEM"],
                        "채권/안전자산": ["BND", "AGG", "TLT", "GLD", "SLV"],
                        "섹터별": ["XLF", "XLK", "XLE", "XLV", "XLI", "XLP", "XLY", "VNQ"],
                        "혁신/성장": ["ARKK", "ARKQ", "ARKW", "ARKG", "ARKF"],
                        "배당": ["SCHD", "VYM"]
                    }
                    
                    for category, tickers in categories.items():
                        available_count = sum(1 for ticker in tickers if ticker in products_data)
                        print(f"   📊 {category}: {available_count}개")
                        
                except Exception as e:
                    print(f"   ❌ 오류: {e}")
                
                # 2. 특정 ETF 가격 데이터 조회 (QQQ)
                print("\n2️⃣ get_product_data('QQQ') 테스트...")
                try:
                    price_result = await session.call_tool(
                        name="get_product_data",
                        arguments={"ticker": "QQQ"}
                    )
                    price_text = price_result.content[0].text
                    price_data = eval(price_text)
                    
                    if "error" in price_data:
                        print(f"   ❌ 오류: {price_data['error']}")
                    else:
                        qqq_data = price_data.get("QQQ", {})
                        print(f"   ✅ QQQ 데이터 {len(qqq_data)}일 조회 완료")
                        
                        # 최근 5일 데이터 표시
                        recent_dates = sorted(qqq_data.keys())[-5:]
                        print("   📈 최근 5일 가격:")
                        for date in recent_dates:
                            print(f"      {date}: ${qqq_data[date]}")
                            
                except Exception as e:
                    print(f"   ❌ 오류: {e}")
                
                print("\n" + "=" * 60)
                print("✅ 원격 MCP Server 테스트 완료!")
                print(f"🔧 총 {len(tool_result.tools)}개 도구 사용 가능")
                print("🎯 Portfolio Architect에서 사용할 준비 완료")
                print("=" * 60)
                
    except Exception as e:
        print(f"❌ MCP Server 연결 실패: {e}")
        print("\n💡 해결 방법:")
        print("1. MCP Server 배포 상태 확인")
        print("2. Bearer 토큰 유효성 확인")
        print("3. 네트워크 연결 확인")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())