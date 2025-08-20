"""
app.py
Financial Analyst Streamlit 애플리케이션 (AgentCore Runtime 버전)

개인의 재무 상황을 분석하여 투자 성향과 목표 수익률을 계산하는 웹 애플리케이션입니다.
Reflection 패턴을 활용하여 AI가 분석 결과의 품질을 검증하고 신뢰성을 보장합니다.
"""

import streamlit as st
import json
import os
import sys
import boto3
from pathlib import Path

# ================================
# 페이지 설정 및 초기화
# ================================

st.set_page_config(page_title="Financial Analyst")
st.title("💰 Financial Analyst")

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

# ================================
# 데이터 표시 함수들
# ================================

def display_financial_analysis(trace_container, analysis_data):
    """재무 분석 결과 표시 (기존 동작 유지)"""
    sub_col1, sub_col2 = trace_container.columns(2)
    
    with sub_col1:
        st.metric("**위험 성향**", analysis_data["risk_profile"])
        st.markdown("**위험 성향 분석**")
        st.info(analysis_data["risk_profile_reason"])
    
    with sub_col2:
        st.metric("**필요 수익률**", f"{analysis_data['required_annual_return_rate']}%")
        st.markdown("**수익률 분석**")
        st.info(analysis_data["return_rate_reason"])

def display_reflection_result(trace_container, reflection_content):
    """Reflection 분석 결과 표시 (기존 동작 유지)"""
    if reflection_content.strip().lower().startswith("yes"):
        trace_container.success("재무분석 검토 성공")
    else:
        trace_container.error("재무분석 검토 실패")
        if "\n" in reflection_content:
            trace_container.markdown(reflection_content.split("\n")[1])

# ================================
# 메인 처리 함수
# ================================

def invoke_financial_advisor(input_data):
    """AgentCore Runtime 호출 (기존 함수명 및 동작 유지)"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": input_data})
        )

        # 응답을 표시할 컨테이너 생성
        placeholder = st.container()
        placeholder.markdown("🤖 **Financial Analyst (AgentCore)**")

        # SSE 형식 응답 처리
        analysis_data = None
        reflection_result = None

        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])  # "data: " 제거
                    
                    if event_data["type"] == "data":
                        if "analysis_data" in event_data:
                            analysis_data = json.loads(event_data["analysis_data"])
                            # 분석 결과 즉시 표시
                            placeholder.subheader("📌 재무 분석")
                            display_financial_analysis(placeholder, analysis_data)
                            
                        elif "reflection_result" in event_data:
                            reflection_result = event_data["reflection_result"]
                            # Reflection 결과 즉시 표시
                            placeholder.subheader("")
                            placeholder.subheader("📌 재무 분석 검토 (Reflection)")
                            display_reflection_result(placeholder, reflection_result)
                            
                    elif event_data["type"] == "error":
                        return {
                            "status": "error",
                            "error": event_data.get("error", "Unknown error")
                        }
                except json.JSONDecodeError:
                    continue

        return {
            "analysis": analysis_data,
            "reflection_result": reflection_result,
            "status": "success"
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
    ### 🔄 AgentCore Runtime Architecture
    ```
    사용자 입력 → AgentCore Runtime → 재무 분석가 AI → Reflection AI → 최종 결과
    ```
    
    **구성 요소:**
    - **Financial Analyst Agent**: 재무 상황 분석 및 위험 성향 평가
    - **Reflection Agent**: 분석 결과 검증 및 품질 보장
    - **AgentCore Runtime**: AWS 서버리스 실행 환경
    """)

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
    "💰1년 후 목표 금액 (억원 단위)",
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
        "0-1년": 1,
        "1-3년": 2,
        "3-5년": 4,
        "5-10년": 7,
        "10-20년": 15,
        "20년 이상": 25
    }
    experience_years = experience_mapping[stock_investment_experience_years]
    
    input_data = {
        "total_investable_amount": int(total_investable_amount * 100000000),
        "age": age_number,
        "stock_investment_experience_years": experience_years,
        "target_amount": int(target_amount * 100000000),
    }
    
    st.divider()
    
    with st.spinner("AI 분석 중..."):
        try:
            result = invoke_financial_advisor(input_data)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                st.stop()
            
            # 상세 정보
            with st.expander("상세 분석 데이터 보기"):
                st.subheader("📥 입력 데이터")
                st.json(input_data)
                
                st.subheader("📊 완전한 분석 결과")
                st.json(result)
                
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
            