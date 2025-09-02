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

def display_products_table(container, products):
    """ETF 상품 목록 테이블 표시"""
    try:
        if isinstance(products, str):
            products = json.loads(products)
        
        df = pd.DataFrame(
            [[ticker, desc] for ticker, desc in products.items()],
            columns=['티커', '설명']
        )
        container.markdown("**사용 가능한 ETF 상품**")
        container.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        container.error(f"상품 목록 표시 오류: {e}")

def display_price_chart(container, price_data):
    """ETF 가격 차트 표시"""
    try:
        if isinstance(price_data, str):
            price_data = json.loads(price_data)
        
        for ticker, prices in price_data.items():
            df = pd.DataFrame.from_dict(prices, orient='index', columns=['Price'])
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Price'], mode='lines', name=ticker))
            fig.update_layout(title=f"{ticker} 가격 추이", height=400)
            container.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        container.error(f"가격 차트 표시 오류: {e}")

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
            st.markdown("**투자 전략**")
            st.info(data["strategy"])
        
        container.markdown("**상세 근거**")
        container.write(data["reason"])
        
    except Exception as e:
        container.error(f"포트폴리오 표시 오류: {e}")

def display_etf_analysis_result(container, etf_data):
    """개별 ETF 분석 결과 표시"""
    try:
        container.markdown(f"**📊 {etf_data['ticker']} 분석 결과**")
        
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
        
    except Exception as e:
        container.error(f"ETF 분석 결과 표시 오류: {e}")

def invoke_portfolio_architect(financial_analysis):
    """Portfolio Architect 호출"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"financial_analysis": financial_analysis})
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
                        try:
                            body = json.loads(result_text)
                        except:
                            body = result_text
                        
                        if actual_tool_name == "get_available_products":
                            display_products_table(placeholder, body)
                        elif actual_tool_name == "get_product_data":
                            display_price_chart(placeholder, body)
                        elif actual_tool_name == "analyze_etf_performance":
                            if isinstance(body, str):
                                etf_data = json.loads(body)
                            else:
                                etf_data = body
                            display_etf_analysis_result(placeholder, etf_data)
                    
                    current_thinking = ""
                    if tool_use_id in tool_id_to_name:
                        del tool_id_to_name[tool_use_id]
                    current_text_placeholder = placeholder.empty()
                    
            except json.JSONDecodeError:
                continue
        
        # 최종 결과 표시
        placeholder.divider()
        placeholder.subheader("📌 포트폴리오 설계 결과")
        display_portfolio_result(placeholder, current_thinking)
        
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
return_rate_reason = st.text_input("수익률 근거", value="1년간 연평균 40.0% 수익률 필요")

if st.button("분석 시작", use_container_width=True):
    financial_analysis = {
        "risk_profile": risk_profile,
        "risk_profile_reason": risk_profile_reason,
        "required_annual_return_rate": required_return,
        "return_rate_reason": return_rate_reason
    }
    
    st.divider()
    
    with st.spinner("AI 분석 중..."):
        result = invoke_portfolio_architect(financial_analysis)
        
        if result['status'] == 'error':
            st.error(f"❌ 분석 중 오류: {result.get('error', 'Unknown error')}")