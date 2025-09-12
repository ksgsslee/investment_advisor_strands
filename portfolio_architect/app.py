"""
app.py

Portfolio Architect Streamlit 앱
AI 포트폴리오 설계사 웹 인터페이스
"""

import streamlit as st
import json
import boto3
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Portfolio Architect")
st.title("🤖 Portfolio Architect")

# 배포 정보 로드
try:
    with open(Path(__file__).parent / "deployment_info.json") as f:
        deployment_info = json.load(f)
    AGENT_ARN = deployment_info["agent_arn"]
    REGION = deployment_info["region"]
except Exception:
    st.error("배포 정보를 찾을 수 없습니다. deploy.py를 먼저 실행해주세요.")
    st.stop()

agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)

def extract_json_from_text(text):
    """텍스트에서 JSON 추출"""
    if isinstance(text, dict):
        return text
    if not isinstance(text, str):
        return None
    
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            return None
    return None


def display_portfolio_result(container, portfolio_content):
    """최종 포트폴리오 결과 표시"""
    try:
        data = extract_json_from_text(portfolio_content)
        if not data:
            container.error("포트폴리오 데이터를 찾을 수 없습니다.")
            return
        
        col1, col2 = container.columns(2)
        
        with col1:
            st.markdown("**포트폴리오 배분**")
            fig = go.Figure(data=[go.Pie(
                labels=list(data["portfolio_allocation"].keys()),
                values=list(data["portfolio_allocation"].values()),
                hole=.3,
                textinfo='label+percent'
            )])
            fig.update_layout(height=400)
            st.plotly_chart(fig)
        
        with col2:
            st.markdown("**포트폴리오 구성 근거**")
            st.info(data["reason"])
        
        # Portfolio Scores 표시
        if "portfolio_scores" in data:
            container.markdown("**포트폴리오 평가 점수**")
            scores = data["portfolio_scores"]
            
            col1, col2, col3 = container.columns(3)
            with col1:
                profitability = scores.get("profitability", {})
                st.metric("수익성", f"{profitability.get('score', 'N/A')}/10")
                if profitability.get('reason'):
                    st.caption(profitability['reason'])
            
            with col2:
                risk_mgmt = scores.get("risk_management", {})
                st.metric("리스크 관리", f"{risk_mgmt.get('score', 'N/A')}/10")
                if risk_mgmt.get('reason'):
                    st.caption(risk_mgmt['reason'])
            
            with col3:
                diversification = scores.get("diversification", {})
                st.metric("분산투자 완성도", f"{diversification.get('score', 'N/A')}/10")
                if diversification.get('reason'):
                    st.caption(diversification['reason'])
        

        
    except Exception as e:
        container.error(f"포트폴리오 표시 오류: {e}")

def display_correlation_analysis(container, correlation_data):
    """상관관계 분석 결과 표시"""
    try:
        container.markdown("**🔗 ETF 상관관계 매트릭스**")
        
        correlation_matrix = correlation_data.get('correlation_matrix', {})
        
        if correlation_matrix:
            # 상관관계 매트릭스를 DataFrame으로 변환
            df = pd.DataFrame(correlation_matrix)
            
            # 히트맵으로 표시
            fig = px.imshow(
                df.values,
                x=df.columns,
                y=df.index,
                color_continuous_scale='RdBu_r',
                aspect="auto",
                text_auto=True,
                color_continuous_midpoint=0,
                zmin=-1,
                zmax=1
            )
            
            fig.update_layout(
                title="ETF 간 상관관계 매트릭스",
                height=400,
                xaxis_title="ETF",
                yaxis_title="ETF"
            )
            
            fig.update_traces(texttemplate="%{z:.2f}", textfont_size=12)
            container.plotly_chart(fig, width='stretch')
            
            # 상관관계 해석
            container.markdown("**상관관계 해석**")
            container.info("""
            - **0.7 이상**: 높은 상관관계 (분산투자 효과 제한적)
            - **0.3~0.7**: 중간 상관관계 (적당한 분산투자 효과)
            - **0.3 미만**: 낮은 상관관계 (좋은 분산투자 효과)
            """)
        
    except Exception as e:
        container.error(f"상관관계 분석 표시 오류: {e}")

