"""
app.py

Investment Advisor Streamlit 애플리케이션
Multi-Agent 패턴 기반 투자 자문 시스템의 웹 인터페이스
"""

import streamlit as st
import json
import boto3
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path
from datetime import datetime

# ================================
# 페이지 설정 및 초기화
# ================================

st.set_page_config(page_title="🤖 Investment Advisor")
st.title("🤖 Investment Advisor - Multi-Agent 투자 자문")

# 배포 정보 로드
try:
    with open(Path(__file__).parent / "deployment_info.json", "r") as f:
        deployment_info = json.load(f)
    AGENT_ARN = deployment_info["agent_arn"]
    REGION = deployment_info["region"]
except Exception as e:
    st.error("배포 정보를 찾을 수 없습니다. deploy.py를 먼저 실행해주세요.")
    st.stop()

agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)

# ================================
# 유틸리티 함수들 (각 에이전트 app.py에서 복사)
# ================================

def extract_json_from_text(text_content):
    """텍스트에서 JSON 추출"""
    if isinstance(text_content, dict):
        return text_content
    if not isinstance(text_content, str):
        return None
    
    start = text_content.find('{')
    end = text_content.rfind('}') + 1
    if start != -1 and end > start:
        try:
            return json.loads(text_content[start:end])
        except json.JSONDecodeError:
            return None
    return None

def create_pie_chart(allocation_data, chart_title=""):
    """포트폴리오 배분 파이 차트 생성"""
    fig = go.Figure(data=[go.Pie(
        labels=list(allocation_data.keys()),
        values=list(allocation_data.values()),
        hole=.3,
        textinfo='label+percent',
        marker=dict(colors=px.colors.qualitative.Set3)
    )])
    fig.update_layout(title=chart_title, showlegend=True, width=400, height=400)
    return fig

# ================================
# 각 에이전트별 결과 표시 함수들 (각 app.py에서 복사)
# ================================

def display_financial_analysis(container, analysis_content):
    """재무 분석 결과 표시 (financial_analyst 스타일)"""
    try:
        data = extract_json_from_text(analysis_content)
        if not data:
            container.error("재무 분석 데이터를 찾을 수 없습니다.")
            return
            
        container.markdown("**종합 총평**")
        container.info(data.get("summary", ""))

        col1, col2 = container.columns(2)
        
        with col1:
            st.metric("**위험 성향**", data.get("risk_profile", "N/A"))
            st.markdown("**위험 성향 분석**")
            st.write(data.get("risk_profile_reason", ""))
        
        with col2:
            st.metric("**필요 수익률**", f"{data.get('required_annual_return_rate', 'N/A')}%")
            st.markdown("**수익률 분석**")
            st.write(data.get("return_rate_reason", ""))

    except Exception as e:
        container.error(f"재무 분석 표시 오류: {str(e)}")

def display_portfolio_result(container, portfolio_content):
    """포트폴리오 설계 결과 표시 (portfolio_architect 스타일)"""
    try:
        data = extract_json_from_text(portfolio_content)
        if not data:
            container.error("포트폴리오 데이터를 찾을 수 없습니다.")
            return
        
        col1, col2 = container.columns(2)
        
        with col1:
            st.markdown("**포트폴리오 배분**")
            fig = go.Figure(data=[go.Pie(
                labels=list(data["portfolio_allocation"].keys()),
                values=list(data["portfolio_allocation"].values()),
                hole=.3,
                textinfo='label+percent'
            )])
            fig.update_layout(height=400)
            st.plotly_chart(fig)
        
        with col2:
            st.markdown("**포트폴리오 구성 근거**")
            st.info(data["reason"])
        
        # Portfolio Scores 표시
        if "portfolio_scores" in data:
            container.markdown("**포트폴리오 평가 점수**")
            scores = data["portfolio_scores"]
            
            col1, col2, col3 = container.columns(3)
            with col1:
                profitability = scores.get("profitability", {})
                st.metric("수익성", f"{profitability.get('score', 'N/A')}/10")
                if profitability.get('reason'):
                    st.caption(profitability['reason'])
            
            with col2:
                risk_mgmt = scores.get("risk_management", {})
                st.metric("리스크 관리", f"{risk_mgmt.get('score', 'N/A')}/10")
                if risk_mgmt.get('reason'):
                    st.caption(risk_mgmt['reason'])
            
            with col3:
                diversification = scores.get("diversification", {})
                st.metric("분산투자 완성도", f"{diversification.get('score', 'N/A')}/10")
                if diversification.get('reason'):
                    st.caption(diversification['reason'])
        
    except Exception as e:
        container.error(f"포트폴리오 표시 오류: {str(e)}")

