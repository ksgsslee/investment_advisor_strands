"""
Investment Advisor Streamlit 앱
Multi-Agent 투자 자문 시스템 웹 인터페이스
"""

import streamlit as st
import os
import json
import boto3
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path
from bedrock_agentcore.memory import MemoryClient

st.set_page_config(
    page_title="🤖 Investment Advisor",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🤖 Investment Advisor")

# 사이드바 메뉴
menu = st.sidebar.selectbox(
    "메뉴 선택",
    ["🤖 새로운 투자 상담", "📚 상담 히스토리 (Long-term Memory)"]
)

# 배포 정보 로드
try:
    with open(Path(__file__).parent / "deployment_info.json") as f:
        deployment_info = json.load(f)
    AGENT_ARN = deployment_info["agent_arn"]
    REGION = deployment_info["region"]
    
    with open(Path(__file__).parent / "agentcore_memory" / "deployment_info.json") as f:
        memory_info = json.load(f)
    MEMORY_ID = memory_info["memory_id"]
    
except Exception:
    st.error("배포 정보를 찾을 수 없습니다. deploy.py를 먼저 실행해주세요.")
    st.stop()

agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)
memory_client = MemoryClient(region_name=REGION)

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

def display_calculator_result(container, tool_input, result_text):
    """Calculator 도구 결과 표시"""
    container.markdown("**🧮 Calculator 계산 결과**")
    container.code(f"Input: {tool_input}\n\n{result_text}", language="text")

def display_etf_analysis_result(container, etf_data):
    """개별 ETF 분석 결과 표시"""
    try:
        container.markdown(f"**📊 {etf_data['ticker']} 분석 결과 (몬테카를로 시뮬레이션)**")
        
        col1, col2, col3, col4 = container.columns(4)
        
        with col1:
            st.metric("예상 수익률", f"{etf_data['expected_annual_return']}%")
        with col2:
            st.metric("손실 확률", f"{etf_data['loss_probability']}%")
        with col3:
            st.metric("변동성", f"{etf_data['volatility']}%")
        with col4:
            st.metric("과거 수익률", f"{etf_data['historical_annual_return']}%")
        
        if 'return_distribution' in etf_data:
            distribution = etf_data['return_distribution']
            ranges = list(distribution.keys())
            counts = list(distribution.values())
            
            fig = go.Figure(data=[go.Bar(
                x=ranges,
                y=counts,
                text=[f"{count}회<br>({count/5:.1f}%)" for count in counts],
                textposition='auto',
                marker_color='lightblue',
                name=etf_data['ticker']
            )])
            
            fig.update_layout(
                title=f"1년 후 예상 수익률 분포 (1000회 시뮬레이션)",
                xaxis_title="수익률 구간",
                yaxis_title="시나리오 개수",
                height=400,
                showlegend=False
            )
            
            container.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        container.error(f"ETF 분석 결과 표시 오류: {e}")

def display_correlation_analysis(container, correlation_data):
    """상관관계 분석 결과 표시"""
    try:
        container.markdown("**🔗 ETF 상관관계 매트릭스**")
        
        correlation_matrix = correlation_data.get('correlation_matrix', {})
        
        if correlation_matrix:
            df = pd.DataFrame(correlation_matrix)
            
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
            container.plotly_chart(fig, use_container_width=True)
            
            container.markdown("**상관관계 해석**")
            container.info("""
            - **1.0**: 완전한 양의 상관관계 (같은 방향으로 움직임)
            - **0.7~0.9**: 높은 양의 상관관계 (분산투자 효과 제한적)
            - **0.3~0.7**: 중간 양의 상관관계 (적당한 분산투자 효과)
            - **-0.3~0.3**: 낮은 상관관계 (좋은 분산투자 효과)
            - **-1.0**: 완전한 음의 상관관계 (반대 방향으로 움직임)
            """)
        
    except Exception as e:
        container.error(f"상관관계 분석 표시 오류: {e}")

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

def display_financial_analysis(container, analysis_content):
    """재무 분석 결과 표시"""
    try:
        data = extract_json_from_text(analysis_content)
        if not data:
            container.error("재무 분석 데이터를 찾을 수 없습니다.")
            return
            
        container.markdown("**종합 총평**")
        container.info(data.get("summary", ""))

        col1, col2 = container.columns(2)
        
        with col1:
            st.metric("위험 성향", data.get("risk_profile", "N/A"))
            st.markdown("**위험 성향 분석**")
            st.write(data.get("risk_profile_reason", ""))
        
        with col2:
            st.metric("필요 수익률", f"{data.get('required_annual_return_rate', 'N/A')}%")
            st.markdown("**수익률 분석**")
            st.write(data.get("return_rate_reason", ""))

    except Exception as e:
        container.error(f"재무 분석 표시 오류: {str(e)}")

