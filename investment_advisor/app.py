"""
app.py
Investment Advisor Streamlit 애플리케이션 (AgentCore Runtime 버전)

Multi-Agent 패턴 기반 투자 자문 시스템의 웹 인터페이스
3개의 전문 에이전트가 협업하여 종합적인 투자 분석을 제공합니다.
"""

import streamlit as st
import json
import time
import boto3
import plotly.graph_objects as go
from pathlib import Path


def parse_tool_result(result_text):
    """
    도구 실행 결과에서 실제 데이터를 추출하는 함수
    
    Args:
        result_text (str): MCP Server 응답 JSON 문자열
        
    Returns:
        dict: 파싱된 데이터
    """
    try:
        parsed_result = json.loads(result_text)

        start_idx = parsed_result.find('{')
        end_idx = parsed_result.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            try:
                json_str = parsed_result[start_idx:end_idx]
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None
        
        return None
            
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 에러: {e}")
        print(f"원본 텍스트: {result_text}")
        return result_text

# ================================
# 페이지 설정 및 초기화
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

def display_step1_financial_analysis(container, result_data):
    """1단계: 재무 분석 결과 표시"""
    try:
        # result_data = json.loads(result_text)
        if "analysis_data" in result_data:
            analysis_data = json.loads(result_data["analysis_data"])
            reflection_result = result_data.get("reflection_result", "")
            
            with container:
                st.success("✅ **1단계: 재무 분석 완료!**")
                
                sub_col1, sub_col2 = st.columns(2)
                
                with sub_col1:
                    st.metric("**위험 성향**", analysis_data.get("risk_profile", "N/A"))
                    st.markdown("**위험 성향 분석**")
                    st.info(analysis_data.get("risk_profile_reason", ""))
                
                with sub_col2:
                    st.metric("**필요 수익률**", f"{analysis_data.get('required_annual_return_rate', 'N/A')}%")
                    st.markdown("**수익률 분석**")
                    st.info(analysis_data.get("return_rate_reason", ""))
                
                st.markdown("**🔍 분석 검증 결과**")
                if reflection_result.strip().lower().startswith("yes"):
                    st.success("재무분석 검토 성공 - 분석 결과가 검증되었습니다")
                else:
                    st.error("재무분석 검토 실패")
                    if "\n" in reflection_result:
                        st.markdown(reflection_result.split("\n")[1])
                
    except Exception as e:
        with container:
            st.warning(f"재무 분석 결과 파싱 실패: {str(e)}")

