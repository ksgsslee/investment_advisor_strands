"""
app.py
Investment Advisor Streamlit 애플리케이션

Multi-Agent 패턴 기반 투자 자문 시스템의 웹 인터페이스
3개의 전문 에이전트가 협업하여 종합적인 투자 분석을 제공합니다.
"""

import streamlit as st
import json
import boto3
import plotly.graph_objects as go
from pathlib import Path
import plotly.express as px
import os
from datetime import datetime

# ================================
# 페이지 설정 및 초기화
# ================================

st.set_page_config(page_title="Agentic AI Private Banker")

# 사이드바에 탭 선택
tab_selection = st.sidebar.radio("메뉴", ["새 분석", "리포트 히스토리"])

if tab_selection == "새 분석":
    st.title("🤖 Agentic AI Private Banker")
else:
    st.title("📋 투자 리포트 히스토리")

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

def create_pie_chart(allocation_data, chart_title=""):
    """포트폴리오 배분을 위한 파이 차트 생성"""
    fig = go.Figure(data=[go.Pie(
        labels=list(allocation_data.keys()),
        values=list(allocation_data.values()),
        hole=.3,
        textinfo='label+percent',
        marker=dict(colors=px.colors.qualitative.Set3)
    )])
    fig.update_layout(title=chart_title, showlegend=True, width=400, height=400)
    return fig


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

def display_financial_analysis(analysis_content):
    """
    재무 분석 결과 표시 (financial_analyst 스타일 적용)
    
    Args:
        analysis_content: 재무 분석 데이터 (dict 또는 JSON 문자열)
    """
    try:
        # JSON 데이터 추출
        data = extract_json_from_text(analysis_content)
        if not data:
            st.error("재무 분석 데이터를 찾을 수 없습니다.")
            return
            
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("**위험 성향**", data.get("risk_profile", "N/A"))
            st.markdown("**위험 성향 분석**")
            st.info(data.get("risk_profile_reason", ""))
        
        with col2:
            st.metric("**필요 수익률**", f"{data.get('required_annual_return_rate', 'N/A')}%")
            st.markdown("**수익률 분석**")
            st.info(data.get("return_rate_reason", ""))

    except Exception as e:
        st.error(f"재무 분석 표시 오류: {str(e)}")
        st.text(str(analysis_content))

def display_portfolio_design(portfolio_content):
    """
    포트폴리오 설계 결과 표시
    
    Args:
        portfolio_content: 포트폴리오 데이터 (dict 또는 JSON 문자열)
    """
    try:
        # JSON 데이터 추출
        data = extract_json_from_text(portfolio_content)
        if not data:
            st.error("포트폴리오 데이터를 찾을 수 없습니다.")
            return
        
        # 2열 레이아웃으로 표시
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📊 포트폴리오**")
            fig = create_pie_chart(
                data["portfolio_allocation"],
                "포트폴리오 자산 배분"
            )
            st.plotly_chart(fig)
        
        with col2:
            st.markdown("**💡 투자 전략**")
            st.info(data["strategy"])
        
        # 상세 근거 표시
        st.markdown("**📝 상세 근거**")
        st.write(data["reason"])
        
    except Exception as e:
        st.error(f"포트폴리오 표시 오류: {str(e)}")
        st.text(str(portfolio_content))

def display_risk_analysis(risk_content):
    """
    리스크 분석 결과 표시 (risk_manager 스타일 적용)
    
    Args:
        risk_content: 리스크 분석 데이터 (dict 또는 JSON 문자열)
    """
    try:
        # JSON 데이터 추출
        data = extract_json_from_text(risk_content)
        if not data:
            st.error("리스크 분석 데이터를 찾을 수 없습니다.")
            return
        
        # 각 시나리오별로 표시 (risk_manager 스타일)
        for i, scenario_key in enumerate(["scenario1", "scenario2"], 1):
            if scenario_key in data:
                scenario = data[scenario_key]
                
                st.subheader(f"시나리오 {i}: {scenario.get('name', f'Scenario {i}')}")
                st.markdown(scenario.get('description', '설명 없음'))
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # 파이 차트 생성 및 표시
                    allocation = scenario.get('allocation_management', {})
                    if allocation:
                        fig = create_pie_chart(
                            allocation,
                            "조정된 포트폴리오 자산 배분"
                        )
                        st.plotly_chart(fig)
                
                with col2:
                    st.markdown("**조정 이유 및 전략**")
                    st.info(scenario.get('reason', '근거 없음'))
        
    except Exception as e:
        st.error(f"리스크 분석 표시 오류: {str(e)}")
        st.text(str(risk_content))

