"""
app.py
Portfolio Architect Streamlit 애플리케이션 (AgentCore Runtime 버전)

AI 포트폴리오 설계사가 실시간으로 시장 데이터를 분석하여 
맞춤형 투자 포트폴리오를 제안하는 웹 애플리케이션
"""

import streamlit as st
import json
import os
import sys
import boto3
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

# 상위 디렉토리 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AVAILABLE_PRODUCTS

# ================================
# 페이지 설정 및 초기화
# ================================

st.set_page_config(page_title="Portfolio Architect")
st.title("🤖 Portfolio Architect")

# 배포 정보 로드
CURRENT_DIR = Path(__file__).parent.resolve()
try:
    with open(CURRENT_DIR / "deployment_info.json", "r") as f:
        deployment_info = json.load(f)
    AGENT_ARN = deployment_info["agent_arn"]
    REGION = deployment_info["region"]
except Exception as e:
    st.error("배포 정보를 찾을 수 없습니다. deploy.py를 먼저 실행해주세요.")
    st.stop()

# AgentCore 클라이언트 설정
agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)

# ================================
# 유틸리티 함수들
# ================================

def extract_json_from_text(text_content):
    """
    텍스트에서 JSON 데이터를 추출하는 함수
    
    Args:
        text_content (str): JSON이 포함된 텍스트
        
    Returns:
        dict: 파싱된 JSON 데이터 또는 None
    """
    if isinstance(text_content, dict):
        return text_content
    
    if not isinstance(text_content, str):
        return None
    
    # JSON 블록 찾기
    start_idx = text_content.find('{')
    end_idx = text_content.rfind('}') + 1
    
    if start_idx != -1 and end_idx != -1:
        try:
            json_str = text_content[start_idx:end_idx]
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    return None

def parse_tool_result(result_text):
    """
    도구 실행 결과에서 실제 데이터를 추출하는 함수
    
    Args:
        result_text (str): MCP Server 응답 JSON 문자열
        
    Returns:
        dict: 파싱된 데이터
    """
    try:
        # MCP Server 응답은 직접 JSON 형태일 수 있음
        if isinstance(result_text, str):
            parsed_result = json.loads(result_text)
        else:
            parsed_result = result_text
            
        # Lambda 형식인 경우
        if "response" in parsed_result and "payload" in parsed_result["response"]:
            return parsed_result["response"]["payload"]["body"]
        # 직접 데이터인 경우
        else:
            return parsed_result
            
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 에러: {e}")
        print(f"원본 텍스트: {result_text}")
        return result_text

# ================================
# 데이터 표시 함수들
# ================================

def display_available_products(container, products_data):
    """
    사용 가능한 투자 상품 목록을 테이블 형태로 표시
    
    Args:
        container: Streamlit 컨테이너
        products_data: 상품 데이터 (dict 또는 JSON 문자열)
    """
    try:
        # 데이터 타입 정규화
        if isinstance(products_data, str):
            products = json.loads(products_data)
        else:
            products = products_data
        
        # DataFrame 생성
        df = pd.DataFrame(
            [[ticker, desc] for ticker, desc in products.items()],
            columns=['티커', '설명']
        )
        
        # 테이블 표시
        container.markdown("**사용 가능한 투자 상품**")
        container.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "티커": st.column_config.TextColumn(width="small"),
                "설명": st.column_config.TextColumn(width="large")
            }
        )
    except Exception as e:
        container.error(f"상품 목록 표시 오류: {str(e)}")

def display_product_data(container, price_data):
    """
    ETF 가격 데이터를 차트로 표시
    
    Args:
        container: Streamlit 컨테이너
        price_data: 가격 데이터 (dict 또는 JSON 문자열)
    """
    try:
        # 데이터 타입 정규화
        if isinstance(price_data, str):
            data = json.loads(price_data)
        else:
            data = price_data
        
        # 각 ETF별로 개별 차트 표시
        for ticker, prices in data.items():
            df = pd.DataFrame.from_dict(prices, orient='index', columns=['Price'])
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Price'],
                    mode='lines',
                    name=ticker,
                    line=dict(width=2)
                )
            )
            
            fig.update_layout(
                title=f"{ticker} 가격 추이",
                xaxis_title="날짜",
                yaxis_title="가격 ($)",
                height=400,
                showlegend=True,
                hovermode='x unified'
            )
            
            container.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        container.error(f"가격 데이터 표시 오류: {str(e)}")

def create_pie_chart(allocation_data, chart_title=""):
    """
    포트폴리오 배분을 위한 파이 차트 생성
    
    Args:
        allocation_data (dict): 자산 배분 데이터
        chart_title (str): 차트 제목
        
    Returns:
        plotly.graph_objects.Figure: 파이 차트
    """
    fig = go.Figure(data=[go.Pie(
        labels=list(allocation_data.keys()),
        values=list(allocation_data.values()),
        hole=.3,
        textinfo='label+percent',
        marker=dict(colors=px.colors.qualitative.Set3)
    )])
    
    fig.update_layout(
        title=chart_title,
        showlegend=True,
        width=400,
        height=400
    )
    return fig

def display_portfolio_suggestion(container, portfolio_content):
    """
    최종 포트폴리오 제안 결과를 표시
    
    Args:
        container: Streamlit 컨테이너
        portfolio_content: 포트폴리오 데이터 (dict 또는 JSON 문자열)
    """
    try:
        # JSON 데이터 추출
        data = extract_json_from_text(portfolio_content)
        if not data:
            container.error("포트폴리오 데이터를 찾을 수 없습니다.")
            return
        
        # 2열 레이아웃으로 표시
        col1, col2 = container.columns([1, 1])
        
        with col1:
            st.markdown("**포트폴리오**")
            fig = create_pie_chart(
                data["portfolio_allocation"],
                "포트폴리오 자산 배분"
            )
            st.plotly_chart(fig)
        
        with col2:
            st.markdown("**투자 전략**")
            st.info(data["strategy"])
        
        # 상세 근거 표시
        container.markdown("**상세 근거**")
        container.write(data["reason"])
        
    except Exception as e:
        container.error(f"포트폴리오 표시 오류: {str(e)}")
        container.text(str(portfolio_content))

