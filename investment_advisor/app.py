"""
app.py
Investment Advisor Streamlit 애플리케이션

Graph 기반 통합 투자 자문 시스템의 웹 인터페이스입니다.
3개 에이전트를 순차 실행하고 Memory에 히스토리를 저장하는 시스템입니다.
"""

import streamlit as st
import json
import os
import sys
import boto3
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import asyncio
from pathlib import Path
from datetime import datetime
from bedrock_agentcore.memory import Memory

# ================================
# 페이지 설정 및 초기화
# ================================

st.set_page_config(page_title="Investment Advisor", layout="wide")

# 사이드바 네비게이션
st.sidebar.title("🤖 Investment Advisor")
page = st.sidebar.selectbox("페이지 선택", [
    "💰 새로운 투자 상담",
    "📊 상담 히스토리"
])

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

def get_user_history(user_id, limit=10):
    """사용자의 투자 상담 히스토리 조회"""
    try:
        memory = Memory(
            memory_type="VECTOR",
            description="Investment consultation history"
        )
        
        results = memory.search(
            query=f"user_id:{user_id}",
            limit=limit
        )
        
        history_list = []
        for result in results:
            try:
                data = json.loads(result.content)
                history_list.append({
                    "session_id": data["session_id"],
                    "title": data["consultation_title"],
                    "date": data["timestamp"][:10],
                    "time": data["timestamp"][11:16],
                    "tags": data["tags"],
                    "summary": {
                        "risk_profile": data["analysis_results"]["risk_profile"],
                        "main_assets": list(data["analysis_results"]["recommended_portfolio"].keys())[:3],
                        "investment_amount": data["user_profile"]["investment_amount"]
                    },
                    "full_data": data
                })
            except (json.JSONDecodeError, KeyError) as e:
                continue
        
        # 날짜순 정렬
        history_list.sort(key=lambda x: x["date"] + x["time"], reverse=True)
        return history_list
        
    except Exception as e:
        st.error(f"히스토리 조회 오류: {str(e)}")
        return []

# ================================
# 메인 처리 함수
# ================================

