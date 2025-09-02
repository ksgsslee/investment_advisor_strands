"""
app.py

Risk Manager Streamlit 앱
AI 리스크 관리사 웹 인터페이스
"""

import streamlit as st
import json
import boto3
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Risk Manager")
st.title("⚠️ Risk Manager")

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

def parse_tool_result(result_text):
    """도구 실행 결과에서 실제 데이터 추출"""
    parsed_result = json.loads(result_text)
    return parsed_result["response"]["payload"]["body"]

def display_news_data(container, news_data):
    """ETF 뉴스 데이터 표시"""
    try:
        if isinstance(news_data, str):
            data = json.loads(news_data)
        else:
            data = news_data
        
        ticker = data.get('ticker', 'Unknown')
        news_list = data.get('news', [])
        
        if not news_list:
            container.warning(f"{ticker}: 뉴스 데이터가 없습니다.")
            return
        
        container.markdown(f"**📰 {ticker} 최신 뉴스**")
        
        news_df = pd.DataFrame(news_list)
        if not news_df.empty and all(col in news_df.columns for col in ['publish_date', 'title', 'summary']):
            container.dataframe(
                news_df[['publish_date', 'title', 'summary']],
                hide_index=True,
                use_container_width=True
            )
        else:
            for i, news_item in enumerate(news_list[:5], 1):
                with container.expander(f"{i}. {news_item.get('title', 'No Title')}"):
                    st.write(f"**발행일:** {news_item.get('publish_date', 'Unknown')}")
                    st.write(f"**요약:** {news_item.get('summary', 'No summary available')}")
                
    except Exception as e:
        container.error(f"뉴스 데이터 표시 오류: {str(e)}")

def display_market_data(container, market_data):
    """거시경제 지표 데이터 표시"""
    try:
        if isinstance(market_data, str):
            data = json.loads(market_data)
        else:
            data = market_data
        
        container.markdown("**📊 주요 거시경제 지표**")
        
        indicators = {k: v for k, v in data.items() if not k.startswith('_')}
        
        indicator_items = list(indicators.items())
        for i in range(0, len(indicator_items), 3):
            cols = container.columns(3)
            for j, (key, info) in enumerate(indicator_items[i:i+3]):
                if j < len(cols):
                    with cols[j]:
                        if isinstance(info, dict) and 'value' in info:
                            description = info.get('description', key)
                            value = info['value']
                            st.metric(description, f"{value}")
                        else:
                            st.write(f"**{key}**: 데이터 없음")
                
    except Exception as e:
        container.error(f"시장 데이터 표시 오류: {str(e)}")

def display_risk_analysis_result(container, analysis_content):
    """최종 리스크 분석 결과 표시"""
    try:
        data = extract_json_from_text(analysis_content)
        if not data:
            container.error("리스크 분석 데이터를 찾을 수 없습니다.")
            return
        
        for i, scenario_key in enumerate(["scenario1", "scenario2"], 1):
            if scenario_key in data:
                scenario = data[scenario_key]
                
                container.subheader(f"시나리오 {i}: {scenario.get('name', f'Scenario {i}')}")
                container.markdown(scenario.get('description', '설명 없음'))
                
                col1, col2 = container.columns(2)
                
                with col1:
                    allocation = scenario.get('allocation_management', {})
                    if allocation:
                        fig = go.Figure(data=[go.Pie(
                            labels=list(allocation.keys()),
                            values=list(allocation.values()),
                            hole=.3,
                            textinfo='label+percent'
                        )])
                        fig.update_layout(height=400)
                        st.plotly_chart(fig)
                
                with col2:
                    st.markdown("**조정 이유 및 전략**")
                    st.info(scenario.get('reason', '근거 없음'))
        
    except Exception as e:
        container.error(f"리스크 분석 표시 오류: {str(e)}")
        container.text(str(analysis_content))

def invoke_risk_manager(portfolio_data):
    """Risk Manager 호출"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"portfolio_data": portfolio_data})
        )
        
        placeholder = st.container()
        placeholder.subheader("AI 분석 과정")
        
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
                        body = parse_tool_result(result_text)
                        
                        if actual_tool_name == "get_product_news":
                            display_news_data(placeholder, body)
                        elif actual_tool_name == "get_market_data":
                            display_market_data(placeholder, body)
                    
                    current_thinking = ""
                    if tool_use_id in tool_id_to_name:
                        del tool_id_to_name[tool_use_id]
                    current_text_placeholder = placeholder.empty()
                    
            except json.JSONDecodeError:
                continue
        
        placeholder.divider()
        placeholder.subheader("📌 리스크 분석 및 시나리오 플래닝")
        display_risk_analysis_result(placeholder, current_thinking)
        
        return {"status": "success"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

# UI 구성
with st.expander("아키텍처", expanded=True):
    st.image("../static/risk_manager.png", width=800)
st.markdown("**포트폴리오 구성 입력**")

# 포트폴리오 배분 입력
st.markdown("**포트폴리오 배분**")
col1, col2, col3 = st.columns(3)
with col1:
    ticker1 = st.text_input("ETF 1", value="QQQ")
    allocation1 = st.number_input("비율 1 (%)", min_value=0, max_value=100, value=60)
with col2:
    ticker2 = st.text_input("ETF 2", value="SPY")
    allocation2 = st.number_input("비율 2 (%)", min_value=0, max_value=100, value=30)
with col3:
    ticker3 = st.text_input("ETF 3", value="GLD")
    allocation3 = st.number_input("비율 3 (%)", min_value=0, max_value=100, value=10)

strategy = st.text_input("투자 전략", value="고성장 기술주 중심의 공격적 포트폴리오")
reason = st.text_area("구성 근거", value="고객의 공격적인 위험 성향과 높은 목표 수익률 달성을 위한 전략", height=100)

submitted = st.button("리스크 분석 시작", use_container_width=True)

if submitted:
    st.divider()
    
    with st.spinner("AI 리스크 분석 중..."):
        portfolio_dict = {
            "portfolio_allocation": {
                ticker1: allocation1,
                ticker2: allocation2,
                ticker3: allocation3
            },
            "strategy": strategy,
            "reason": reason
        }
        
        result = invoke_risk_manager(portfolio_dict)
        
        if result['status'] == 'error':
            st.error(f"❌ 분석 중 오류: {result.get('error', 'Unknown error')}")