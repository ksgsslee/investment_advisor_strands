"""
streamlit_app.py
재무 분석가 + Reflection 패턴 시연 앱 (Strands 버전)
"""
import streamlit as st
import json
import os
import sys

# 상위 디렉토리 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Functions
def display_financial_analysis(trace_container, analysis_data):
    """Display financial analysis results"""
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
    """Display reflection analysis results"""
    if reflection_content.strip().lower().startswith("yes"):
        trace_container.success("재무분석 검토 성공")
    else:
        trace_container.error("재무분석 검토 실패")
        # "no" 다음의 설명 부분 표시
        lines = reflection_content.strip().split('\n')
        if len(lines) > 1:
            trace_container.markdown(lines[1])

# Page setup
st.set_page_config(page_title="Financial Analyst")

st.title("🤖 Financial Analyst (Strands Version)")

with st.expander("아키텍처", expanded=True):
    st.markdown("""
    ### 🔄 Reflection Pattern Architecture
    ```
    사용자 입력 → 재무 분석가 AI → 분석 결과 → Reflection AI → 검증 결과 → 최종 결과
    ```
    
    **구성 요소:**
    - **Financial Analyst Agent**: 재무 상황 분석 및 위험 성향 평가
    - **Reflection Agent**: 분석 결과 검증 및 품질 보장
    - **Strands Framework**: 멀티 에이전트 시스템 조율
    """)

# Input form
st.markdown("**투자자 정보 입력**")
col1, col2, col3 = st.columns(3)

with col1:
    total_investable_amount = st.number_input(
        "💰 투자 가능 금액 (억원 단위)",
        min_value=0.0,
        max_value=1000.0,
        value=0.5,  # 5천만원
        step=0.1,
        format="%.1f"
    )
    st.caption("예: 0.5 = 5천만원")

with col2:
    age_options = [f"{i}-{i+4}세" for i in range(20, 101, 5)]
    age = st.selectbox(
        "나이",
        options=age_options,
        index=3  # 35-39세
    )

with col3:
    experience_categories = ["0-1년", "1-3년", "3-5년", "5-10년", "10-20년", "20년 이상"]
    stock_investment_experience_years = st.selectbox(
        "주식 투자 경험",
        options=experience_categories,
        index=3  # 5-10년
    )

target_amount = st.number_input(
    "💰1년 후 목표 금액 (억원 단위)",
    min_value=0.0,
    max_value=1000.0,
    value=0.7,  # 7천만원
    step=0.1,
    format="%.1f"
)
st.caption("예: 0.7 = 7천만원")

submitted = st.button("분석 시작", use_container_width=True)

if submitted:
    # 나이 범위를 숫자로 변환
    age_number = int(age.split('-')[0]) + 2  # 범위의 중간값
    
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
    
    with st.spinner("AI is processing..."):
        try:
            # Financial Analysis
            placeholder.markdown("🤖 **Financial Analyst (Strands)**")
            placeholder.subheader("📌 재무 분석")
            
            # Strands 재무 분석가 import 및 실행
            from agent import FinancialAnalyst
            analyst = FinancialAnalyst()
            
            result = analyst.analyze(input_data)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                st.stop()
            
            # 분석 결과 표시
            analysis_data = result['analysis']
            display_financial_analysis(placeholder, analysis_data)
            
            # Reflection Analysis
            placeholder.subheader("")
            placeholder.subheader("📌 재무 분석 검토 (Reflection)")
            
            reflection_content = result['reflection_result']
            display_reflection_result(placeholder, reflection_content)
            
            # 상세 정보 (선택적 표시)
            with st.expander("상세 분석 데이터 보기"):
                st.subheader("📥 입력 데이터")
                st.json(input_data)
                
                st.subheader("📊 완전한 분석 결과")
                st.json(result)
                
        except ImportError as e:
            st.error("❌ 필요한 모듈을 찾을 수 없습니다. agent.py 파일이 올바른 위치에 있는지 확인하세요.")
            st.code(f"Import Error: {str(e)}")
            
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
            
            # 디버깅 정보
            with st.expander("디버깅 정보"):
                st.markdown("""
                ### 🔧 문제 해결 방법
                1. `.env` 파일에 `ANTHROPIC_API_KEY`가 올바르게 설정되어 있는지 확인하세요
                2. 필요한 패키지가 모두 설치되어 있는지 확인하세요: `pip install -r requirements.txt`
                3. `agent.py` 파일이 올바른 경로에 있는지 확인하세요
                4. 인터넷 연결을 확인하세요
                """)
                st.code(f"Error Details: {str(e)}")