def display_step2_portfolio_design(container, result_data):
    """2단계: 포트폴리오 설계 결과 표시"""
    try:
        # result_data = json.loads(result_text)
        if "portfolio_result" in result_data:
            portfolio = json.loads(result_data["portfolio_result"])
            
            with container:
                st.success("✅ **2단계: 포트폴리오 설계 완료!**")
                
                if "portfolio_allocation" in portfolio:
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown("**📊 추천 포트폴리오 구성**")
                        for etf, ratio in portfolio["portfolio_allocation"].items():
                            st.metric(f"**{etf}**", f"{ratio}%")
                    
                    with col2:
                        fig = create_pie_chart(
                            portfolio["portfolio_allocation"], 
                            "포트폴리오 배분"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("**💡 투자 전략**")
                    st.info(portfolio.get("strategy", ""))
                    
                    st.markdown("**📝 구성 근거**")
                    st.info(portfolio.get("reason", ""))
                
    except Exception as e:
        with container:
            st.warning(f"포트폴리오 결과 파싱 실패: {str(e)}")

def display_step3_risk_analysis(container, result_data):
    """3단계: 리스크 분석 결과 표시"""
    try:
        # result_data = json.loads(result_text)
        if "risk_result" in result_data:
            risk = json.loads(result_data["risk_result"])
            
            with container:
                st.success("✅ **3단계: 리스크 분석 완료!**")
                
                st.markdown("**⚠️ 시나리오별 리스크 분석**")
                
                col1, col2 = st.columns(2)
                
                if "scenario1" in risk:
                    with col1:
                        st.markdown("### 📈 시나리오 1")
                        st.markdown(f"**{risk['scenario1'].get('name', 'N/A')}**")
                        st.info(risk['scenario1'].get('description', ''))
                        
                        if "allocation_management" in risk['scenario1']:
                            st.markdown("**조정된 포트폴리오:**")
                            for etf, ratio in risk['scenario1']['allocation_management'].items():
                                st.write(f"• **{etf}**: {ratio}%")
                            
                            st.markdown("**조정 이유:**")
                            st.write(risk['scenario1'].get('reason', ''))
                
                if "scenario2" in risk:
                    with col2:
                        st.markdown("### 📉 시나리오 2")
                        st.markdown(f"**{risk['scenario2'].get('name', 'N/A')}**")
                        st.info(risk['scenario2'].get('description', ''))
                        
                        if "allocation_management" in risk['scenario2']:
                            st.markdown("**조정된 포트폴리오:**")
                            for etf, ratio in risk['scenario2']['allocation_management'].items():
                                st.write(f"• **{etf}**: {ratio}%")
                            
                            st.markdown("**조정 이유:**")
                            st.write(risk['scenario2'].get('reason', ''))
                
    except Exception as e:
        with container:
            st.warning(f"리스크 분석 결과 파싱 실패: {str(e)}")

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
        
        # UI 컨테이너 설정
        placeholder = st.container()
        placeholder.subheader("Bedrock Reasoning")

        # SSE 형식 응답 처리 (채팅 스타일)
        current_thinking = ""
        current_text_placeholder = placeholder.empty()
        tool_id_to_name = {}  # tool_use_id와 tool_name 매핑
        
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])  # "data: " 제거
                    event_type = event_data.get("type")
                    
                    if event_type == "text_chunk":
                        # AI 생각 과정을 실시간으로 표시
                        chunk_data = event_data.get("data", "")
                        current_thinking += chunk_data
                        
                        if current_thinking.strip():
                            with current_text_placeholder.chat_message("assistant"):
                                st.markdown(current_thinking)
                    
                    elif event_type == "tool_use":
                        # 도구 사용 시작 - 매핑 정보 저장
                        tool_name = event_data.get("tool_name", "")
                        tool_use_id = event_data.get("tool_use_id", "")
                        
                        # 실제 함수명 추출 (target-portfolio-architect___get_available_products -> get_available_products)
                        actual_tool_name = tool_name.split("___")[-1] if "___" in tool_name else tool_name
                        tool_id_to_name[tool_use_id] = actual_tool_name

                        current_text_placeholder = placeholder.empty()
                    
                    elif event_type == "tool_result":
                        # 도구 실행 결과 처리
                        tool_use_id = event_data.get("tool_use_id", "")
                        actual_tool_name = tool_id_to_name.get(tool_use_id, "unknown")
                        
                        tool_content = event_data.get("content", [{}])
                        if tool_content and len(tool_content) > 0:
                            result_text = tool_content[0].get("text", "{}")
                            body = json.loads(result_text)
                            
                            # 도구 타입에 따라 적절한 표시 함수 호출
                            if actual_tool_name == "financial_analyst_tool":
                                display_step1_financial_analysis(placeholder, body)
                            elif actual_tool_name == "portfolio_architect_tool":
                                display_step2_portfolio_design(placeholder, body)
                            elif actual_tool_name == "risk_analysis_tool":
                                display_step3_risk_analysis(placeholder, body)

                    elif event_type == "streaming_complete":
                        # 최종 완료 메시지
                        break
                            
                    elif event_type == "error":
                        return {
                            "status": "error",
                            "error": event_data.get("error", "Unknown error")
                        }
                except json.JSONDecodeError:
                    continue
        
        return {
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
        
        # 첫 인사 메시지 추가
        st.session_state.messages.append({
            "role": "assistant", 
            "content": f"안녕하세요! 투자 상담을 시작하겠습니다.\n\n**입력하신 정보:**\n- 투자 가능 금액: {total_investable_amount}억원\n- 나이: {age}\n- 투자 경험: {stock_investment_experience_years}\n- 목표 금액: {target_amount}억원\n\n어떤 도움이 필요하신가요? 전체 분석을 원하시면 '전체 분석해줘'라고 말씀해주세요."
        })
        st.rerun()

else:
    # 대화 인터페이스
    st.markdown("### 💬 AI 투자 상담사와 대화하기")
    
    # 사용자 정보 표시 (사이드바)
    with st.sidebar:
        st.header("📊 투자자 정보")
        st.write(f"💰 투자금액: {st.session_state.user_info['total_investable_amount'] / 100000000:.1f}억원")
        st.write(f"👤 나이: {st.session_state.user_info['age']}세")
        st.write(f"📈 경험: {st.session_state.user_info['stock_investment_experience_years']}년")
        st.write(f"🎯 목표금액: {st.session_state.user_info['target_amount'] / 100000000:.1f}억원")
        
        if st.button("🔄 정보 다시 입력"):
            st.session_state.user_info = None
            st.session_state.messages = []
            st.rerun()
    
    # 대화 히스토리 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 사용자 입력
    if prompt := st.chat_input("투자 관련 질문을 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # AI 응답 생성
        with st.chat_message("assistant"):
            try:
                # 전체 대화 컨텍스트 준비
                conversation_context = {
                    "user_info": st.session_state.user_info,
                    "messages": st.session_state.messages,
                    "current_question": prompt
                }
                
                with st.spinner("AI가 분석 중입니다..."):
                    result = invoke_investment_advisor(conversation_context)
                    
                    if result['status'] == 'error':
                        error_msg = f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    else:
                        success_msg = "✅ 분석이 완료되었습니다! 위의 결과를 확인해보세요."
                        st.success(success_msg)
                        st.session_state.messages.append({"role": "assistant", "content": success_msg})
                        
            except Exception as e:
                error_msg = f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# 사이드바 - 상담 히스토리
if st.session_state.user_info is not None:
    with st.sidebar:
        st.header("📋 상담 히스토리")
        if st.button("Memory 조회"):
            try:
                from bedrock_agentcore.memory import MemoryClient
                memory_client = MemoryClient(region_name=REGION)
                
                memories = memory_client.list_memories()
                if memories:
                    st.success(f"총 {len(memories)}개 메모리")
                    for memory in memories[:3]:
                        st.text(memory.get('name', 'Unknown'))
                else:
                    st.info("저장된 히스토리 없음")
            except Exception as e:
                st.error(f"조회 실패: {str(e)}")