# ================================
# 메인 처리 함수
# ================================

def invoke_portfolio_architect(financial_analysis):
    """
    AgentCore Runtime을 호출하여 포트폴리오 설계 수행
    
    Args:
        financial_analysis (str): 재무 분석 결과 JSON
        
    Returns:
        dict: 실행 결과 (status, output_text)
    """
    try:
        # AgentCore Runtime 호출
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"financial_analysis": financial_analysis})
        )
        
        # UI 컨테이너 설정
        placeholder = st.container()
        placeholder.subheader("Bedrock Reasoning")
        
        # 상태 변수 초기화
        current_thinking = ""
        current_text_placeholder = placeholder.empty()
        tool_id_to_name = {}  # tool_use_id와 tool_name 매핑

        # 스트리밍 응답 처리
        for line in response["response"].iter_lines(chunk_size=1):
            try:
                event_data = json.loads(line.decode("utf-8")[6:])
                event_type = event_data.get("type")
                
                if event_type == "text_chunk":
                    # AI 생각 과정을 실시간으로 표시
                    chunk_data = event_data.get("data", "")
                    current_thinking += chunk_data
                    
                    if current_thinking.strip():
                        with current_text_placeholder.chat_message("assistant"):
                            st.markdown(current_thinking)
                
                elif event_type == "tool_use":
                    # 도구 사용 시작 - 매핑 정보 저장
                    tool_name = event_data.get("tool_name", "")
                    tool_use_id = event_data.get("tool_use_id", "")
                    
                    # 실제 함수명 추출 (target-portfolio-architect___get_available_products -> get_available_products)
                    actual_tool_name = tool_name.split("___")[-1] if "___" in tool_name else tool_name
                    tool_id_to_name[tool_use_id] = actual_tool_name
                
                elif event_type == "tool_result":
                    # 도구 실행 결과 처리
                    tool_use_id = event_data.get("tool_use_id", "")
                    actual_tool_name = tool_id_to_name.get(tool_use_id, "unknown")
                    
                    tool_content = event_data.get("content", [{}])
                    if tool_content and len(tool_content) > 0:
                        result_text = tool_content[0].get("text", "{}")
                        body = parse_tool_result(result_text)
                        
                        # 도구 타입에 따라 적절한 표시 함수 호출
                        if actual_tool_name == "get_available_products":
                            display_available_products(placeholder, body)
                        elif actual_tool_name == "get_product_data":
                            display_product_data(placeholder, body)
                    
                    # 도구 결과 처리 후 생각 텍스트 리셋 및 새로운 placeholder 생성
                    current_thinking = ""
                    if tool_use_id in tool_id_to_name:
                        del tool_id_to_name[tool_use_id]
                    current_text_placeholder = placeholder.empty()
                
                elif event_type == "streaming_complete":
                    # 마지막 AI 생각 표시 후 완료
                    if current_thinking.strip():
                        with current_text_placeholder.chat_message("assistant"):
                            st.markdown(current_thinking.strip())
                    break
                    
            except json.JSONDecodeError:
                continue
        
        # 최종 포트폴리오 결과 표시
        placeholder.divider()
        placeholder.markdown("🤖 **Portfolio Architect**")
        placeholder.subheader("📌 포트폴리오 설계")
        display_portfolio_suggestion(placeholder, current_thinking)
        
        return {
            "status": "success",
            "output_text": current_thinking
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ================================
# UI 구성
# ================================

# 아키텍처 설명
with st.expander("아키텍처", expanded=True):
    st.markdown("""
    ### 🔄 MCP Server Architecture (Tool Use Pattern)
    ```
    재무 분석 결과 → Portfolio Architect → MCP Server → ETF 데이터 → 최종 포트폴리오
    ```
    
    **구성 요소:**
    - **Portfolio Architect Agent**: AI 포트폴리오 설계사 (AgentCore Runtime)
    - **MCP Server**: ETF 데이터 조회 도구 서버 (AgentCore Runtime)
    - **Tool Use Pattern**: MCP 프로토콜을 통한 도구 활용
    - **yfinance**: 실시간 ETF 가격 데이터 소스
    
    **사용 도구:**
    - `get_available_products()`: 30개 ETF 상품 목록 조회
    - `get_product_data(ticker)`: 실시간 가격 데이터 조회 (최근 3개월)
    """)

# 입력 폼
st.markdown("**재무 분석 결과 입력(🤖 Financial Analyst)**")

financial_analysis = st.text_area(
    "JSON 형식",
    value='{"risk_profile": "공격적", "risk_profile_reason": "나이가 35세로 젊고, 주식 투자 경험이 10년으로 상당히 많으며, 총 투자 가능 금액이 5000만원으로 상당히 높은 편입니다.", "required_annual_return_rate": 40.0, "return_rate_reason": "필요 연간 수익률은 (70000000 - 50000000) / 50000000 * 100 = 40.00%입니다."}',
    height=200
)

submitted = st.button("분석 시작", use_container_width=True)

# 메인 실행 로직
if submitted and financial_analysis:
    st.divider()
    
    with st.spinner("AI is processing..."):
        try:
            result = invoke_portfolio_architect(financial_analysis)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")