def invoke_investment_advisor(input_data, user_id=None):
    """AgentCore Runtime을 호출하여 통합 투자 자문 수행"""
    try:
        payload = {"input_data": input_data}
        if user_id:
            payload["user_id"] = user_id
            
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps(payload)
        )

        # 응답을 표시할 컨테이너 생성
        placeholder = st.container()
        placeholder.markdown("🤖 **Investment Advisor (Graph + Memory)**")

        # 각 단계별 결과를 저장할 변수들
        all_results = {}
        final_report = None
        session_id = None

        # SSE 형식 응답 처리
        for line in response["response"].iter_lines(chunk_size=1):
            if line and line.decode("utf-8").startswith("data: "):
                try:
                    event_data = json.loads(line.decode("utf-8")[6:])
                    
                    if event_data["type"] == "analysis_start":
                        placeholder.info("🚀 Graph 기반 종합 분석을 시작합니다...")
                    
                    elif event_data["type"] == "analysis_complete":
                        session_id = event_data.get("session_id")
                        final_report = event_data.get("final_report")
                        all_results = event_data.get("all_results", {})
                        
                        placeholder.success("🎉 종합 투자 분석이 완료되었습니다!")
                        if session_id:
                            placeholder.info(f"📝 상담 결과가 Memory에 저장되었습니다 (세션 ID: {session_id})")
                        break
                        
                except json.JSONDecodeError:
                    continue

        return {
            "status": "success",
            "session_id": session_id,
            "final_report": final_report,
            "all_results": all_results
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ================================
# 페이지별 UI 구성
# ================================

if page == "💰 새로운 투자 상담":
    st.title("💰 새로운 투자 상담")
    
    # 아키텍처 설명
    with st.expander("시스템 아키텍처", expanded=False):
        st.markdown("""
        ### 🔄 Graph + Memory Architecture
        ```
        사용자 입력 → Financial Analyst → Portfolio Architect → Risk Manager → 리포트 생성 → Memory 저장
        ```
        
        **주요 특징:**
        - **Graph 패턴**: 3개 에이전트 순차 실행
        - **Memory 저장**: 상담 히스토리 자동 저장
        - **통합 리포트**: AI가 생성하는 종합 분석 리포트
        """)
    
    # 사용자 ID 입력
    user_id = st.text_input("사용자 ID (선택사항)", value="user123", help="히스토리 저장을 위한 사용자 식별자")
    
    # 입력 폼
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
        "💰1년 후 목표 금액 (억원 단위)",
        min_value=0.0,
        max_value=1000.0,
        value=0.7,
        step=0.1,
        format="%.1f"
    )
    st.caption("예: 0.7 = 7천만원")

    submitted = st.button("종합 투자 자문 시작", use_container_width=True)

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
        
        with st.spinner("AI Graph 분석 중..."):
            try:
                result = invoke_investment_advisor(input_data, user_id if user_id else None)
                
                if result['status'] == 'error':
                    st.error(f"❌ 분석 중 오류가 발생했습니다: {result.get('error', 'Unknown error')}")
                else:
                    # 최종 리포트 표시
                    if result.get('final_report'):
                        st.divider()
                        st.markdown("### 📋 AI 생성 종합 투자 리포트")
                        
                        report = result['final_report']
                        
                        # 리포트 제목과 요약
                        st.markdown(f"## {report.get('report_title', '투자 리포트')}")
                        st.info(report.get('executive_summary', '요약 정보 없음'))
                        
                        # 탭으로 구분하여 표시
                        tab1, tab2, tab3, tab4 = st.tabs(["고객 프로필", "추천 전략", "리스크 관리", "실행 계획"])
                        
                        with tab1:
                            if 'client_profile' in report:
                                profile = report['client_profile']
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("위험 성향", profile.get('risk_tolerance', 'N/A'))
                                with col2:
                                    st.metric("투자 목표", profile.get('investment_goal', 'N/A'))
                                with col3:
                                    st.metric("목표 수익률", profile.get('target_return', 'N/A'))
                        
                        with tab2:
                            if 'recommended_strategy' in report:
                                strategy = report['recommended_strategy']
                                if 'portfolio_allocation' in strategy:
                                    fig = create_pie_chart(
                                        strategy['portfolio_allocation'],
                                        "최종 추천 포트폴리오"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                st.markdown("**투자 근거**")
                                st.write(strategy.get('investment_rationale', '정보 없음'))
                                st.markdown("**예상 결과**")
                                st.write(strategy.get('expected_outcome', '정보 없음'))
                        
                        with tab3:
                            if 'risk_management' in report:
                                risk_mgmt = report['risk_management']
                                st.markdown("**주요 리스크**")
                                for risk in risk_mgmt.get('key_risks', []):
                                    st.write(f"• {risk}")
                                
                                st.markdown("**모니터링 포인트**")
                                for point in risk_mgmt.get('monitoring_points', []):
                                    st.write(f"• {point}")
                        
                        with tab4:
                            if 'action_plan' in report:
                                action = report['action_plan']
                                st.markdown("**즉시 실행할 액션**")
                                for action_item in action.get('immediate_actions', []):
                                    st.write(f"• {action_item}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("검토 주기", action.get('review_schedule', 'N/A'))
                                with col2:
                                    st.markdown("**성공 지표**")
                                    for metric in action.get('success_metrics', []):
                                        st.write(f"• {metric}")
                        
                        # 면책 조항
                        if 'disclaimer' in report:
                            st.warning(f"⚠️ **투자 유의사항**: {report['disclaimer']}")
                    
            except Exception as e:
                st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")

elif page == "📊 상담 히스토리":
    st.title("📊 투자 상담 히스토리")
    
    # 사용자 ID 입력
    user_id = st.text_input("사용자 ID", value="user123")
    
    if user_id:
        # 히스토리 조회
        with st.spinner("히스토리 로딩 중..."):
            history_list = get_user_history(user_id)
        
        if not history_list:
            st.info("아직 투자 상담 이력이 없습니다.")
        else:
            st.markdown(f"**총 {len(history_list)}건의 상담 이력**")
            
            # 히스토리 목록 표시 (카드 형태)
            for i, consultation in enumerate(history_list):
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{consultation['title']}**")
                        # 태그 표시
                        tag_html = " ".join([
                            f"<span style='background-color: #e1f5fe; padding: 2px 6px; border-radius: 10px; font-size: 12px;'>{tag}</span>" 
                            for tag in consultation['tags']
                        ])
                        st.markdown(tag_html, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f"📅 {consultation['date']}")
                        st.markdown(f"🕐 {consultation['time']}")
                    
                    with col3:
                        if st.button("상세보기", key=f"detail_{i}"):
                            st.session_state[f"show_detail_{i}"] = True
                    
                    # 간단한 요약 정보
                    with st.expander("간단 요약"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("위험성향", consultation['summary']['risk_profile'])
                            st.metric("투자금액", f"{consultation['summary']['investment_amount']:,}원")
                        with col_b:
                            st.markdown("**주요 자산**")
                            st.write(", ".join(consultation['summary']['main_assets']))
                    
                    # 상세 정보 표시
                    if st.session_state.get(f"show_detail_{i}", False):
                        st.markdown("### 📋 상담 상세 내용")
                        
                        detail = consultation['full_data']
                        
                        # 탭으로 구분
                        tab1, tab2, tab3, tab4 = st.tabs(["기본정보", "재무분석", "포트폴리오", "최종리포트"])
                        
                        with tab1:
                            st.json(detail["user_profile"])
                        
                        with tab2:
                            analysis = detail["analysis_results"]
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("위험 성향", analysis["risk_profile"])
                            with col2:
                                st.metric("목표 수익률", f"{analysis['target_return']}%")
                            st.markdown("**투자 전략**")
                            st.write(analysis["investment_strategy"])
                        
                        with tab3:
                            portfolio = analysis["recommended_portfolio"]
                            fig = create_pie_chart(portfolio, "추천 포트폴리오")
                            st.plotly_chart(fig)
                        
                        with tab4:
                            if "final_report" in detail:
                                st.json(detail["final_report"])
                            else:
                                st.info("최종 리포트 정보가 없습니다.")
                        
                        if st.button("상세보기 닫기", key=f"close_{i}"):
                            st.session_state[f"show_detail_{i}"] = False
                            st.rerun()
                    
                    st.divider()