def display_etf_analysis_result(container, etf_data):
    """개별 ETF 분석 결과 표시"""
    try:
        container.markdown(f"**📊 {etf_data['ticker']} 분석 결과 (몬테카를로 시뮬레이션)**")
        
        # 기본 지표
        col1, col2, col3, col4 = container.columns(4)
        
        with col1:
            st.metric(
                "예상 수익률", 
                f"{etf_data['expected_annual_return']}%"
            )
        
        with col2:
            st.metric(
                "손실 확률", 
                f"{etf_data['loss_probability']}%"
            )
        
        with col3:
            st.metric(
                "변동성", 
                f"{etf_data['volatility']}%"
            )
        
        with col4:
            st.metric(
                "과거 수익률", 
                f"{etf_data['historical_annual_return']}%"
            )
        
        # 수익률 분포 차트
        if 'return_distribution' in etf_data:
            distribution = etf_data['return_distribution']
            ranges = list(distribution.keys())
            counts = list(distribution.values())
            
            fig = go.Figure(data=[
                go.Bar(
                    x=ranges,
                    y=counts,
                    text=[f"{count}회<br>({count/5:.1f}%)" for count in counts],
                    textposition='auto',
                    marker_color='lightblue',
                    name=etf_data['ticker']
                )
            ])
            
            fig.update_layout(
                title=f"1년 후 예상 수익률 분포 (1000회 시뮬레이션)",
                xaxis_title="수익률 구간",
                yaxis_title="시나리오 개수",
                height=400,
                showlegend=False
            )
            
            container.plotly_chart(fig, width='stretch')
        
    except Exception as e:
        container.error(f"ETF 분석 결과 표시 오류: {e}")

def invoke_portfolio_architect(financial_analysis):
    """Portfolio Architect 호출"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": financial_analysis})
        )
        
        placeholder = st.container()
        placeholder.subheader("Reasoning")
        
        current_thinking = ""
        current_text_placeholder = placeholder.empty()
        tool_id_to_name = {}

        for line in response["response"].iter_lines(chunk_size=1):
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
                    actual_tool_name = tool_name.split("___")[-1] if "___" in tool_name else tool_name
                    tool_id_to_name[tool_use_id] = actual_tool_name
                
                elif event_type == "tool_result":
                    tool_use_id = event_data.get("tool_use_id", "")
                    actual_tool_name = tool_id_to_name.get(tool_use_id, "unknown")
                    
                    tool_content = event_data.get("content", [{}])
                    if tool_content and len(tool_content) > 0:
                        result_text = tool_content[0].get("text", "{}")
                        try:
                            body = json.loads(result_text)
                        except:
                            body = result_text
                        
                        if actual_tool_name == "analyze_etf_performance":
                            display_etf_analysis_result(placeholder, body)
                        elif actual_tool_name == "calculate_correlation":
                            display_correlation_analysis(placeholder, body)
                    
                    current_thinking = ""
                    if tool_use_id in tool_id_to_name:
                        del tool_id_to_name[tool_use_id]
                    current_text_placeholder = placeholder.empty()
                
                elif event_type == "streaming_complete":
                    result_str = event_data.get("result", "")
                    
                    # 최종 결과 표시
                    placeholder.divider()
                    placeholder.subheader("📌 포트폴리오 설계 결과")
                    display_portfolio_result(placeholder, result_str)
                    
            except json.JSONDecodeError:
                continue
        
        return {"status": "success"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

# UI 구성
with st.expander("아키텍처", expanded=True):
    st.image("../static/portfolio_architect.png", width=800)

st.markdown("**재무 분석 결과 입력**")

risk_profile = st.text_input("위험 성향", value="공격적")
risk_profile_reason = st.text_input("위험 성향 근거", value="35세, 공격적 투자 성향")
required_return = st.number_input("필요 연간 수익률 (%)", value=40.0)
key_sectors = st.multiselect(
    "추천 투자 분야", 
    options=[
        "기술주 (Technology)", "헬스케어 (Healthcare)", "금융 (Financial)", 
        "소비재 (Consumer)", "에너지 (Energy)", "부동산 (Real Estate)", 
        "유틸리티 (Utilities)", "산업재 (Industrial)", "원자재 (Materials)", 
        "암호화폐 (Cryptocurrency)"
    ],
    default=["기술주 (Technology)", "헬스케어 (Healthcare)"]
)
summary = st.text_area("종합 총평", value="높은 목표 수익률을 위해 공격적 투자 전략이 필요합니다.")

if st.button("분석 시작", width='stretch'):
    financial_analysis = {
        "risk_profile": risk_profile,
        "risk_profile_reason": risk_profile_reason,
        "required_annual_return_rate": required_return,
        "key_sectors": key_sectors,
        "summary": summary
    }
    
    st.divider()
    
    with st.spinner("AI 분석 중..."):
        result = invoke_portfolio_architect(financial_analysis)
        
        if result['status'] == 'error':
            st.error(f"❌ 분석 중 오류: {result.get('error', 'Unknown error')}")