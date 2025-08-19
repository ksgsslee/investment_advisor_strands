"""
app.py
Portfolio Architect Streamlit 애플리케이션 (AgentCore Runtime 버전)
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
from typing import Dict, Any

# 상위 디렉토리 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AVAILABLE_PRODUCTS

# 페이지 설정
st.set_page_config(page_title="Portfolio Architect")
st.title("📈 Portfolio Architect (AgentCore Version)")

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

def display_portfolio_analysis(container, portfolio_data):
    """포트폴리오 분석 결과를 깔끔하게 표시"""
    if not portfolio_data:
        container.warning("포트폴리오 데이터가 없습니다.")
        return
    
    try:
        # 이미 파싱된 딕셔너리인지 확인
        if isinstance(portfolio_data, dict):
            portfolio = portfolio_data
        else:
            # 문자열에서 JSON 추출
            portfolio = extract_portfolio_from_text(str(portfolio_data))
            if not portfolio:
                container.error("포트폴리오 데이터 파싱 실패")
                return
        
        container.markdown("## 🎯 포트폴리오 설계 결과")
        
        # 포트폴리오 배분 표시
        allocation = portfolio.get('portfolio_allocation', {})
        if not allocation:
            container.warning("포트폴리오 배분 데이터를 찾을 수 없습니다.")
            return
        
        # 2열 레이아웃
        col1, col2 = container.columns([1, 1])
        
        with col1:
            st.markdown("### 📊 자산 배분")
            
            # 배분 테이블 생성
            allocation_data = []
            for ticker, ratio in allocation.items():
                description = AVAILABLE_PRODUCTS.get(ticker, "설명 없음")
                allocation_data.append({
                    "ETF": ticker,
                    "비율": f"{ratio}%",
                    "설명": description
                })
            
            df = pd.DataFrame(allocation_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("### 📈 배분 차트")
            
            # 파이 차트
            fig = px.pie(
                values=list(allocation.values()),
                names=list(allocation.keys()),
                title="",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        # 전략 및 근거 (전체 폭)
        container.markdown("### 💡 투자 전략")
        strategy = portfolio.get('strategy', '전략 정보가 없습니다.')
        container.info(strategy)
        
        container.markdown("### 📋 구성 근거")
        reason = portfolio.get('reason', '구성 근거가 없습니다.')
        container.success(reason)
        
        # 요약 정보
        total_allocation = sum(allocation.values())
        container.markdown(f"**총 배분 비율:** {total_allocation}% | **선택된 ETF 수:** {len(allocation)}개")
            
    except Exception as e:
        container.error(f"포트폴리오 표시 중 오류: {str(e)}")
        if portfolio_data:
            with container.expander("원본 데이터 보기"):
                st.text(str(portfolio_data))

def process_streaming_response(response):
    """스트리밍 응답을 실시간으로 처리하고 UI 업데이트"""
    
    # UI 컨테이너들 생성
    status_container = st.container()
    progress_container = st.container()
    content_container = st.container()
    
    # 상태 추적 변수들
    accumulated_text = ""
    current_tool = None
    portfolio_result = None
    
    # 진행 상황 표시
    progress_bar = progress_container.progress(0)
    status_text = status_container.empty()
    content_text = content_container.empty()
    
    try:
        for line in response["response"].iter_lines(chunk_size=1):
            if not line or not line.decode("utf-8").startswith("data: "):
                continue
                
            try:
                event_data = json.loads(line.decode("utf-8")[6:])  # "data: " 제거
                event_type = event_data.get("type")
                
                if event_type == "text_chunk":
                    # 텍스트 청크 누적
                    chunk_data = event_data.get("data", "")
                    accumulated_text += chunk_data
                    
                    # 실시간 텍스트 업데이트 (너무 자주 업데이트하지 않도록 조절)
                    if len(accumulated_text) % 50 == 0 or event_data.get("complete", False):
                        content_text.markdown(f"**AI 응답:** {accumulated_text}")
                
                elif event_type == "tool_use":
                    # 도구 사용 시작
                    tool_name = event_data.get("tool_name", "Unknown")
                    current_tool = tool_name
                    status_text.info(f"🔧 도구 실행 중: {tool_name}")
                    progress_bar.progress(0.3)
                
                elif event_type == "tool_result":
                    # 도구 실행 결과
                    if current_tool:
                        status_text.success(f"✅ 도구 완료: {current_tool}")
                        progress_bar.progress(0.6)
                        current_tool = None
                
                elif event_type == "streaming_complete":
                    # 스트리밍 완료
                    message = event_data.get("message", "완료")
                    status_text.success(f"🎉 {message}")
                    progress_bar.progress(1.0)
                    
                    # 최종 결과에서 JSON 포트폴리오 추출
                    portfolio_result = extract_portfolio_from_text(accumulated_text)
                    break
                    
                elif event_type == "error":
                    status_text.error(f"❌ 오류: {event_data.get('error', 'Unknown error')}")
                    return {"status": "error", "error": event_data.get("error")}
                    
            except json.JSONDecodeError:
                continue
        
        # 최종 결과 표시
        if portfolio_result:
            content_container.empty()  # 기존 텍스트 지우기
            display_portfolio_analysis(content_container, portfolio_result)
        
        return {
            "status": "success",
            "portfolio_data": portfolio_result,
            "full_response": accumulated_text
        }
        
    except Exception as e:
        status_text.error(f"❌ 스트리밍 처리 중 오류: {str(e)}")
        return {"status": "error", "error": str(e)}

def extract_portfolio_from_text(text):
    """텍스트에서 JSON 포트폴리오 데이터 추출"""
    try:
        # JSON 블록 찾기
        start_idx = text.find('{')
        end_idx = text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx]
            return json.loads(json_str)
    except:
        pass
    return None

def invoke_portfolio_architect(financial_analysis):
    """AgentCore Runtime 호출"""
    try:
        st.markdown("### 📈 Portfolio Architect 실행 중...")
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"financial_analysis": financial_analysis})
        )
        
        # 스트리밍 응답 처리
        return process_streaming_response(response)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# 아키텍처 설명
with st.expander("아키텍처", expanded=True):
    st.markdown("""
    ### 🔄 AgentCore Runtime Architecture (Tool Use Pattern)
    ```
    재무 분석 결과 → AgentCore Runtime → 포트폴리오 설계사 AI → 도구 사용 → 최종 포트폴리오
    ```
    
    **구성 요소:**
    - **Portfolio Architect Agent**: 실시간 시장 데이터 기반 포트폴리오 설계
    - **Tool Use Pattern**: 외부 API 및 데이터 소스 활용
    - **AgentCore Runtime**: AWS 서버리스 실행 환경
    
    **사용 도구:**
    - `get_available_products()`: 투자 상품 목록 조회
    - `get_product_data(ticker)`: 실시간 가격 데이터 조회
    """)

# 입력 폼
st.markdown("**재무 분석 결과 입력**")
col1, col2 = st.columns(2)

with col1:
    risk_profile = st.selectbox(
        "위험 성향",
        ["매우 보수적", "보수적", "중립적", "공격적", "매우 공격적"],
        index=3
    )
    
    required_return = st.number_input(
        "필요 연간 수익률 (%)",
        min_value=0.0,
        max_value=100.0,
        value=40.0,
        step=0.1
    )

with col2:
    risk_reason = st.text_area(
        "위험 성향 평가 근거",
        value="나이가 35세로 젊고, 주식 투자 경험이 10년으로 상당히 많으며, 총 투자 가능 금액이 5000만원으로 상당히 높은 편입니다.",
        height=100
    )
    
    return_reason = st.text_area(
        "수익률 계산 근거",
        value="필요 연간 수익률은 (70000000 - 50000000) / 50000000 * 100 = 40.00%입니다.",
        height=100
    )

submitted = st.button("포트폴리오 설계 시작", use_container_width=True)

if submitted:
    financial_analysis = {
        "risk_profile": risk_profile,
        "risk_profile_reason": risk_reason,
        "required_annual_return_rate": required_return,
        "return_rate_reason": return_reason
    }
    
    st.divider()
    
    try:
        result = invoke_portfolio_architect(financial_analysis)
        
        if result['status'] == 'error':
            st.error(f"❌ 설계 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
        else:
            st.success("✅ 포트폴리오 설계가 완료되었습니다!")
            
            # 상세 정보 (선택적으로 보기)
            with st.expander("🔍 상세 분석 데이터 보기"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**� 입 력 데이터**")
                    st.json(financial_analysis)
                
                with col2:
                    st.markdown("**📤 AI 응답 데이터**")
                    if result.get('full_response'):
                        st.text_area("전체 응답", result['full_response'], height=200)
                    else:
                        st.json(result.get('portfolio_data', {}))
                
    except Exception as e:
        st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
        st.exception(e)