def display_portfolio_result(container, portfolio_content):
    """포트폴리오 설계 결과 표시"""
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
        container.error(f"포트폴리오 표시 오류: {str(e)}")

def display_risk_analysis_result(container, analysis_content):
    """리스크 분석 결과 표시"""
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
                
                probability_str = scenario.get('probability', '0%')
                try:
                    prob_value = int(probability_str.replace('%', ''))
                    container.markdown(f"**📊 발생 확률: {probability_str}**")
                    container.progress(prob_value / 100)
                except:
                    container.markdown(f"**📊 발생 확률: {probability_str}**")
                
                col1, col2 = container.columns(2)
                
                with col1:
                    st.markdown("**조정된 포트폴리오 배분**")
                    allocation = scenario.get('allocation_management', {})
                    if allocation:
                        fig = go.Figure(data=[go.Pie(
                            labels=list(allocation.keys()),
                            values=list(allocation.values()),
                            hole=.3,
                            textinfo='label+percent'
                        )])
                        fig.update_layout(height=400, title=f"시나리오 {i} 포트폴리오")
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**조정 이유 및 전략**")
                    st.info(scenario.get('reason', '근거 없음'))

        
    except Exception as e:
        container.error(f"리스크 분석 표시 오류: {str(e)}")

def invoke_investment_advisor(input_data):
    """Investment Advisor 호출"""
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"input_data": input_data})
        )
        
        progress_container = st.container()
        results_container = st.container()
        
        current_agent = None
        agent_containers = {}
        agent_thinking_containers = {}
        current_thinking = {}
        current_text_placeholders = {}
        tool_id_to_name = {}
        tool_id_to_input = {}
        
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    event_type = event_data.get("type")
                    
                    if event_type == "text_chunk":
                        chunk_data = event_data.get("data", "")
                        if current_agent and current_agent in current_thinking:
                            current_thinking[current_agent] += chunk_data
                            if current_thinking[current_agent].strip() and current_agent in current_text_placeholders:
                                # expander 내부에서 채팅 형태로 표시
                                with current_text_placeholders[current_agent].chat_message("assistant"):
                                    st.markdown(current_thinking[current_agent])
                    
                    elif event_type == "tool_use":
                        tool_name = event_data.get("tool_name", "")
                        tool_use_id = event_data.get("tool_use_id", "")
                        tool_input = event_data.get("tool_input", "")
                        
                        actual_tool_name = tool_name.split("___")[-1] if "___" in tool_name else tool_name
                        tool_id_to_name[tool_use_id] = actual_tool_name
                        tool_id_to_input[tool_use_id] = tool_input
                    
                    elif event_type == "tool_result":
                        tool_use_id = event_data.get("tool_use_id", "")
                        actual_tool_name = tool_id_to_name.get(tool_use_id, "unknown")
                        tool_input = tool_id_to_input.get(tool_use_id, "unknown")
                        tool_content = event_data.get("content", [{}])
                        
                        if tool_content and len(tool_content) > 0 and current_agent in agent_thinking_containers:
                            result_text = tool_content[0].get("text", "{}")
                            container = agent_thinking_containers[current_agent]
                            
                            if current_agent == "financial" and actual_tool_name == "calculator":
                                display_calculator_result(container, tool_input, result_text)
                            elif current_agent == "portfolio":
                                try:
                                    body = json.loads(result_text)
                                    if actual_tool_name == "analyze_etf_performance":
                                        display_etf_analysis_result(container, body)
                                    elif actual_tool_name == "calculate_correlation":
                                        display_correlation_analysis(container, body)
                                except:
                                    pass
                            elif current_agent == "risk":
                                try:
                                    parsed_result = json.loads(result_text)
                                    if "statusCode" in parsed_result and "body" in parsed_result:
                                        body = parsed_result["body"]
                                        if isinstance(body, str):
                                            body = json.loads(body)
                                    else:
                                        body = parsed_result
                                    
                                    if actual_tool_name == "get_product_news":
                                        display_news_data(container, body)
                                    elif actual_tool_name == "get_market_data":
                                        display_market_data(container, body)
                                except:
                                    pass
                        
                        if current_agent:
                            current_thinking[current_agent] = ""
                            if tool_use_id in tool_id_to_name:
                                del tool_id_to_name[tool_use_id]
                            if tool_use_id in tool_id_to_input:
                                del tool_id_to_input[tool_use_id]
                            if current_agent in current_text_placeholders:
                                current_text_placeholders[current_agent] = agent_thinking_containers[current_agent].empty()
                    
                    elif event_type == "node_start":
                        agent_name = event_data.get("agent_name")
                        current_agent = agent_name
                        
                        agent_display_names = {
                            "financial": "Financial Analyst",
                            "portfolio": "Portfolio Architect", 
                            "risk": "Risk Manager"
                        }
                        
                        agent_containers[agent_name] = results_container.container()
                        
                        # 사고과정을 expander로 감싸기
                        thinking_expander = agent_containers[agent_name].expander(f"🧠 {agent_display_names.get(agent_name, agent_name)} Reasoning", expanded=True)
                        agent_thinking_containers[agent_name] = thinking_expander.container()
                        
                        current_thinking[agent_name] = ""
                        current_text_placeholders[agent_name] = agent_thinking_containers[agent_name].empty()
                        
                    elif event_type == "node_complete":
                        agent_name = event_data.get("agent_name")
                        result = event_data.get("result")
                        
                        if agent_name in agent_containers and result:
                            container = agent_containers[agent_name]
                            
                            # 최종 결과는 expander 밖에 표시 (메인 영역)
                            if agent_name == "financial":
                                container.subheader("📌 재무 분석 결과")
                                display_financial_analysis(container, result)
                                container.divider()
                                
                            elif agent_name == "portfolio":
                                container.subheader("📌 포트폴리오 설계 결과")
                                display_portfolio_result(container, result)
                                container.divider()
                                
                            elif agent_name == "risk":
                                container.subheader("📌 리스크 분석 및 시나리오 플래닝")
                                display_risk_analysis_result(container, result)
                                container.divider()
                        


                    elif event_type == "error":
                        return {"status": "error", "error": event_data.get("error", "Unknown error")}
                        
                except json.JSONDecodeError:
                    continue
        
        # 모든 분석 완료 메시지를 results_container 맨 아래에 표시
        with results_container:
            st.success("🎉 모든 에이전트 분석 완료!")
            st.info("💾 이 상담 내용은 AgentCore Memory에 자동으로 요약되어 저장됩니다. 좌측 📚 상담 히스토리 메뉴에서 확인하실 수 있습니다.")

        return {"status": "success"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def load_long_term_summaries():
    """Long-term Memory에서 요약 데이터 로드 - retrieve_memories 사용"""
    try:
        # SUMMARY 전략이 생성한 Long-term Memory 조회
        response = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace="investment/session",
            query="investment consultation summary"  # 투자 상담 요약 검색
        )
        
        summaries = []
        for record in response:
            # content 추출 (간단화)
            content = record.get('content', {})
            content_text = content.get('text', str(content)) if isinstance(content, dict) else str(content)
            
            # timestamp 추출 (간단화)
            timestamp = record.get('createdAt', record.get('created_at', 'Unknown'))
            timestamp_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
            
            summaries.append({
                'session_id': record.get('memoryRecordId', 'Unknown'),
                'timestamp': timestamp_str,
                'content': content_text,
                'namespaces': record.get('namespaces', [])
            })

        # 시간순으로 정렬 (최신순)
        summaries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return summaries[:10]  # 최대 10개만 반환
        
    except Exception as e:
        st.error(f"Long-term Memory 조회 실패: {e}")
        st.error(f"오류 상세: {str(e)}")
        
        # 디버깅을 위해 MemoryClient의 사용 가능한 메서드 표시
        try:
            available_methods = [method for method in dir(memory_client) if not method.startswith('_')]
            st.info(f"사용 가능한 MemoryClient 메서드들: {', '.join(available_methods)}")
        except:
            pass
            
        return []

