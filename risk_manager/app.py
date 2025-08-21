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
from pathlib import Path

# 상위 디렉토리 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        
        for i, news_item in enumerate(news_list[:3], 1):  # 상위 3개만 표시
            with container.expander(f"{i}. {news_item.get('title', 'No Title')}"):
                st.write(f"**발행일:** {news_item.get('publish_date', 'Unknown')}")
                st.write(f"**요약:** {news_item.get('summary', 'No summary available')}")
                if news_item.get('link'):
                    st.write(f"**링크:** {news_item['link']}")
                
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
        
        # 2열로 지표 표시
        cols = container.columns(2)
        col_idx = 0
        
        for key, info in indicators.items():
            with cols[col_idx % 2]:
                if isinstance(info, dict) and 'value' in info:
                    value = info['value']
                    description = info.get('description', key)
                    
                    # 값에 따른 색상 설정
                    if 'vix' in key.lower():
                        # VIX는 높을수록 위험 (빨간색)
                        color = "red" if value > 20 else "green"
                    elif 'yield' in key.lower():
                        # 수익률은 높을수록 주의 (노란색)
                        color = "orange" if value > 4 else "blue"
                    else:
                        color = "blue"
                    
                    st.metric(
                        label=description,
                        value=f"{value}",
                        delta=None
                    )
                else:
                    st.write(f"**{key}**: 데이터 없음")
            
            col_idx += 1
                
    except Exception as e:
        container.error(f"시장 데이터 표시 오류: {str(e)}")

def create_scenario_comparison_chart(scenario_data):
    """
    시나리오별 포트폴리오 비교 차트 생성
    
    Args:
        scenario_data (dict): 시나리오 데이터
        
    Returns:
        plotly.graph_objects.Figure: 비교 차트
    """
    try:
        scenario1 = scenario_data.get('scenario1', {})
        scenario2 = scenario_data.get('scenario2', {})
        
        allocation1 = scenario1.get('allocation_management', {})
        allocation2 = scenario2.get('allocation_management', {})
        
        # 데이터 준비
        tickers = list(set(list(allocation1.keys()) + list(allocation2.keys())))
        scenario1_values = [allocation1.get(ticker, 0) for ticker in tickers]
        scenario2_values = [allocation2.get(ticker, 0) for ticker in tickers]
        
        # 그룹화된 막대 차트 생성
        fig = go.Figure(data=[
            go.Bar(name=scenario1.get('name', 'Scenario 1'), x=tickers, y=scenario1_values, marker_color='lightblue'),
            go.Bar(name=scenario2.get('name', 'Scenario 2'), x=tickers, y=scenario2_values, marker_color='lightcoral')
        ])
        
        fig.update_layout(
            title="시나리오별 포트폴리오 배분 비교",
            xaxis_title="ETF 티커",
            yaxis_title="배분 비율 (%)",
            barmode='group',
            height=400
        )
        
        return fig
        
    except Exception as e:
        st.error(f"차트 생성 오류: {str(e)}")
        return None

def display_risk_analysis_result(container, analysis_content):
    """
    최종 리스크 분석 결과를 표시
    
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
        
        # 시나리오 비교 차트
        fig = create_scenario_comparison_chart(data)
        if fig:
            container.plotly_chart(fig, use_container_width=True)
        
        # 시나리오별 상세 정보
        col1, col2 = container.columns(2)
        
        # 시나리오 1
        with col1:
            scenario1 = data.get('scenario1', {})
            st.markdown(f"### 🔮 {scenario1.get('name', 'Scenario 1')}")
            st.info(scenario1.get('description', '설명 없음'))
            
            st.markdown("**조정된 포트폴리오:**")
            allocation1 = scenario1.get('allocation_management', {})
            for ticker, ratio in allocation1.items():
                st.write(f"• {ticker}: {ratio}%")
            
            st.markdown("**조정 근거:**")
            st.write(scenario1.get('reason', '근거 없음'))
        
        # 시나리오 2
        with col2:
            scenario2 = data.get('scenario2', {})
            st.markdown(f"### 🔮 {scenario2.get('name', 'Scenario 2')}")
            st.info(scenario2.get('description', '설명 없음'))
            
            st.markdown("**조정된 포트폴리오:**")
            allocation2 = scenario2.get('allocation_management', {})
            for ticker, ratio in allocation2.items():
                st.write(f"• {ticker}: {ratio}%")
            
            st.markdown("**조정 근거:**")
            st.write(scenario2.get('reason', '근거 없음'))
        
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
                    # 마지막 AI 생각 표시 후 완료
                    if current_thinking.strip():
                        with current_text_placeholder.chat_message("assistant"):
                            st.markdown(current_thinking.strip())
                    break
                    
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
    st.markdown("""
    ### 🔄 AgentCore Runtime Architecture (Planning Pattern)
    ```
    포트폴리오 제안 → AgentCore Runtime → 리스크 관리사 AI → 도구 사용 → 시나리오 플래닝
    ```
    
    **구성 요소:**
    - **Risk Manager Agent**: 뉴스 기반 리스크 분석 및 시나리오 플래닝
    - **Planning Pattern**: 체계적인 데이터 수집 → 분석 → 계획 수립
    - **AgentCore Runtime**: AWS 서버리스 실행 환경
    
    **사용 도구:**
    - `get_product_news(ticker)`: ETF별 최신 뉴스 조회
    - `get_market_data()`: 주요 거시경제 지표 조회
    """)

# 입력 폼
st.markdown("**포트폴리오 제안 결과 입력 (🤖 Portfolio Architect)**")

portfolio_data = st.text_area(
    "JSON 형식",
    value='{"portfolio_allocation": {"QQQ": 60, "SPY": 30, "GLD": 10}, "strategy": "고성장 기술주 중심의 공격적 포트폴리오로, 시장 전반의 익스포저와 위험 헤지를 결합한 전략", "reason": "고객의 공격적인 위험 성향과 40%의 높은 목표 수익률을 달성하기 위해, 성장성이 높은 기술주(QQQ) 60%를 주축으로 하고, 시장 전반의 성장을 담는 SPY 30%를 배분했습니다. 변동성 위험을 관리하기 위해 GLD 10%를 배분하여 포트폴리오의 안정성을 보완했습니다."}',
    height=200
)

submitted = st.button("리스크 분석 시작", use_container_width=True)

# 메인 실행 로직
if submitted and portfolio_data:
    st.divider()
    
    with st.spinner("AI 리스크 분석 중..."):
        try:
            # JSON 파싱
            portfolio_dict = json.loads(portfolio_data)
            
            result = invoke_risk_manager(portfolio_dict)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                
        except json.JSONDecodeError:
            st.error("❌ 올바른 JSON 형식이 아닙니다. 입력 데이터를 확인해주세요.")
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")