"""
app.py
Investment Advisor Streamlit 애플리케이션

AgentCore Memory 기반 Multi-Agent 투자 자문 시스템의 웹 인터페이스
"""

import streamlit as st
import json
import boto3
import plotly.graph_objects as go
from pathlib import Path
from bedrock_agentcore.memory import MemoryClient

# ================================
# 페이지 설정
# ================================

st.set_page_config(page_title="Investment Advisor", layout="wide")
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

# 클라이언트 설정
agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)
memory_client = MemoryClient(region_name=REGION)

# ================================
# 유틸리티 함수
# ================================

def create_pie_chart(allocation_data, chart_title=""):
    """포트폴리오 배분 파이 차트 생성"""
    fig = go.Figure(data=[go.Pie(
        labels=list(allocation_data.keys()),
        values=list(allocation_data.values()),
        hole=.3,
        textinfo='label+percent'
    )])
    fig.update_layout(title=chart_title, showlegend=True, width=400, height=400)
    return fig

def invoke_investment_advisor(input_data, user_id=None, memory_id=None):
    """AgentCore Runtime 호출"""
    try:
        payload = {"input_data": input_data}
        if user_id:
            payload["user_id"] = user_id
        if memory_id:
            payload["memory_id"] = memory_id
            
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps(payload)
        )

        # 응답 처리
        placeholder = st.container()
        placeholder.markdown("🤖 **Investment Advisor (Multi-Agent + Memory)**")
        
        current_text = ""
        session_id = None
        memory_id = None

        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    
                    if event_data.get("type") == "data":
                        current_text += event_data.get("data", "")
                        with placeholder.chat_message("assistant"):
                            st.markdown(current_text)
                    
                    elif event_data.get("type") == "result":
                        session_id = event_data.get("session_id")
                        memory_id = event_data.get("memory_id")
                        break
                        
                except json.JSONDecodeError:
                    continue

        return {
            "status": "success",
            "session_id": session_id,
            "memory_id": memory_id,
            "response": current_text
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}

# ================================
# UI 구성
# ================================

# 아키텍처 설명
with st.expander("시스템 아키텍처", expanded=False):
    st.markdown("""
    ### 🔄 Multi-Agent + Memory Architecture
    ```
    사용자 입력 → Financial Analyst → Portfolio Architect → Risk Manager → 종합 리포트 → Memory 저장
    ```
    
    **주요 특징:**
    - **Multi-Agent**: 3개 전문 에이전트 협업
    - **AgentCore Memory**: 상담 히스토리 자동 저장 및 조회
    - **실시간 스트리밍**: AI 사고 과정 실시간 표시
    """)

# 사용자 설정
col1, col2 = st.columns(2)
with col1:
    user_id = st.text_input("사용자 ID", value="user123", help="상담 히스토리 관리용")
with col2:
    memory_id = st.text_input("메모리 ID (선택사항)", help="기존 메모리 사용 시")

# 투자자 정보 입력
st.markdown("**투자자 정보 입력**")
col1, col2, col3 = st.columns(3)

with col1:
    total_investable_amount = st.number_input(
        "💰 투자 가능 금액 (억원)",
        min_value=0.0, max_value=1000.0, value=0.5, step=0.1, format="%.1f"
    )

with col2:
    age_options = [f"{i}-{i+4}세" for i in range(20, 101, 5)]
    age = st.selectbox("나이", options=age_options, index=3)

with col3:
    experience_categories = ["0-1년", "1-3년", "3-5년", "5-10년", "10-20년", "20년 이상"]
    stock_investment_experience_years = st.selectbox("주식 투자 경험", options=experience_categories, index=3)

target_amount = st.number_input(
    "💰 1년 후 목표 금액 (억원)",
    min_value=0.0, max_value=1000.0, value=0.7, step=0.1, format="%.1f"
)

# 상담 실행
if st.button("🚀 종합 투자 자문 시작", use_container_width=True):
    # 입력 데이터 변환
    age_number = int(age.split('-')[0]) + 2
    experience_mapping = {"0-1년": 1, "1-3년": 2, "3-5년": 4, "5-10년": 7, "10-20년": 15, "20년 이상": 25}
    experience_years = experience_mapping[stock_investment_experience_years]
    
    input_data = {
        "total_investable_amount": int(total_investable_amount * 100000000),
        "age": age_number,
        "stock_investment_experience_years": experience_years,
        "target_amount": int(target_amount * 100000000),
    }
    
    st.divider()
    
    with st.spinner("AI 종합 분석 중..."):
        try:
            result = invoke_investment_advisor(
                input_data, 
                user_id if user_id else None,
                memory_id if memory_id else None
            )
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류: {result.get('error')}")
            else:
                st.success("🎉 투자 상담 완료!")
                if result.get('session_id'):
                    st.info(f"📝 세션 ID: {result['session_id']}")
                if result.get('memory_id'):
                    st.info(f"💾 메모리 ID: {result['memory_id']}")
                    
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류: {str(e)}")

# 상담 히스토리 조회
if user_id:
    st.divider()
    st.markdown("### 📊 상담 히스토리")
    
    if st.button("히스토리 조회"):
        try:
            # 메모리에서 과거 상담 조회 (간단 버전)
            memories = memory_client.list_memories()
            if memories:
                st.success(f"총 {len(memories)}개의 메모리 발견")
                for memory in memories[:5]:  # 최근 5개만 표시
                    with st.expander(f"메모리: {memory.get('name', 'Unknown')}"):
                        st.json(memory)
            else:
                st.info("저장된 상담 히스토리가 없습니다.")
        except Exception as e:
            st.error(f"히스토리 조회 실패: {str(e)}")