# 메뉴별 UI 구성
if menu == "🤖 새로운 투자 상담":
    with st.expander("🏗️ Investment Advisor 아키텍처", expanded=False):
        st.image(os.path.join("../static/investment_advisor.png"))


    st.markdown("**투자자 정보 입력**")

    col1, col2 = st.columns(2)

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
        target_amount = st.number_input(
            "🎯 1년 후 목표 금액 (억원 단위)",
            min_value=0.0,
            max_value=1000.0,
            value=0.7,
            step=0.1,
            format="%.1f"
        )
        st.caption("예: 0.7 = 7천만원")

    col3, col4, col5 = st.columns(3)

    with col3:
        age_options = [f"{i}-{i+4}세" for i in range(20, 101, 5)]
        age = st.selectbox(
            "나이",
            options=age_options,
            index=3
        )

    with col4:
        experience_categories = ["0-1년", "1-3년", "3-5년", "5-10년", "10-20년", "20년 이상"]
        stock_investment_experience_years = st.selectbox(
            "주식 투자 경험",
            options=experience_categories,
            index=3
        )

    with col5:
        investment_purpose = st.selectbox(
            "🎯 투자 목적",
            options=["단기 수익 추구", "노후 준비", "주택 구입 자금", "자녀 교육비", "여유 자금 운용"],
            index=0
        )

    preferred_sectors = st.multiselect(
        "📈 관심 투자 분야 (복수 선택)",
        options=[
            "배당주 (안정적 배당)",
            "성장주 (기술/바이오)",
            "가치주 (저평가 우량주)", 
            "리츠 (부동산 투자)",
            "ETF (분산 투자)",
            "해외 주식",
            "채권 (안전 자산)",
            "원자재/금"
        ],
        default=["ETF (분산 투자)"]
    )

    submitted = st.button("분석 시작", use_container_width=True)

    if submitted:
        age_number = int(age.split('-')[0]) + 2
        
        experience_mapping = {
            "0-1년": 1, "1-3년": 2, "3-5년": 4, 
            "5-10년": 7, "10-20년": 15, "20년 이상": 25
        }
        experience_years = experience_mapping[stock_investment_experience_years]
        
        input_data = {
            "total_investable_amount": int(total_investable_amount * 100000000),
            "age": age_number,
            "stock_investment_experience_years": experience_years,
            "target_amount": int(target_amount * 100000000),
            "investment_purpose": investment_purpose,
            "preferred_sectors": preferred_sectors
        }
        
        st.divider()
        
        with st.spinner("AI 분석 중..."):
            result = invoke_investment_advisor(input_data)
            
            if result['status'] == 'error':
                st.error(f"❌ 분석 중 오류: {result.get('error', 'Unknown error')}")

