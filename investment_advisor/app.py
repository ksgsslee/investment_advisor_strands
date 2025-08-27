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

# ================================
# 페이지 설정 및 초기화
# ================================

st.set_page_config(page_title="Investment Advisor")
st.title("🤖 Investment Advisor")

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
        textinfo='label+percent'
    )])
    fig.update_layout(title=chart_title, showlegend=True, width=400, height=400)
    return fig

def display_financial_analysis(analysis_content):
    """
    재무 분석 결과 표시
    
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
            st.metric("위험 성향", data.get("risk_profile", "N/A"))
            st.info(data.get("risk_profile_reason", ""))
        
        with col2:
            st.metric("필요 수익률", f"{data.get('required_annual_return_rate', 'N/A')}%")
            st.info(data.get("return_rate_reason", ""))

    except Exception as e:
        st.error(f"재무 분석 표시 오류: {str(e)}")
        st.text(str(analysis_content))

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
                        step = event_data.get("step")
                        message = event_data.get("message", "")
                        if step and message:
                            st.info(f"**단계 {step}**: {message}")
                    
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
# UI 구성
# ================================

# 아키텍처 설명
with st.expander("아키텍처", expanded=True):
    st.markdown("""
    ### 🔄 Multi-Agent Architecture (AgentCore Runtime)
    ```
    사용자 입력 → Investment Advisor → 3개 전문 에이전트 순차 호출 → 통합 리포트 + Memory 저장
    ```
    
    **구성 요소:**
    - **Investment Advisor Agent**: Multi-Agent 패턴으로 3개 에이전트 협업 관리
    - **Financial Analyst**: Reflection 패턴으로 재무 분석 + 자체 검증
    - **Portfolio Architect**: Tool Use 패턴으로 실시간 ETF 데이터 기반 포트폴리오 설계
    - **Risk Manager**: Planning 패턴으로 뉴스 분석 + 시나리오 플래닝
    - **AgentCore Memory**: 상담 히스토리 자동 저장 및 개인화
    
    **Agents as Tools 패턴:**
    - 각 전문 에이전트를 도구로 활용하여 깔끔한 아키텍처 구현
    - 실시간 스트리밍으로 분석 과정 시각화
    """)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_info" not in st.session_state:
    st.session_state.user_info = None

# 사용자 정보 입력 (처음에만)
if st.session_state.user_info is None:
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

    if st.button("💬 투자 상담 시작", use_container_width=True):
        # 나이 범위를 숫자로 변환
        age_number = int(age.split('-')[0]) + 2
        
        # 경험 년수를 숫자로 변환
        experience_mapping = {
            "0-1년": 1, "1-3년": 2, "3-5년": 4, 
            "5-10년": 7, "10-20년": 15, "20년 이상": 25
        }
        experience_years = experience_mapping[stock_investment_experience_years]
        
        st.session_state.user_info = {
            "total_investable_amount": int(total_investable_amount * 100000000),
            "age": age_number,
            "stock_investment_experience_years": experience_years,
            "target_amount": int(target_amount * 100000000),
        }
        st.rerun()

else:
    # 투자 상담 실행
    st.markdown("### 🤖 AI 투자 상담 결과")
    
    # 사용자 정보 표시 (사이드바)
    with st.sidebar:
        st.header("📊 투자자 정보")
        st.write(f"💰 투자금액: {st.session_state.user_info['total_investable_amount'] / 100000000:.1f}억원")
        st.write(f"👤 나이: {st.session_state.user_info['age']}세")
        st.write(f"📈 경험: {st.session_state.user_info['stock_investment_experience_years']}년")
        st.write(f"🎯 목표금액: {st.session_state.user_info['target_amount'] / 100000000:.1f}억원")
        
        if st.button("🔄 정보 다시 입력"):
            st.session_state.user_info = None
            st.rerun()
    
    # 투자 상담 실행
    if st.button("🚀 투자 분석 시작", use_container_width=True):
        with st.spinner("AI 에이전트들이 분석 중입니다..."):
            result = invoke_investment_advisor(st.session_state.user_info)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
            else:
                st.success("✅ 투자 분석이 완료되었습니다!")
                st.session_state.results = result.get('results', {})
                    
    # 결과가 있으면 표시
    if "results" in st.session_state:
        results = st.session_state.results
        
        # 탭으로 결과 구성
        tab1, tab2, tab3, tab4 = st.tabs(["재무 분석", "포트폴리오", "리스크 분석", "종합 보고서"])
        
        with tab1:
            if "financial_analysis" in results:
                display_financial_analysis(results["financial_analysis"])
        
        with tab2:
            if "portfolio_design" in results:
                display_portfolio_design(results["portfolio_design"])
        
        with tab3:
            if "risk_analysis" in results:
                display_risk_analysis(results["risk_analysis"])
        
        with tab4:
            if "final_report" in results:
                st.markdown(results["final_report"])