# ================================
# 메인 처리 함수
# ================================

def invoke_investment_advisor(input_data):
    """AgentCore Runtime을 호출하여 투자 상담 수행"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": input_data})
        )
        
        results = {}
        
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    event_type = event_data.get("type")
                    
                    if event_type == "data":
                        message = event_data.get("message", "")
                        if message:
                            with st.chat_message("assistant"):
                                st.markdown(f"{message}")

                    elif event_type == "step_complete":
                        step_name = event_data.get("step_name")
                        data = event_data.get("data")
                        
                        if step_name == "financial_analyst":
                            st.subheader("🔍 재무 분석 결과")
                            display_financial_analysis(data)
                            results["financial_analysis"] = data
                            
                        elif step_name == "portfolio_architect":
                            st.subheader("📊 포트폴리오 설계")
                            display_portfolio_design(data)
                            results["portfolio_design"] = data
                            
                        elif step_name == "risk_manager":
                            st.subheader("⚠️ 리스크 분석")
                            display_risk_analysis(data)
                            results["risk_analysis"] = data
                            
                        elif "보고서" in step_name:
                            st.subheader("📝 종합 투자 보고서")
                            final_report = data.get("final_report", "")
                            st.markdown(final_report)
                            results["final_report"] = final_report

                    elif event_type == "streaming_complete":
                        final_result = event_data.get("final_result", {})
                        results.update(final_result)
                        break
                            
                    elif event_type == "error":
                        return {
                            "status": "error",
                            "error": event_data.get("error", "Unknown error")
                        }
                        
                except json.JSONDecodeError:
                    continue
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ================================
# 리포트 히스토리 조회 함수
# ================================

def get_report_history():
    """리포트 히스토리 조회"""
    try:
        # InvestmentAdvisor 인스턴스 생성하여 히스토리 조회
        from investment_advisor import InvestmentAdvisor
        advisor = InvestmentAdvisor()
        return advisor.get_report_history()
    except Exception as e:
        st.error(f"히스토리 조회 실패: {e}")
        return []

# ================================
# UI 구성
# ================================

if tab_selection == "리포트 히스토리":
    # 리포트 히스토리 표시
    st.markdown("최근 투자 분석 리포트들을 확인할 수 있습니다.")
    
    with st.spinner("리포트 히스토리를 불러오는 중..."):
        history = get_report_history()
    
    if not history:
        st.info("저장된 리포트가 없습니다.")
    else:
        for i, report in enumerate(history):
            with st.expander(f"📊 리포트 {i+1}: {report['user_info']}", expanded=False):
                st.markdown("**생성 시간:**")
                try:
                    timestamp = datetime.fromisoformat(report['timestamp'].replace('Z', '+00:00'))
                    st.text(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                except:
                    st.text(report['timestamp'])
                
                st.markdown("**투자자 정보:**")
                st.text(report['user_info'])
                
                st.markdown("**투자 분석 리포트:**")
                st.markdown(report['report'])
                st.divider()

else:
    # 기존 새 분석 UI
    # 아키텍처 설명
    with st.expander("아키텍처", expanded=True):
        st.image("../static/investment_advisor.png", width=500)

    # 입력 폼
    st.markdown("**투자자 정보 입력**")
    col1, col2, col3 = st.columns(3)

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
        age_options = [f"{i}-{i+4}세" for i in range(20, 101, 5)]
        age = st.selectbox(
            "나이",
            options=age_options,
            index=3
        )

    with col3:
        experience_categories = ["0-1년", "1-3년", "3-5년", "5-10년", "10-20년", "20년 이상"]
        stock_investment_experience_years = st.selectbox(
            "주식 투자 경험",
            options=experience_categories,
            index=3
        )

    target_amount = st.number_input(
        "💰 1년 후 목표 금액 (억원 단위)",
        min_value=0.0,
        max_value=1000.0,
        value=0.7,
        step=0.1,
        format="%.1f"
    )
    st.caption("예: 0.7 = 7천만원")

    submitted = st.button("분석 시작", use_container_width=True)

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
        }
        
        # 투자 분석 실행
        with st.spinner("AI 에이전트들이 분석 중입니다..."):
            result = invoke_investment_advisor(input_data)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
            else:
                st.success("✅ 투자 분석이 완료되었습니다!")