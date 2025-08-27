"""
app.py
Risk Manager Streamlit 애플리케이션 (AgentCore Runtime 버전)

AI 리스크 관리사가 포트폴리오 제안을 바탕으로 뉴스 기반 리스크 분석을 수행하고,
경제 시나리오에 따른 포트폴리오 조정 가이드를 제공하는 웹 애플리케이션
"""

import streamlit as st
import json
import os
import sys
import boto3
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import uuid
import itertools
from pathlib import Path


# ================================
# 페이지 설정 및 초기화
# ================================

st.set_page_config(page_title="Risk Manager")
st.title("⚠️ Risk Manager")

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

def parse_tool_result(result_text):
    """
    도구 실행 결과에서 실제 데이터를 추출하는 함수
    
    Args:
        result_text (str): Lambda 응답 JSON 문자열
        
    Returns:
        dict: 파싱된 데이터
    """
    parsed_result = json.loads(result_text)
    return parsed_result["response"]["payload"]["body"]

# ================================
# 데이터 표시 함수들
# ================================

def display_news_data(container, news_data):
    """
    ETF 뉴스 데이터를 표시
    
    Args:
        container: Streamlit 컨테이너
        news_data: 뉴스 데이터 (dict 또는 JSON 문자열)
    """
    try:
        # 데이터 타입 정규화
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
        
        # DataFrame으로 뉴스 표시 (원본 코드 스타일 적용)
        news_df = pd.DataFrame(news_list)
        if not news_df.empty and all(col in news_df.columns for col in ['publish_date', 'title', 'summary']):
            container.dataframe(
                news_df[['publish_date', 'title', 'summary']],
                hide_index=True,
                use_container_width=True
            )
        else:
            # DataFrame 생성 실패 시 기존 방식으로 표시
            for i, news_item in enumerate(news_list[:5], 1):
                with container.expander(f"{i}. {news_item.get('title', 'No Title')}"):
                    st.write(f"**발행일:** {news_item.get('publish_date', 'Unknown')}")
                    st.write(f"**요약:** {news_item.get('summary', 'No summary available')}")
                
    except Exception as e:
        container.error(f"뉴스 데이터 표시 오류: {str(e)}")

def display_market_data(container, market_data):
    """
    거시경제 지표 데이터를 표시
    
    Args:
        container: Streamlit 컨테이너
        market_data: 시장 데이터 (dict 또는 JSON 문자열)
    """
    try:
        # 데이터 타입 정규화
        if isinstance(market_data, str):
            data = json.loads(market_data)
        else:
            data = market_data
        
        container.markdown("**📊 주요 거시경제 지표**")
        
        # 메타데이터 제외하고 지표만 추출
        indicators = {k: v for k, v in data.items() if not k.startswith('_')}
        
        # 3열로 지표 표시 (원본 코드 스타일 적용)
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

