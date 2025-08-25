"""
app.py
Investment Advisor Orchestrator Streamlit 애플리케이션

Agents as Tools 패턴을 활용한 AI 투자 자문 오케스트레이터 웹 애플리케이션입니다.
사용자의 재무 정보를 입력받아 전문 에이전트들을 순차적으로 조율하여
완전한 투자 자문 서비스를 제공합니다.
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

# ================================
# 페이지 설정 및 초기화
# ================================

st.set_page_config(
    page_title="Investment Advisor Orchestrator",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Investment Advisor Orchestrator")
st.markdown("**Agents as Tools 패턴을 활용한 종합 투자 자문 서비스**")

# 배포 정보 로드
CURRENT_DIR = Path(__file__).parent.resolve()
try:
    with open(CURRENT_DIR / "deployment_info.json", "r") as f:
        deployment_info = json.load(f)
    AGENT_ARN = deployment_info["agent_arn"]
    REGION = deployment_info["region"]
    SPECIALIST_AGENTS = deployment_info["specialist_agents"]
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

def create_pie_chart(allocation_data, chart_title=""):
    """
    포트폴리오 배분을 위한 파이 차트 생성
    
    Args:
        allocation_data (dict): 자산 배분 데이터
        chart_title (str): 차트 제목
        
    Returns:
        plotly.graph_objects.Figure: 파이 차트
    """
    try:
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
    except Exception as e:
        st.error(f"파이 차트 생성 오류: {str(e)}")
        return None

# ================================
# 데이터 표시 함수들
# ================================

def display_tool_usage(container, tool_name, tool_input, tool_result):
    """
    전문 에이전트 도구 사용 과정을 표시
    
    Args:
        container: Streamlit 컨테이너
        tool_name (str): 도구 이름
        tool_input (dict): 도구 입력
        tool_result (str): 도구 실행 결과
    """
    # 도구별 아이콘 및 제목 설정
    tool_info = {
        "financial_analyst_tool": {
            "icon": "📊",
            "title": "Financial Analyst",
            "description": "개인 재무 분석 및 위험 성향 평가"
        },
        "portfolio_architect_tool": {
            "icon": "🤖", 
            "title": "Portfolio Architect",
            "description": "실시간 데이터 기반 포트폴리오 설계"
        },
        "risk_manager_tool": {
            "icon": "⚠️",
            "title": "Risk Manager", 
            "description": "뉴스 기반 리스크 분석 및 시나리오 플래닝"
        }
    }
    
    info = tool_info.get(tool_name, {"icon": "🔧", "title": tool_name, "description": "전문 에이전트"})
    
    with container.expander(f"{info['icon']} {info['title']} - {info['description']}", expanded=True):
        
        # 입력 데이터 표시 (간소화)
        st.markdown("**입력 데이터:**")
        if isinstance(tool_input, dict) and len(str(tool_input)) > 200:
            st.text("📋 재무 정보 및 분석 데이터 (상세 내용 생략)")
        else:
            st.json(tool_input)
        
        # 결과 데이터 표시
        st.markdown("**실행 결과:**")
        try:
            result_data = json.loads(tool_result)
            
            # Financial Analyst 결과 표시
            if tool_name == "financial_analyst_tool" and "risk_profile" in result_data:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("위험 성향", result_data["risk_profile"])
                with col2:
                    st.metric("목표 수익률", f"{result_data['required_annual_return_rate']}%")
                
                st.info(f"**분석 근거:** {result_data.get('risk_profile_reason', '')}")
            
            # Portfolio Architect 결과 표시
            elif tool_name == "portfolio_architect_tool" and "portfolio_allocation" in result_data:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    fig = create_pie_chart(
                        result_data["portfolio_allocation"],
                        "추천 포트폴리오"
                    )
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**투자 전략**")
                    st.info(result_data.get("strategy", ""))
            
            # Risk Manager 결과 표시
            elif tool_name == "risk_manager_tool" and "scenario1" in result_data:
                for i, scenario_key in enumerate(["scenario1", "scenario2"], 1):
                    if scenario_key in result_data:
                        scenario = result_data[scenario_key]
                        
                        st.markdown(f"**시나리오 {i}: {scenario.get('name', '')}**")
                        
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            allocation = scenario.get('allocation_management', {})
                            if allocation:
                                fig = create_pie_chart(
                                    allocation,
                                    f"시나리오 {i} 조정 포트폴리오"
                                )
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.markdown("**시나리오 설명**")
                            st.write(scenario.get('description', ''))
                            st.markdown("**조정 근거**")
                            st.info(scenario.get('reason', ''))
            
            # 기본 JSON 표시
            else:
                st.json(result_data)
                
        except json.JSONDecodeError:
            st.text(tool_result)

def display_final_report(container, final_content):
    """
    최종 투자 자문 보고서를 표시
    
    Args:
        container: Streamlit 컨테이너
        final_content (str): 최종 보고서 내용
    """
    container.markdown("---")
    container.markdown("## 📋 최종 투자 자문 보고서")
    
    # 마크다운 형태의 보고서를 그대로 표시
    container.markdown(final_content)

# ================================
# 메인 처리 함수
# ================================

def invoke_investment_advisor_orchestrator(user_request):
    """
    Investment Advisor Orchestrator 호출
    
    Args:
        user_request (dict): 사용자 투자 자문 요청
        
    Returns:
        dict: 실행 결과
    """
    try:
        # AgentCore Runtime 호출
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"user_request": user_request})
        )
        
        # UI 컨테이너 설정
        placeholder = st.container()
        placeholder.markdown("## 🎯 Investment Advisor Orchestrator")
        placeholder.markdown("**전문 에이전트들을 조율하여 종합적인 투자 자문을 제공합니다**")
        
        # 상태 변수 초기화
        current_thinking = ""
        current_text_placeholder = placeholder.empty()
        tool_usage_data = {}  # tool_use_id별 데이터 저장
        
        # 스트리밍 응답 처리
        for line in response["response"].iter_lines(chunk_size=1):
            if not line or not line.decode("utf-8").startswith("data: "):
                continue
                
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
                    # 도구 사용 시작 - 정보 저장
                    tool_name = event_data.get("tool_name", "")
                    tool_use_id = event_data.get("tool_use_id", "")
                    tool_input = event_data.get("tool_input", {})
                    
                    tool_usage_data[tool_use_id] = {
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_result": None
                    }
                
                elif event_type == "tool_result":
                    # 도구 실행 결과 처리
                    tool_use_id = event_data.get("tool_use_id", "")
                    tool_content = event_data.get("content", [{}])
                    
                    if tool_use_id in tool_usage_data and tool_content:
                        tool_result = tool_content[0].get("text", "")
                        tool_usage_data[tool_use_id]["tool_result"] = tool_result
                        
                        # 도구 사용 과정 표시
                        tool_data = tool_usage_data[tool_use_id]
                        display_tool_usage(
                            placeholder,
                            tool_data["tool_name"],
                            tool_data["tool_input"], 
                            tool_data["tool_result"]
                        )
                    
                    # 생각 텍스트 리셋 및 새로운 placeholder 생성
                    current_thinking = ""
                    current_text_placeholder = placeholder.empty()
                
                elif event_type == "streaming_complete":
                    # 마지막 AI 생각 표시 후 완료
                    if current_thinking.strip():
                        display_final_report(placeholder, current_thinking.strip())
                    break
                    
            except json.JSONDecodeError:
                continue
        
        return {
            "status": "success",
            "final_report": current_thinking
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
with st.expander("🏗️ 시스템 아키텍처", expanded=True):
    st.markdown("""
    ### 🔄 Agents as Tools Pattern Architecture
    ```
    사용자 입력 → Investment Advisor Orchestrator → 전문 에이전트들 → 종합 투자 자문
    ```
    
    **구성 요소:**
    - **🎯 Investment Advisor Orchestrator**: 전문 에이전트들을 조율하는 메인 오케스트레이터
    - **📊 Financial Analyst**: 개인 재무 분석 및 위험 성향 평가 (Reflection 패턴)
    - **🤖 Portfolio Architect**: 실시간 데이터 기반 포트폴리오 설계 (Tool Use 패턴)
    - **⚠️ Risk Manager**: 뉴스 기반 리스크 분석 및 시나리오 플래닝 (Planning 패턴)
    
    **워크플로우:**
    1. 사용자 재무 정보 → Financial Analyst (재무 분석)
    2. 재무 분석 결과 → Portfolio Architect (포트폴리오 설계)
    3. 포트폴리오 결과 → Risk Manager (리스크 분석)
    4. 모든 결과 종합 → 최종 투자 자문 보고서
    """)

# 전문 에이전트 상태 표시
with st.expander("🤖 전문 에이전트 상태", expanded=False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📊 Financial Analyst**")
        st.success("✅ 배포됨")
        st.caption(f"ARN: ...{SPECIALIST_AGENTS['FINANCIAL_ANALYST_ARN'][-20:]}")
    
    with col2:
        st.markdown("**🤖 Portfolio Architect**")
        st.success("✅ 배포됨")
        st.caption(f"ARN: ...{SPECIALIST_AGENTS['PORTFOLIO_ARCHITECT_ARN'][-20:]}")
    
    with col3:
        st.markdown("**⚠️ Risk Manager**")
        st.success("✅ 배포됨")
        st.caption(f"ARN: ...{SPECIALIST_AGENTS['RISK_MANAGER_ARN'][-20:]}")

# 입력 폼
st.markdown("---")
st.markdown("## 📝 투자자 정보 입력")

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
        "👤 나이",
        options=age_options,
        index=3
    )

with col3:
    experience_categories = ["0-1년", "1-3년", "3-5년", "5-10년", "10-20년", "20년 이상"]
    stock_investment_experience_years = st.selectbox(
        "📈 주식 투자 경험",
        options=experience_categories,
        index=3
    )

target_amount = st.number_input(
    "🎯 1년 후 목표 금액 (억원 단위)",
    min_value=0.0,
    max_value=1000.0,
    value=0.7,
    step=0.1,
    format="%.1f"
)
st.caption("예: 0.7 = 7천만원")

# 추가 요구사항 (선택사항)
additional_requirements = st.text_area(
    "📋 추가 요구사항 (선택사항)",
    placeholder="예: ESG 투자 선호, 특정 섹터 제외, 배당 중시 등",
    height=100
)

submitted = st.button("🚀 종합 투자 자문 시작", use_container_width=True, type="primary")

# 메인 실행 로직
if submitted:
    # 나이 범위를 숫자로 변환
    age_number = int(age.split('-')[0]) + 2
    
    # 경험 년수를 숫자로 변환
    experience_mapping = {
        "0-1년": 1,
        "1-3년": 2,
        "3-5년": 4,
        "5-10년": 7,
        "10-20년": 15,
        "20년 이상": 25
    }
    experience_years = experience_mapping[stock_investment_experience_years]
    
    # 사용자 요청 구성
    user_request = {
        "user_financial_data": {
            "total_investable_amount": int(total_investable_amount * 100000000),
            "age": age_number,
            "stock_investment_experience_years": experience_years,
            "target_amount": int(target_amount * 100000000),
        }
    }
    
    # 추가 요구사항이 있으면 포함
    if additional_requirements.strip():
        user_request["additional_requirements"] = additional_requirements.strip()
    
    st.divider()
    
    with st.spinner("🎯 AI 투자 자문 오케스트레이터 실행 중..."):
        try:
            result = invoke_investment_advisor_orchestrator(user_request)
            
            if result['status'] == 'error':
                st.error(f"❌ 투자 자문 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
            else:
                st.success("✅ 종합 투자 자문이 완료되었습니다!")
                
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🎯 Investment Advisor Orchestrator | Agents as Tools Pattern</p>
    <p>Powered by AWS Bedrock AgentCore & Strands Agents SDK</p>
</div>
""", unsafe_allow_html=True)