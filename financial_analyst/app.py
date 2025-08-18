import streamlit as st
import json
import os
import sys
import boto3
from pathlib import Path

# 페이지 설정
st.set_page_config(page_title="Financial Analyst")
st.title("🤖 Financial Analyst (AgentCore Version)")

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

def invoke_financial_advisor(input_data):
    """AgentCore Runtime 호출"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": input_data})
        )
        
        # 스트리밍 응답 처리
        if "text/event-stream" in response.get("contentType", ""):
            analysis_data = None
            reflection_result = None
            
            # 프로그레스 바 설정
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            content = []
            for i, line in enumerate(response["response"].iter_lines(chunk_size=1)):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        try:
                            chunk_data = json.loads(data)
                            if not analysis_data and "risk_profile" in str(chunk_data):
                                analysis_data = chunk_data
                                progress_bar.progress(0.5)
                                status_text.text("분석 완료, 검증 중...")
                            elif "reflection_result" in str(chunk_data):
                                reflection_result = chunk_data
                                progress_bar.progress(1.0)
                                status_text.text("검증 완료")
                        except json.JSONDecodeError:
                            content.append(data)
            
            progress_bar.empty()
            status_text.empty()
            
            return {
                "analysis": analysis_data,
                "reflection_result": reflection_result if reflection_result else " ".join(content),
                "status": "success"
            }
        else:
            return {
                "status": "error",
                "error": "스트리밍 응답이 아닙니다."
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

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
    placeholder = st.container()
    
    with st.spinner("AI 분석 중..."):
        try:
            result = invoke_financial_advisor(input_data)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                st.stop()
            
            # 분석 결과 표시
            placeholder.markdown("🤖 **Financial Analyst (AgentCore)**")
            placeholder.subheader("📌 재무 분석")
            
            analysis_data = result['analysis']
            
            # 결과 표시
            sub_col1, sub_col2 = placeholder.columns(2)
            with sub_col1:
                st.metric("**위험 성향**", analysis_data["risk_profile"])
                st.markdown("**위험 성향 분석**")
                st.info(analysis_data["risk_profile_reason"])
            
            with sub_col2:
                st.metric("**필요 수익률**", f"{analysis_data['required_annual_return_rate']}%")
                st.markdown("**수익률 분석**")
                st.info(analysis_data["return_rate_reason"])
            
            # Reflection 결과 표시
            placeholder.subheader("")
            placeholder.subheader("📌 재무 분석 검토 (Reflection)")
            
            reflection_content = result['reflection_result']
            if isinstance(reflection_content, str):
                if reflection_content.strip().lower().startswith("yes"):
                    placeholder.success("재무분석 검토 성공")
                else:
                    placeholder.error("재무분석 검토 실패")
                    lines = reflection_content.strip().split('\n')
                    if len(lines) > 1:
                        placeholder.markdown(lines[1])
            else:
                placeholder.json(reflection_content)
            
            # 상세 정보
            with st.expander("상세 분석 데이터 보기"):
                st.subheader("📥 입력 데이터")
                st.json(input_data)
                
                st.subheader("📊 완전한 분석 결과")
                st.json(result)
                
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
            
            with st.expander("디버깅 정보"):
                st.markdown("""
                ### 🔧 문제 해결 방법
                1. AgentCore Runtime이 정상적으로 배포되었는지 확인하세요
                2. deployment_info.json 파일이 존재하는지 확인하세요
                3. AWS 자격 증명이 올바르게 설정되어 있는지 확인하세요
                4. 인터넷 연결을 확인하세요
                """)
                st.code(f"Error Details: {str(e)}")