def create_pie_chart(data, chart_title=""):
    """
    포트폴리오 배분을 위한 파이 차트 생성 (원본 코드 스타일)
    
    Args:
        data (dict): 자산 배분 데이터
        chart_title (str): 차트 제목
        
    Returns:
        plotly.graph_objects.Figure: 파이 차트
    """
    try:
        fig = go.Figure(data=[go.Pie(
            labels=list(data.keys()),
            values=list(data.values()),
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

def display_risk_analysis_result(container, analysis_content):
    """
    최종 리스크 분석 결과를 표시 (원본 코드 스타일 적용)
    
    Args:
        container: Streamlit 컨테이너
        analysis_content: 리스크 분석 데이터 (dict 또는 JSON 문자열)
    """
    try:
        # JSON 데이터 추출
        data = extract_json_from_text(analysis_content)
        if not data:
            container.error("리스크 분석 데이터를 찾을 수 없습니다.")
            return
        
        # 각 시나리오별로 표시 (원본 코드 스타일)
        for i, scenario_key in enumerate(["scenario1", "scenario2"], 1):
            if scenario_key in data:
                scenario = data[scenario_key]
                
                container.subheader(f"시나리오 {i}: {scenario.get('name', f'Scenario {i}')}")
                container.markdown(scenario.get('description', '설명 없음'))
                
                sub_col1, sub_col2 = container.columns([1, 1])
                
                with sub_col1:
                    # 파이 차트 생성 및 표시
                    allocation = scenario.get('allocation_management', {})
                    if allocation:
                        fig = create_pie_chart(
                            allocation,
                            "조정된 포트폴리오 자산 배분"
                        )
                        st.plotly_chart(fig)
                
                with sub_col2:
                    st.markdown("**조정 이유 및 전략**")
                    st.info(scenario.get('reason', '근거 없음'))
        
    except Exception as e:
        container.error(f"리스크 분석 표시 오류: {str(e)}")
        container.text(str(analysis_content))

# ================================
# 메인 처리 함수
# ================================

def invoke_risk_manager(portfolio_data):
    """
    AgentCore Runtime을 호출하여 리스크 분석 수행
    
    Args:
        portfolio_data (dict): 포트폴리오 제안 결과
        
    Returns:
        dict: 실행 결과 (status, output_text)
    """
    try:
        # AgentCore Runtime 호출
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"portfolio_data": portfolio_data})
        )
        
        # UI 컨테이너 설정
        placeholder = st.container()
        placeholder.subheader("Bedrock Reasoning")
        
        # 상태 변수 초기화
        current_thinking = ""
        current_text_placeholder = placeholder.empty()
        tool_id_to_name = {}  # tool_use_id와 tool_name 매핑
        
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
                    # 도구 사용 시작 - 매핑 정보 저장
                    tool_name = event_data.get("tool_name", "")
                    tool_use_id = event_data.get("tool_use_id", "")
                    
                    # 실제 함수명 추출
                    actual_tool_name = tool_name.split("___")[-1] if "___" in tool_name else tool_name
                    tool_id_to_name[tool_use_id] = actual_tool_name
                
                elif event_type == "tool_result":
                    # 도구 실행 결과 처리
                    tool_use_id = event_data.get("tool_use_id", "")
                    actual_tool_name = tool_id_to_name.get(tool_use_id, "unknown")
                    
                    tool_content = event_data.get("content", [{}])
                    if tool_content and len(tool_content) > 0:
                        result_text = tool_content[0].get("text", "{}")
                        body = parse_tool_result(result_text)
                        
                        # 도구 타입에 따라 적절한 표시 함수 호출
                        if actual_tool_name == "get_product_news":
                            display_news_data(placeholder, body)
                        elif actual_tool_name == "get_market_data":
                            display_market_data(placeholder, body)
                    
                    # 도구 결과 처리 후 생각 텍스트 리셋 및 새로운 placeholder 생성
                    current_thinking = ""
                    if tool_use_id in tool_id_to_name:
                        del tool_id_to_name[tool_use_id]
                    current_text_placeholder = placeholder.empty()
                
                elif event_type == "streaming_complete":
                    continue
                    
            except json.JSONDecodeError:
                continue
        
        # 최종 리스크 분석 결과 표시
        placeholder.divider()
        placeholder.markdown("⚠️ **Risk Manager**")
        placeholder.subheader("📌 리스크 분석 및 시나리오 플래닝")
        display_risk_analysis_result(placeholder, current_thinking)
        
        return {
            "status": "success",
            "output_text": current_thinking
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
    st.image(os.path.join("../static/risk_manager.png"), width=800)


# 입력 폼
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

# 메인 실행 로직
if submitted:
    st.divider()
    
    with st.spinner("AI 리스크 분석 중..."):
        try:
            # 포트폴리오 데이터 구성
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
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                
        except json.JSONDecodeError:
            st.error("❌ 올바른 JSON 형식이 아닙니다. 입력 데이터를 확인해주세요.")
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")