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
from typing import Dict, Any

# 상위 디렉토리 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AVAILABLE_PRODUCTS

# 페이지 설정
st.set_page_config(page_title="Portfolio Architect")
st.title("📈 Portfolio Architect (AgentCore Version)")

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

def display_portfolio_analysis(trace_container, portfolio_data):
    """포트폴리오 분석 결과 표시"""
    try:
        # JSON 파싱 시도
        result_text = portfolio_data
        start_idx = result_text.find('{')
        end_idx = result_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = result_text[start_idx:end_idx]
            portfolio = json.loads(json_str)
            
            # 포트폴리오 배분 표시
            allocation = portfolio.get('portfolio_allocation', {})
            if allocation:
                sub_col1, sub_col2 = trace_container.columns(2)
                
                with sub_col1:
                    st.subheader("📊 자산 배분")
                    df_allocation = []
                    for ticker, ratio in allocation.items():
                        description = AVAILABLE_PRODUCTS.get(ticker, "설명 없음")
                        df_allocation.append({
                            "ETF": ticker,
                            "배분 비율 (%)": ratio,
                            "설명": description
                        })
                    
                    df = pd.DataFrame(df_allocation)
                    st.dataframe(df, use_container_width=True)
                
                with sub_col2:
                    # 파이 차트
                    fig_pie = px.pie(
                        values=list(allocation.values()),
                        names=list(allocation.keys()),
                        title="포트폴리오 자산 배분"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                # 전략 및 근거
                trace_container.subheader("💡 투자 전략")
                trace_container.write(portfolio.get('strategy', ''))
                
                trace_container.subheader("📋 구성 근거")
                trace_container.write(portfolio.get('reason', ''))
            else:
                trace_container.warning("포트폴리오 배분 데이터를 찾을 수 없습니다.")
        else:
            trace_container.error("포트폴리오 데이터 파싱 실패")
            trace_container.text(portfolio_data)
            
    except Exception as e:
        trace_container.error(f"포트폴리오 표시 중 오류: {str(e)}")
        trace_container.text(portfolio_data)

def invoke_portfolio_architect(financial_analysis):
    """AgentCore Runtime 호출"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"financial_analysis": financial_analysis})
        )

        # 응답을 표시할 컨테이너 생성
        placeholder = st.container()
        placeholder.markdown("📈 **Portfolio Architect (AgentCore)**")

        # SSE 형식 응답 처리
        portfolio_data = None

        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])  # "data: " 제거
                    
                    if event_data["type"] == "data":
                        if "portfolio_data" in event_data:
                            portfolio_data = event_data["portfolio_data"]
                            # 포트폴리오 결과 즉시 표시
                            placeholder.subheader("📌 포트폴리오 설계 결과")
                            display_portfolio_analysis(placeholder, portfolio_data)
                            
                    elif event_data["type"] == "error":
                        return {
                            "status": "error",
                            "error": event_data.get("error", "Unknown error")
                        }
                except json.JSONDecodeError:
                    continue

        return {
            "portfolio_data": portfolio_data,
            "status": "success"
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
st.markdown("**재무 분석 결과 입력**")
col1, col2 = st.columns(2)

with col1:
    risk_profile = st.selectbox(
        "위험 성향",
        ["매우 보수적", "보수적", "중립적", "공격적", "매우 공격적"],
        index=3
    )
    
    required_return = st.number_input(
        "필요 연간 수익률 (%)",
        min_value=0.0,
        max_value=100.0,
        value=40.0,
        step=0.1
    )

with col2:
    risk_reason = st.text_area(
        "위험 성향 평가 근거",
        value="나이가 35세로 젊고, 주식 투자 경험이 10년으로 상당히 많으며, 총 투자 가능 금액이 5000만원으로 상당히 높은 편입니다.",
        height=100
    )
    
    return_reason = st.text_area(
        "수익률 계산 근거",
        value="필요 연간 수익률은 (70000000 - 50000000) / 50000000 * 100 = 40.00%입니다.",
        height=100
    )

submitted = st.button("포트폴리오 설계 시작", use_container_width=True)

if submitted:
    financial_analysis = {
        "risk_profile": risk_profile,
        "risk_profile_reason": risk_reason,
        "required_annual_return_rate": required_return,
        "return_rate_reason": return_reason
    }
    
    st.divider()
    
    with st.spinner("AI 포트폴리오 설계 중..."):
        try:
            result = invoke_portfolio_architect(financial_analysis)
            
            if result['status'] == 'error':
                st.error(f"❌ 설계 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                st.stop()
            
            # 상세 정보
            with st.expander("상세 분석 데이터 보기"):
                st.subheader("📥 입력 데이터")
                st.json(financial_analysis)
                
                st.subheader("📊 완전한 설계 결과")
                st.json(result)
                
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")