def display_risk_analysis_result(container, analysis_content):
    """리스크 분석 결과 표시 (risk_manager 스타일)"""
    try:
        data = extract_json_from_text(analysis_content)
        if not data:
            container.error("리스크 분석 데이터를 찾을 수 없습니다.")
            return
        
        for i, scenario_key in enumerate(["scenario1", "scenario2"], 1):
            if scenario_key in data:
                scenario = data[scenario_key]
                
                container.subheader(f"시나리오 {i}: {scenario.get('name', f'Scenario {i}')}")
                container.markdown(scenario.get('description', '설명 없음'))
                
                # 시나리오 확률 표시
                probability_str = scenario.get('probability', '0%')
                try:
                    prob_value = int(probability_str.replace('%', ''))
                    container.markdown(f"**📊 발생 확률: {probability_str}**")
                    container.progress(prob_value / 100)
                except:
                    container.markdown(f"**📊 발생 확률: {probability_str}**")
                
                col1, col2 = container.columns(2)
                
                with col1:
                    st.markdown("**조정된 포트폴리오 배분**")
                    allocation = scenario.get('allocation_management', {})
                    if allocation:
                        fig = go.Figure(data=[go.Pie(
                            labels=list(allocation.keys()),
                            values=list(allocation.values()),
                            hole=.3,
                            textinfo='label+percent'
                        )])
                        fig.update_layout(height=400, title=f"시나리오 {i} 포트폴리오")
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**조정 이유 및 전략**")
                    st.info(scenario.get('reason', '근거 없음'))

                container.divider()
        
    except Exception as e:
        container.error(f"리스크 분석 표시 오류: {str(e)}")

# ================================
# 메인 처리 함수
# ================================

