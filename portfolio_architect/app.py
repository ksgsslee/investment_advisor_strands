"""
app.py
Portfolio Architect Streamlit 애플리케이션 (AgentCore Runtime 버전)
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
import uuid

# 상위 디렉토리 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AVAILABLE_PRODUCTS

# 페이지 설정
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

# Functions
def display_available_products(trace_container, products_data):
    """Display available investment products in table format"""
    try:
        if isinstance(products_data, str):
            products = json.loads(products_data)
        else:
            products = products_data
        
        df = pd.DataFrame(
            [[ticker, desc] for ticker, desc in products.items()],
            columns=['티커', '설명']
        )
        
        trace_container.markdown("**사용 가능한 투자 상품**")
        trace_container.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "티커": st.column_config.TextColumn(width="small"),
                "설명": st.column_config.TextColumn(width="large")
            }
        )
    except Exception as e:
        trace_container.error(f"상품 목록 표시 오류: {str(e)}")

def display_product_data(trace_container, data):
    """Display price history charts for investment products"""
    try:
        if isinstance(data, str):
            price_data = json.loads(data)
        else:
            price_data = data
        
        # 여러 ETF가 있는 경우 하나의 차트에 모두 표시
        if len(price_data) > 1:
            fig = go.Figure()
            
            for ticker, prices in price_data.items():
                df = pd.DataFrame.from_dict(prices, orient='index', columns=['Price'])
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                
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
                title="선택된 ETF 가격 추이 비교",
                xaxis_title="날짜",
                yaxis_title="가격 ($)",
                height=500,
                showlegend=True,
                hovermode='x unified'
            )
            
            trace_container.plotly_chart(fig, use_container_width=True)
        
        else:
            # 단일 ETF인 경우 개별 차트
            for ticker, prices in price_data.items():
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
                
                trace_container.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        trace_container.error(f"가격 데이터 표시 오류: {str(e)}")
        # 디버깅을 위해 원본 데이터도 표시
        trace_container.json(data)

def create_pie_chart(data, chart_title=""):
    """Create a pie chart for portfolio allocation"""
    fig = go.Figure(data=[go.Pie(
        labels=list(data.keys()),
        values=list(data.values()),
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

def display_portfolio_suggestion(place_holder, input_content):
    """Display portfolio suggestion results"""
    try:
        if isinstance(input_content, str):
            # JSON 추출
            start_idx = input_content.find('{')
            end_idx = input_content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = input_content[start_idx:end_idx]
                data = json.loads(json_str)
            else:
                place_holder.error("포트폴리오 데이터를 찾을 수 없습니다.")
                return
        else:
            data = input_content
        
        sub_col1, sub_col2 = place_holder.columns([1, 1])
        
        with sub_col1:
            st.markdown("**포트폴리오**")
            fig = create_pie_chart(
                data["portfolio_allocation"],
                "포트폴리오 자산 배분"
            )
            st.plotly_chart(fig)
        
        with sub_col2:
            st.markdown("**투자 전략**")
            st.info(data["strategy"])
        
        place_holder.markdown("**상세 근거**")
        place_holder.write(data["reason"])
        
    except Exception as e:
        place_holder.error(f"포트폴리오 표시 오류: {str(e)}")
        place_holder.text(str(input_content))

def invoke_portfolio_architect(financial_analysis):
    """AgentCore Runtime 호출 (기존 Bedrock Agent 스타일 유지)"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"financial_analysis": financial_analysis})
        )
        
        # 응답을 표시할 컨테이너 생성
        placeholder = st.container()
        placeholder.subheader("Bedrock Reasoning")
        
        output_text = ""
        current_thinking = ""  # 현재 생각 중인 텍스트 (도구 호출 사이의 텍스트)
        
        # 실시간 텍스트 표시를 위한 placeholder
        current_text_placeholder = placeholder.empty()
        
        # tool_use_id와 tool_name을 매핑하는 딕셔너리 (핵심 추가!)
        tool_id_to_name = {}
        
        # SSE 형식 응답 처리
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])  # "data: " 제거
                    event_type = event_data.get("type")
                    
                    if event_type == "text_chunk":
                        # 텍스트 청크 누적하고 실시간 업데이트
                        chunk_data = event_data.get("data", "")
                        output_text += chunk_data
                        current_thinking += chunk_data
                        
                        # 실시간으로 현재까지의 생각 표시
                        if current_thinking.strip():
                            with current_text_placeholder.chat_message("assistant"):
                                st.markdown(current_thinking)
                    
                    elif event_type == "tool_use":
                        # 도구 사용 시작 - tool_id와 tool_name 매핑 저장
                        tool_name = event_data.get("tool_name", "")
                        tool_use_id = event_data.get("tool_use_id", "")
                        
                        # tool_name에서 실제 함수명 추출 (___로 분리해서 마지막 부분)
                        actual_tool_name = tool_name.split("___")[-1] if "___" in tool_name else tool_name
                        
                        # tool_id와 실제 tool_name 매핑 저장
                        tool_id_to_name[tool_use_id] = actual_tool_name
                        
                        current_thinking = ""  # 리셋
                    
                    elif event_type == "tool_result":
                        # 도구 실행 결과 표시 - tool_use_id로 실제 함수명 찾기
                        tool_use_id = event_data.get("tool_use_id", "")
                        actual_tool_name = tool_id_to_name.get(tool_use_id, "unknown")
                        
                        tool_content = event_data.get("content", [{}])
                        if tool_content and len(tool_content) > 0:
                            # JSON에서 실제 데이터 추출
                            result_text = tool_content[0].get("text", "{}")
                            parsed_result = json.loads(result_text)
                            body = parsed_result["response"]["payload"]["body"]

                            # 실제 함수명에 따라 적절한 display 함수 호출
                            if actual_tool_name == "get_available_products":
                                display_available_products(placeholder, body)
                            
                            elif actual_tool_name == "get_product_data":
                                display_product_data(placeholder, body)
                        
                        # 처리 완료된 tool_id는 딕셔너리에서 제거 (메모리 정리)
                        if tool_use_id in tool_id_to_name:
                            del tool_id_to_name[tool_use_id]
                    
                        # 현재 텍스트 placeholder 고정 (더 이상 업데이트 안 함)
                        current_text_placeholder = placeholder.empty()


                    elif event_type == "streaming_complete":
                        # 마지막 남은 AI 생각을 표시
                        if current_thinking.strip():
                            with current_text_placeholder.chat_message("assistant"):
                                st.markdown(current_thinking.strip())
                        # 스트리밍 완료
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        # 최종 포트폴리오 결과 표시
        placeholder.divider()
        placeholder.markdown("🤖 **Portfolio Architect**")
        placeholder.subheader("📌 포트폴리오 설계")
        display_portfolio_suggestion(placeholder, output_text)
        
        return {
            "status": "success",
            "output_text": output_text
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# 아키텍처 설명
with st.expander("아키텍처", expanded=True):
    st.markdown("""
    ### 🔄 AgentCore Runtime Architecture (Tool Use Pattern)
    ```
    재무 분석 결과 → AgentCore Runtime → 포트폴리오 설계사 AI → 도구 사용 → 최종 포트폴리오
    ```
    
    **구성 요소:**
    - **Portfolio Architect Agent**: 실시간 시장 데이터 기반 포트폴리오 설계
    - **Tool Use Pattern**: 외부 API 및 데이터 소스 활용
    - **AgentCore Runtime**: AWS 서버리스 실행 환경
    
    **사용 도구:**
    - `get_available_products()`: 투자 상품 목록 조회
    - `get_product_data(ticker)`: 실시간 가격 데이터 조회
    """)

# 입력 폼
st.markdown("**재무 분석 결과 입력(🤖 Financial Analyst)**")

financial_analysis = st.text_area(
    "JSON 형식",
    value='{"risk_profile": "공격적", "risk_profile_reason": "나이가 35세로 젊고, 주식 투자 경험이 10년으로 상당히 많으며, 총 투자 가능 금액이 5000만원으로 상당히 높은 편입니다.", "required_annual_return_rate": 40.0, "return_rate_reason": "필요 연간 수익률은 (70000000 - 50000000) / 50000000 * 100 = 40.00%입니다."}',
    height=200
)

submitted = st.button("분석 시작", use_container_width=True)

if submitted and financial_analysis:
    st.divider()
    
    with st.spinner("AI is processing..."):
        try:
            result = invoke_portfolio_architect(financial_analysis)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
            else:
                # 상세 정보
                with st.expander("상세 분석 데이터 보기"):
                    st.subheader("📥 입력 데이터")
                    st.json(json.loads(financial_analysis) if isinstance(financial_analysis, str) else financial_analysis)
                    
                    st.subheader("📊 완전한 설계 결과")
                    st.json(result)
                
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")