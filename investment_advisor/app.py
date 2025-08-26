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

def display_step1_financial_analysis(container, result_text):
    """1단계: 재무 분석 결과 표시"""
    try:
        result_data = json.loads(result_text)
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

def display_step2_portfolio_design(container, result_text):
    """2단계: 포트폴리오 설계 결과 표시"""
    try:
        result_data = json.loads(result_text)
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

def display_step3_risk_analysis(container, result_text):
    """3단계: 리스크 분석 결과 표시"""
    try:
        result_data = json.loads(result_text)
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
        placeholder.subheader("🤖 AI 투자 상담사와의 대화")
        
        # 단계별 결과 컨테이너
        st.subheader("📊 단계별 분석 결과")
        step1_container = st.container()
        step2_container = st.container() 
        step3_container = st.container()
        
        # 상태 변수 초기화
        current_thinking = ""
        current_text_placeholder = placeholder.empty()
        tool_results = {}
        
        # 스트리밍 응답 처리
        for line in response["response"].iter_lines(chunk_size=1):
            if not line:
                continue
                
            try:
                line_str = line.decode("utf-8")
                
                if line_str.startswith("data: "):
                    data_content = line_str[6:]
                    
                    # JSON 형태와 문자열 형태 모두 처리
                    try:
                        # 먼저 JSON으로 파싱 시도
                        event_data = json.loads(data_content)
                    except json.JSONDecodeError:
                        # JSON 파싱 실패시 문자열로 eval 시도
                        try:
                            if data_content.startswith("'") and data_content.endswith("'"):
                                import ast
                                event_data = ast.literal_eval(data_content)
                            else:
                                continue
                        except:
                            continue
                else:
                    try:
                        event_data = json.loads(line_str)
                    except:
                        continue
                
                if not isinstance(event_data, dict):
                    continue
                
                # AI 대화 텍스트 스트리밍 - 여러 방법으로 텍스트 추출
                text_chunk = None
                
                # 방법 1: 직접 data 필드에서 텍스트 추출
                if "data" in event_data and isinstance(event_data["data"], str):
                    text_chunk = event_data["data"]
                
                # 방법 2: event.contentBlockDelta.delta.text에서 텍스트 추출
                elif "event" in event_data and isinstance(event_data["event"], dict):
                    event_obj = event_data["event"]
                    if "contentBlockDelta" in event_obj:
                        delta = event_obj["contentBlockDelta"].get("delta", {})
                        if "text" in delta:
                            text_chunk = delta["text"]
                
                # 방법 3: delta.text에서 직접 추출
                elif "delta" in event_data and isinstance(event_data["delta"], dict):
                    if "text" in event_data["delta"]:
                        text_chunk = event_data["delta"]["text"]
                
                # 텍스트 청크가 있으면 실시간 업데이트
                if text_chunk:
                    current_thinking += text_chunk
                    
                    if current_thinking.strip():
                        with current_text_placeholder.chat_message("assistant"):
                            st.markdown(current_thinking)
                
                # 도구 시작 감지 (contentBlockStart)
                elif "event" in event_data and isinstance(event_data["event"], dict):
                    event_obj = event_data["event"]
                    if "contentBlockStart" in event_obj:
                        start_info = event_obj["contentBlockStart"].get("start", {})
                        if "toolUse" in start_info:
                            tool_name = start_info["toolUse"].get("name", "")
                            
                            if "financial_analyst" in tool_name:
                                with step1_container:
                                    st.info("🔍 **1단계: 재무 분석 실행 중...** 고객님의 재무 상황을 분석하고 있습니다.")
                                current_thinking = ""
                                current_text_placeholder = placeholder.empty()
                            elif "portfolio_architect" in tool_name:
                                with step2_container:
                                    st.info("📊 **2단계: 포트폴리오 설계 실행 중...** 맞춤형 투자 포트폴리오를 설계하고 있습니다.")
                                current_thinking = ""
                                current_text_placeholder = placeholder.empty()
                            elif "risk_manager" in tool_name:
                                with step3_container:
                                    st.info("⚠️ **3단계: 리스크 분석 실행 중...** 시장 리스크를 분석하고 시나리오를 도출하고 있습니다.")
                                current_thinking = ""
                                current_text_placeholder = placeholder.empty()
                
                # 도구 사용 및 결과 처리
                elif "message" in event_data:
                    message = event_data["message"]
                    
                    # Assistant 메시지: 도구 사용 시작
                    if message.get("role") == "assistant":
                        for content in message.get("content", []):
                            if "toolUse" in content:
                                tool_name = content["toolUse"].get("name", "")
                                
                                if "financial_analyst" in tool_name:
                                    with step1_container:
                                        st.info("🔍 **1단계: 재무 분석 실행 중...** 고객님의 재무 상황을 분석하고 있습니다.")
                                elif "portfolio_architect" in tool_name:
                                    with step2_container:
                                        st.info("📊 **2단계: 포트폴리오 설계 실행 중...** 맞춤형 투자 포트폴리오를 설계하고 있습니다.")
                                elif "risk_manager" in tool_name:
                                    with step3_container:
                                        st.info("⚠️ **3단계: 리스크 분석 실행 중...** 시장 리스크를 분석하고 시나리오를 도출하고 있습니다.")
                    
                    # User 메시지: 도구 결과
                    elif message.get("role") == "user":
                        for content in message.get("content", []):
                            if "toolResult" in content:
                                tool_result = content["toolResult"]
                                result_content = tool_result.get("content", [])
                                
                                if result_content and len(result_content) > 0:
                                    result_text = result_content[0].get("text", "")
                                    
                                    if "financial_analyst" in str(tool_result):
                                        tool_results["financial_analysis"] = result_text
                                        display_step1_financial_analysis(step1_container, result_text)
                                    elif "portfolio_architect" in str(tool_result):
                                        tool_results["portfolio_design"] = result_text
                                        display_step2_portfolio_design(step2_container, result_text)
                                    elif "risk_manager" in str(tool_result):
                                        tool_results["risk_analysis"] = result_text
                                        display_step3_risk_analysis(step3_container, result_text)
                                
                                current_thinking = ""
                                current_text_placeholder = placeholder.empty()
                
                # 최종 결과 처리
                elif "result" in event_data:
                    if current_thinking.strip():
                        with current_text_placeholder.chat_message("assistant"):
                            st.markdown(current_thinking)
                    st.success("🎉 **투자 상담이 완료되었습니다!** 모든 분석 결과를 확인해보세요.")
                    break
                    
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
        
        return {
            "status": "success",
            "tool_results": tool_results
        }
        
    except Exception as e:
        st.error(f"❌ AgentCore Runtime 호출 오류: {str(e)}")
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