def invoke_investment_advisor(input_data):
    """Investment Advisor 호출 및 실시간 결과 표시"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": input_data})
        )
        
        # 진행 상황 표시용 컨테이너들
        progress_container = st.container()
        results_container = st.container()
        
        # 진행 상황 추적
        current_agent = None
        agent_containers = {}
        
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    event_type = event_data.get("type")
                    
                    if event_type == "node_start":
                        agent_name = event_data.get("agent_name")
                        session_id = event_data.get("session_id")
                        current_agent = agent_name
                        
                        # 에이전트별 컨테이너 생성
                        agent_display_names = {
                            "financial": "🔍 재무 분석가",
                            "portfolio": "📊 포트폴리오 아키텍트", 
                            "risk": "⚠️ 리스크 매니저"
                        }
                        
                        with progress_container:
                            st.info(f"{agent_display_names.get(agent_name, agent_name)} 분석 시작...")
                        
                        # 결과 표시용 컨테이너 미리 생성
                        agent_containers[agent_name] = results_container.container()
                        
                    elif event_type == "node_complete":
                        agent_name = event_data.get("agent_name")
                        result = event_data.get("result")
                        
                        if agent_name in agent_containers and result:
                            container = agent_containers[agent_name]
                            
                            # 각 에이전트별 결과 표시
                            if agent_name == "financial":
                                container.subheader("🔍 재무 분석 결과")
                                display_financial_analysis(container, result)
                                
                            elif agent_name == "portfolio":
                                container.subheader("📊 포트폴리오 설계")
                                display_portfolio_result(container, result)
                                
                            elif agent_name == "risk":
                                container.subheader("⚠️ 리스크 분석 및 시나리오 플래닝")
                                display_risk_analysis_result(container, result)
                        
                        with progress_container:
                            agent_display_names = {
                                "financial": "🔍 재무 분석가",
                                "portfolio": "📊 포트폴리오 아키텍트", 
                                "risk": "⚠️ 리스크 매니저"
                            }
                            st.success(f"{agent_display_names.get(agent_name, agent_name)} 분석 완료!")
                            
                    elif event_type == "error":
                        return {
                            "status": "error",
                            "error": event_data.get("error", "Unknown error")
                        }
                        
                except json.JSONDecodeError:
                    continue
        
        # 최종 완료 메시지
        with progress_container:
            st.success("🎉 모든 에이전트 분석 완료!")
        
        return {"status": "success"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ================================
# UI 구성
# ================================

# 아키텍처 설명
with st.expander("🏗️ Multi-Agent 아키텍처", expanded=False):
    st.markdown("""
    **3개의 전문 AI 에이전트가 순차적으로 협업합니다:**
    
    1. **🔍 재무 분석가** (Reflection 패턴)
       - 개인 재무 상황 분석 및 위험 성향 평가
       - Calculator 도구로 정확한 수익률 계산
       
    2. **📊 포트폴리오 아키텍트** (Tool Use 패턴)  
       - 실시간 ETF 데이터 기반 포트폴리오 설계
       - 몬테카를로 시뮬레이션으로 성과 분석
       
    3. **⚠️ 리스크 매니저** (Planning 패턴)
       - 뉴스 기반 리스크 분석 및 시나리오 플래닝
       - 2개 경제 시나리오별 포트폴리오 조정 전략
    """)

# 입력 폼
st.markdown("### 📝 투자자 정보 입력")

col1, col2 = st.columns(2)

with col1:
    total_investable_amount = st.number_input(
        "💰 투자 가능 금액 (억원 단위)",
        min_value=0.0,
        max_value=1000.0,
        value=0.5,
        step=0.1,
        format="%.1f"
    )
    st.caption("예: 0.5 = 5천만원")

with col2:
    target_amount = st.number_input(
        "🎯 1년 후 목표 금액 (억원 단위)",
        min_value=0.0,
        max_value=1000.0,
        value=0.7,
        step=0.1,
        format="%.1f"
    )
    st.caption("예: 0.7 = 7천만원")

col3, col4, col5 = st.columns(3)

with col3:
    age_options = [f"{i}-{i+4}세" for i in range(20, 101, 5)]
    age = st.selectbox(
        "나이",
        options=age_options,
        index=3
    )

with col4:
    experience_categories = ["0-1년", "1-3년", "3-5년", "5-10년", "10-20년", "20년 이상"]
    stock_investment_experience_years = st.selectbox(
        "주식 투자 경험",
        options=experience_categories,
        index=3
    )

with col5:
    investment_purpose = st.selectbox(
        "🎯 투자 목적",
        options=["단기 수익 추구", "노후 준비", "주택 구입 자금", "자녀 교육비", "여유 자금 운용"],
        index=0
    )

preferred_sectors = st.multiselect(
    "📈 관심 투자 분야 (복수 선택)",
    options=[
        "배당주 (안정적 배당)",
        "성장주 (기술/바이오)",
        "가치주 (저평가 우량주)", 
        "리츠 (부동산 투자)",
        "ETF (분산 투자)",
        "해외 주식",
        "채권 (안전 자산)",
        "원자재/금"
    ],
    default=["ETF (분산 투자)"]
)

submitted = st.button("🚀 Multi-Agent 분석 시작", use_container_width=True, type="primary")

if submitted:
    # 나이 범위를 숫자로 변환
    age_number = int(age.split('-')[0]) + 2
    
    # 경험 년수를 숫자로 변환
    experience_mapping = {
        "0-1년": 1, "1-3년": 2, "3-5년": 4, 
        "5-10년": 7, "10-20년": 15, "20년 이상": 25
    }
    experience_years = experience_mapping[stock_investment_experience_years]
    
    # 입력 데이터 구성
    input_data = {
        "total_investable_amount": int(total_investable_amount * 100000000),
        "age": age_number,
        "stock_investment_experience_years": experience_years,
        "target_amount": int(target_amount * 100000000),
        "investment_purpose": investment_purpose,
        "preferred_sectors": preferred_sectors
    }
    
    st.divider()
    st.markdown("### 🤖 AI 에이전트 분석 진행")
    
    # 투자 분석 실행
    result = invoke_investment_advisor(input_data)
    
    if result['status'] == 'error':
        st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
    else:
        st.balloons()  # 성공 시 축하 애니메이션