elif menu == "📚 상담 히스토리 (Long-term Memory)":
    st.markdown("### 📚 투자 상담 히스토리")
    st.info("AgentCore SUMMARY 전략이 자동으로 생성한 투자 상담 요약을 확인할 수 있습니다.")
    
    if st.button("🔄 히스토리 새로고침", use_container_width=True):
        st.rerun()
    
    with st.spinner("Long-term Memory에서 요약 데이터 로딩 중..."):
        summaries = load_long_term_summaries()
    
    if not summaries:
        st.warning("아직 저장된 투자 상담 히스토리가 없습니다.")
        st.markdown("새로운 투자 상담을 진행하면 자동으로 요약이 생성됩니다.")
    else:
        for i, summary in enumerate(summaries, 1):
            timestamp = summary['timestamp']
            # 시간 표시를 더 읽기 쉽게 포맷
            try:
                from datetime import datetime
                if isinstance(timestamp, str) and 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_display = dt.strftime('%Y-%m-%d %H:%M')
                else:
                    time_display = str(timestamp)
            except:
                time_display = str(timestamp)
            
            # 네임스페이스에서 session ID 추출 (마지막 / 부분)
            session_display = summary['session_id']
            if summary.get('namespaces'):
                namespace = summary['namespaces'][0] if isinstance(summary['namespaces'], list) else str(summary['namespaces'])
                if '/' in namespace:
                    session_display = namespace.split('/')[-1]
            
            with st.expander(f"📋 {time_display} - Session: {session_display}"):
                st.markdown("**투자 상담 요약 (AgentCore SUMMARY 자동 생성)**")
                content = summary['content']
                
                # XML 형태의 summary를 더 읽기 쉽게 처리
                if isinstance(content, str) and '<summary>' in content:
                    # XML에서 topic들을 추출해서 표시
                    import re
                    topics = re.findall(r'<topic name="([^"]+)">\s*(.*?)\s*</topic>', content, re.DOTALL)
                    
                    if topics:
                        for topic_name, topic_content in topics:
                            st.markdown(f"**📌 {topic_name}**")
                            # HTML 엔티티 디코딩
                            clean_content = topic_content.replace('&quot;', '"').replace('&#39;', "'")
                            st.write(clean_content.strip())
                            st.write("")  # 빈 줄 추가
                    else:
                        # XML 파싱 실패 시 원본 표시
                        st.text(content)
                else:
                    # 일반 텍스트 처리
                    content_str = str(content)
                    st.markdown(content_str)
