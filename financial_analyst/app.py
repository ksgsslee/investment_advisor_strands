"""
app.py

Financial Analyst Streamlit 애플리케이션
"""

import streamlit as st
import json
import os
import boto3
from pathlib import Path

st.set_page_config(page_title="Financial Analyst")
st.title("💰 Financial Analyst")

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

def display_financial_analysis(trace_container, result):
    """재무 분석 결과 표시"""
    trace_container.markdown("**종합 총평**")
    trace_container.info(result.get("summary", ""))

    col1, col2 = trace_container.columns(2)
    
    with col1:
        st.metric("**위험 성향**", result.get("risk_profile", "N/A"))
        st.markdown("**위험 성향 분석**")
        st.write(result.get("risk_profile_reason", ""))
    
    with col2:
        st.metric("**필요 수익률**", f"{result.get('required_annual_return_rate', 'N/A')}%")
        
        # 추천 투자 섹터를 태그로 표시
        st.markdown("**🎯 추천 투자 섹터**")
        sectors = result.get("key_sectors", [])
        tag_html = ""
        for sector in sectors:
            tag_html += f'<span style="background-color: #e8f5e8; color: #2e7d32; padding: 4px 8px; margin: 2px; border-radius: 12px; font-size: 12px; display: inline-block;">{sector}</span> '
        st.markdown(tag_html, unsafe_allow_html=True)

def display_calculator_result(trace_container, tool_input, result_text):
    """Calculator 도구 결과 표시"""
    trace_container.markdown("**Calculator 도구로 계산된 수익률**")
    trace_container.code(f"Input: {tool_input}\n\n{result_text}", language="text")

def invoke_financial_advisor(input_data):
    """AgentCore Runtime 호출"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": input_data})
        )

        placeholder = st.container()
        placeholder.markdown("🤖 **Financial Analyst**")

        current_thinking = ""
        current_text_placeholder = placeholder.empty()
        tool_id_to_name = {}
        tool_id_to_input = {}

        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    event_type = event_data.get("type")

                    if event_type == "text_chunk":
                        chunk_data = event_data.get("data", "")
                        current_thinking += chunk_data
                        if current_thinking.strip():
                            with current_text_placeholder.chat_message("assistant"):
                                st.markdown(current_thinking)
                    
                    elif event_type == "tool_use":
                        tool_name = event_data.get("tool_name", "")
                        tool_use_id = event_data.get("tool_use_id", "")
                        tool_input = event_data.get("tool_input", "")

                        actual_tool_name = tool_name.split("___")[-1] if "___" in tool_name else tool_name
                        tool_id_to_name[tool_use_id] = actual_tool_name
                        tool_id_to_input[tool_use_id] = tool_input
                    
                    elif event_type == "tool_result":
                        tool_use_id = event_data.get("tool_use_id", "")
                        actual_tool_name = tool_id_to_name.get(tool_use_id, "unknown")
                        tool_input = tool_id_to_input.get(tool_use_id, "unknown")
                        tool_content = event_data.get("content", [{}])
                        
                        if tool_content and len(tool_content) > 0:
                            result_text = tool_content[0].get("text", "{}")
                            
                            if actual_tool_name == "calculator":
                                display_calculator_result(placeholder, tool_input, result_text)
                        
                        current_thinking = ""
                        if tool_use_id in tool_id_to_name:
                            del tool_id_to_name[tool_use_id]
                        current_text_placeholder = placeholder.empty()
                    
                    elif event_type == "streaming_complete":
                        result_str = event_data.get("result", "")
                        result = json.loads(result_str)
                        
                        placeholder.divider()
                        placeholder.subheader("📌 재무 분석 결과")
                        display_financial_analysis(placeholder, result)

                    elif event_type == "error":
                        return {"status": "error", "error": event_data.get("error", "Unknown error")}
                        
                except json.JSONDecodeError:
                    continue

        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "error": str(e)}

# 아키텍처 설명
with st.expander("아키텍처", expanded=True):
    st.image(os.path.join("../static/financial_analyst.png"), width=500)

# 입력 폼
st.markdown("**투자자 정보 입력**")
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
        "암호화폐 (디지털 자산)",
        "글로벌 주식 (해외 분산)",
        "채권 (안전 자산)",
        "원자재/금 (인플레이션 헤지)",
        "ESG/친환경 (지속가능 투자)",
        "인프라/유틸리티 (필수 서비스)"
    ],
    default=["성장주 (기술/바이오)"]
)

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
        "investment_purpose": investment_purpose,
        "preferred_sectors": preferred_sectors
    }
    
    st.divider()
    
    with st.spinner("AI 분석 중..."):
        try:
            result = invoke_financial_advisor(input_data)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                st.stop()
            
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
            