# 투자자 정보 입력
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

submitted = st.button("🚀 Multi-Agent 투자 상담 시작", use_container_width=True)

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
    
    with st.spinner("Multi-Agent AI 분석 중..."):
        try:
            result = invoke_investment_advisor(input_data)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                st.stop()
            
            # 성공 시 최종 요약 표시
            if result.get('tool_results'):
                st.balloons()
                st.success("🎉 **Multi-Agent 투자 상담이 완료되었습니다!**")
                
                # 최종 요약 탭
                st.header("📋 투자 상담 최종 요약")
                tab1, tab2, tab3 = st.tabs(["🔍 1단계: 재무분석", "📊 2단계: 포트폴리오", "⚠️ 3단계: 리스크분석"])
                
                with tab1:
                    if "financial_analysis" in result['tool_results']:
                        display_step1_financial_analysis(st.container(), result['tool_results']["financial_analysis"])
                
                with tab2:
                    if "portfolio_design" in result['tool_results']:
                        display_step2_portfolio_design(st.container(), result['tool_results']["portfolio_design"])
                
                with tab3:
                    if "risk_analysis" in result['tool_results']:
                        display_step3_risk_analysis(st.container(), result['tool_results']["risk_analysis"])
                
                # 다운로드 기능
                st.divider()
                download_data = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "input_data": input_data,
                    "results": result['tool_results']
                }
                st.download_button(
                    label="📥 상담 결과 다운로드 (JSON)",
                    data=json.dumps(download_data, ensure_ascii=False, indent=2),
                    file_name=f"investment_consultation_{int(time.time())}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")

# 사이드바 - 상담 히스토리
st.sidebar.header("📊 상담 히스토리")
if st.sidebar.button("Memory 조회"):
    try:
        from bedrock_agentcore.memory import MemoryClient
        memory_client = MemoryClient(region_name=REGION)
        
        memories = memory_client.list_memories()
        if memories:
            st.sidebar.success(f"총 {len(memories)}개 메모리")
            for memory in memories[:3]:
                st.sidebar.text(memory.get('name', 'Unknown'))
        else:
            st.sidebar.info("저장된 히스토리 없음")
    except Exception as e:
        st.sidebar.error(f"조회 실패: {str(e)}")