"""
Lab 4: Investment Advisor Streamlit App
투자 어드바이저 + Multi-Agent 패턴 시연 앱 (통합 시스템)
"""
import streamlit as st
import json
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 페이지 설정
st.set_page_config(
    page_title="Lab 4: AI 투자 어드바이저 (Multi-Agent Pattern)",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .step-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2e8b57;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .agent-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        color: #495057;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # 메인 헤더
    st.markdown('<div class="main-header">🤖 Lab 4: AI 투자 어드바이저 (Multi-Agent Pattern)</div>', unsafe_allow_html=True)
    
    # 패턴 설명
    st.markdown("""
    ### 🎯 Multi-Agent Pattern이란?
    여러 전문가 AI 에이전트들이 협업하여 복잡한 작업을 수행하는 패턴입니다.
    - **Lab 1**: 재무 분석가 (Reflection Pattern) 
    - **Lab 2**: 포트폴리오 설계사 (Tool Use Pattern)
    - **Lab 3**: 리스크 관리사 (Planning Pattern)
    - **Lab 4**: 보고서 생성가 + 전체 통합 관리
    """)
    
    # 사이드바 - 사용자 입력
    with st.sidebar:
        st.header("📊 투자 정보 입력")
        
        # 사용자 입력 폼
        with st.form("investment_form"):
            st.subheader("기본 정보")
            total_amount = st.number_input(
                "총 투자 가능 금액 (원)",
                min_value=1000000,
                max_value=10000000000,
                value=50000000,
                step=1000000,
                help="1년 동안 투자에 사용할 수 있는 총 금액"
            )
            
            age = st.number_input(
                "나이 (세)",
                min_value=20,
                max_value=80,
                value=35,
                step=1
            )
            
            experience = st.number_input(
                "주식 투자 경험 (년)",
                min_value=0,
                max_value=50,
                value=10,
                step=1
            )
            
            target_amount = st.number_input(
                "1년 후 목표 금액 (원)",
                min_value=total_amount,
                max_value=total_amount * 3,
                value=70000000,
                step=1000000
            )
            
            submitted = st.form_submit_button("🚀 종합 투자 분석 시작", use_container_width=True)
        
        # Multi-Agent Pattern 설명
        st.markdown("---")
        st.subheader("🤖 참여 에이전트")
        st.markdown("""
        1. **재무 분석가**: Reflection Pattern
        2. **포트폴리오 설계사**: Tool Use Pattern  
        3. **리스크 관리사**: Planning Pattern
        4. **보고서 생성가**: 최종 통합 보고서
        """)
        
        # 처리 단계
        st.subheader("📋 처리 단계")
        st.markdown("""
        1. 재무 상황 분석 및 검증
        2. 실시간 데이터 기반 포트폴리오 설계
        3. 뉴스 기반 리스크 시나리오 분석
        4. 종합 투자 보고서 생성
        """)
    
    # 메인 컨텐츠
    if submitted:
        # 사용자 입력 데이터 구성
        user_input = {
            "total_investable_amount": int(total_amount),
            "age": int(age),
            "stock_investment_experience_years": int(experience),
            "target_amount": int(target_amount)
        }
        
        # 투자 분석 실행
        run_investment_analysis(user_input)
    else:
        # 초기 화면
        show_welcome_screen()


def show_welcome_screen():
    """초기 환영 화면"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ### 🎯 Lab 4: AI 투자 어드바이저에 오신 것을 환영합니다!
        
        이 시스템은 **Multi-Agent Pattern**을 활용한 종합 AI 투자 상담 서비스입니다.
        
        #### 🚀 주요 기능
        - **4개 전문가 AI 협업**: 각 분야 전문가들의 체계적 협업
        - **4가지 Agentic Pattern**: Reflection, Tool Use, Planning, Multi-Agent 통합
        - **종합적 분석**: 재무분석부터 리스크관리까지 원스톱 서비스
        - **전문가급 보고서**: 실무에서 사용 가능한 수준의 상세 보고서
        
        #### 🤖 Multi-Agent Pattern의 장점
        - **전문성**: 각 에이전트가 특정 분야에 특화
        - **협업**: 에이전트 간 정보 공유 및 협력
        - **품질**: 다단계 검증을 통한 높은 신뢰성
        - **확장성**: 새로운 전문가 에이전트 쉽게 추가
        - **투명성**: 각 단계별 처리 과정 추적 가능
        
        **👈 왼쪽 사이드바에서 투자 정보를 입력하고 종합 분석을 시작하세요!**
        """)
        
        # Multi-Agent Pattern 아키텍처 다이어그램
        st.markdown("---")
        st.subheader("🏗️ Multi-Agent 시스템 아키텍처")
        
        # 복잡한 플로우차트 시각화
        fig = go.Figure()
        
        # 노드 위치 정의 (더 복잡한 구조)
        nodes = {
            "사용자 입력": (1, 4),
            "투자 어드바이저": (2, 4),
            "재무 분석가": (3, 5.5),
            "Reflection AI": (4, 5.5),
            "포트폴리오 설계사": (3, 4),
            "시장 데이터 도구": (4, 4),
            "리스크 관리사": (3, 2.5),
            "뉴스 분석 도구": (4, 2.5),
            "보고서 생성가": (5, 4),
            "최종 보고서": (6, 4)
        }
        
        colors = {
            "사용자 입력": "lightblue",
            "투자 어드바이저": "lightgreen",
            "재무 분석가": "lightyellow",
            "Reflection AI": "lightcoral",
            "포트폴리오 설계사": "lightyellow",
            "시장 데이터 도구": "lightpink",
            "리스크 관리사": "lightyellow",
            "뉴스 분석 도구": "lightpink",
            "보고서 생성가": "lightcyan",
            "최종 보고서": "lightgray"
        }
        
        # 노드 추가
        for name, (x, y) in nodes.items():
            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode='markers+text',
                marker=dict(size=50, color=colors[name]),
                text=name,
                textposition="middle center",
                showlegend=False,
                textfont=dict(size=8)
            ))
        
        # 연결선 추가 (더 복잡한 연결)
        connections = [
            ("사용자 입력", "투자 어드바이저"),
            ("투자 어드바이저", "재무 분석가"),
            ("재무 분석가", "Reflection AI"),
            ("Reflection AI", "포트폴리오 설계사"),
            ("포트폴리오 설계사", "시장 데이터 도구"),
            ("시장 데이터 도구", "리스크 관리사"),
            ("리스크 관리사", "뉴스 분석 도구"),
            ("뉴스 분석 도구", "보고서 생성가"),
            ("보고서 생성가", "최종 보고서")
        ]
        
        for start, end in connections:
            x0, y0 = nodes[start]
            x1, y1 = nodes[end]
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1],
                mode='lines',
                line=dict(color='gray', width=2),
                showlegend=False
            ))
        
        fig.update_layout(
            title="Multi-Agent 투자 어드바이저 시스템",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=400,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)


def run_investment_analysis(user_input: Dict[str, Any]):
    """투자 분석 실행"""
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 에이전트별 상태 표시
    agent_status = st.empty()
    
    try:
        # 투자 어드바이저 import 및 초기화
        status_text.text("🔧 Multi-Agent 시스템 초기화 중...")
        agent_status.markdown("""
        <div class="agent-box">
        🤖 <strong>시스템 상태</strong><br>
        • 재무 분석가: 대기 중<br>
        • 포트폴리오 설계사: 대기 중<br>
        • 리스크 관리사: 대기 중<br>
        • 보고서 생성가: 대기 중
        </div>
        """, unsafe_allow_html=True)
        progress_bar.progress(10)
        
        from agent import InvestmentAdvisor
        advisor = InvestmentAdvisor()
        
        # Step 1: 재무 분석
        status_text.text("💰 재무 분석가 (Reflection Pattern) 실행 중...")
        agent_status.markdown("""
        <div class="agent-box">
        🤖 <strong>시스템 상태</strong><br>
        • 재무 분석가: ✅ 실행 중 (Reflection Pattern)<br>
        • 포트폴리오 설계사: 대기 중<br>
        • 리스크 관리사: 대기 중<br>
        • 보고서 생성가: 대기 중
        </div>
        """, unsafe_allow_html=True)
        progress_bar.progress(30)
        
        # Step 2: 포트폴리오 설계
        status_text.text("📈 포트폴리오 설계사 (Tool Use Pattern) 실행 중...")
        agent_status.markdown("""
        <div class="agent-box">
        🤖 <strong>시스템 상태</strong><br>
        • 재무 분석가: ✅ 완료<br>
        • 포트폴리오 설계사: ✅ 실행 중 (Tool Use Pattern)<br>
        • 리스크 관리사: 대기 중<br>
        • 보고서 생성가: 대기 중
        </div>
        """, unsafe_allow_html=True)
        progress_bar.progress(50)
        
        # Step 3: 리스크 분석
        status_text.text("⚠️ 리스크 관리사 (Planning Pattern) 실행 중...")
        agent_status.markdown("""
        <div class="agent-box">
        🤖 <strong>시스템 상태</strong><br>
        • 재무 분석가: ✅ 완료<br>
        • 포트폴리오 설계사: ✅ 완료<br>
        • 리스크 관리사: ✅ 실행 중 (Planning Pattern)<br>
        • 보고서 생성가: 대기 중
        </div>
        """, unsafe_allow_html=True)
        progress_bar.progress(70)
        
        # Step 4: 보고서 생성
        status_text.text("📋 보고서 생성가 실행 중...")
        agent_status.markdown("""
        <div class="agent-box">
        🤖 <strong>시스템 상태</strong><br>
        • 재무 분석가: ✅ 완료<br>
        • 포트폴리오 설계사: ✅ 완료<br>
        • 리스크 관리사: ✅ 완료<br>
        • 보고서 생성가: ✅ 실행 중
        </div>
        """, unsafe_allow_html=True)
        progress_bar.progress(90)
        
        # 실제 분석 실행
        result = advisor.process_investment_request(user_input)
        
        progress_bar.progress(100)
        status_text.text("✅ Multi-Agent 분석 완료!")
        agent_status.markdown("""
        <div class="agent-box">
        🤖 <strong>시스템 상태</strong><br>
        • 재무 분석가: ✅ 완료<br>
        • 포트폴리오 설계사: ✅ 완료<br>
        • 리스크 관리사: ✅ 완료<br>
        • 보고서 생성가: ✅ 완료
        </div>
        """, unsafe_allow_html=True)
        
        # 결과 표시
        display_analysis_results(user_input, result)
        
    except Exception as e:
        st.error(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")
        st.markdown("""
        ### 🔧 문제 해결 방법
        1. `.env` 파일에 `ANTHROPIC_API_KEY`가 올바르게 설정되어 있는지 확인하세요
        2. 필요한 패키지가 모두 설치되어 있는지 확인하세요: `pip install -r requirements.txt`
        3. 인터넷 연결을 확인하세요 (실시간 데이터 조회 필요)
        4. 각 Lab 폴더의 agent.py 파일이 올바르게 구성되어 있는지 확인하세요
        """)


def display_analysis_results(user_input: Dict[str, Any], result: Dict[str, Any]):
    """분석 결과 표시"""
    
    if result['status'] != 'success':
        st.markdown(f'<div class="error-box">❌ {result["message"]}</div>', unsafe_allow_html=True)
        
        # 오류 상세 정보
        with st.expander("🔍 오류 상세 정보"):
            st.json(result)
        return
    
    # 성공 메시지
    st.markdown(f'<div class="success-box">✅ {result["message"]}</div>', unsafe_allow_html=True)
    
    # 탭으로 결과 구성
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 최종 보고서", 
        "🤖 Multi-Agent 협업", 
        "💰 재무 분석", 
        "📈 포트폴리오", 
        "⚠️ 리스크 분석",
        "📊 종합 시각화"
    ])
    
    with tab1:
        display_final_report(result.get('final_report', ''))
    
    with tab2:
        display_multi_agent_collaboration(result)
    
    with tab3:
        display_financial_analysis(result.get('financial_analysis', {}))
    
    with tab4:
        display_portfolio_analysis(result.get('portfolio_result', {}))
    
    with tab5:
        display_risk_analysis(result.get('risk_result', {}))
    
    with tab6:
        display_comprehensive_visualization(user_input, result)


def display_final_report(report: str):
    """최종 보고서 표시"""
    st.markdown('<div class="step-header">📋 종합 투자 포트폴리오 분석 보고서</div>', unsafe_allow_html=True)
    
    if report:
        st.markdown(report)
    else:
        st.warning("보고서를 생성할 수 없습니다.")


def display_multi_agent_collaboration(result: Dict[str, Any]):
    """Multi-Agent 협업 과정 표시"""
    st.markdown('<div class="step-header">🤖 Multi-Agent Pattern 협업 과정</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-box">4개의 전문가 AI 에이전트가 순차적으로 협업하여 종합적인 투자 분석을 수행했습니다.</div>', unsafe_allow_html=True)
    
    # 각 에이전트별 결과 요약
    agents_summary = [
        {
            "에이전트": "🔄 재무 분석가 (Lab 1)",
            "패턴": "Reflection Pattern",
            "역할": "사용자 재무 상황 분석 및 자체 검증",
            "상태": "✅ 완료" if result.get('financial_analysis', {}).get('is_valid') else "❌ 검증 실패",
            "주요 결과": f"위험 성향: {result.get('financial_analysis', {}).get('analysis', {}).get('risk_profile', 'N/A')}"
        },
        {
            "에이전트": "🛠️ 포트폴리오 설계사 (Lab 2)",
            "패턴": "Tool Use Pattern",
            "역할": "실시간 시장 데이터 기반 포트폴리오 설계",
            "상태": "✅ 완료" if result.get('portfolio_result', {}).get('status') == 'success' else "❌ 실패",
            "주요 결과": f"ETF 조합: {', '.join(result.get('portfolio_result', {}).get('portfolio', {}).get('portfolio_allocation', {}).keys())}"
        },
        {
            "에이전트": "📋 리스크 관리사 (Lab 3)",
            "패턴": "Planning Pattern",
            "역할": "뉴스 분석 기반 리스크 시나리오 계획",
            "상태": "✅ 완료" if result.get('risk_result', {}).get('status') == 'success' else "❌ 실패",
            "주요 결과": f"시나리오 수: {len([k for k in result.get('risk_result', {}).get('risk_analysis', {}).keys() if k.startswith('scenario')])}"
        },
        {
            "에이전트": "📄 보고서 생성가 (Lab 4)",
            "패턴": "Integration Pattern",
            "역할": "전체 결과 통합 및 최종 보고서 생성",
            "상태": "✅ 완료" if result.get('final_report') else "❌ 실패",
            "주요 결과": "종합 투자 보고서 생성 완료"
        }
    ]
    
    for agent in agents_summary:
        with st.expander(f"{agent['에이전트']} - {agent['패턴']}"):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.write(f"**역할**: {agent['역할']}")
                st.write(f"**상태**: {agent['상태']}")
            
            with col2:
                st.write(f"**주요 결과**: {agent['주요 결과']}")
    
    # Multi-Agent Pattern 설명
    st.subheader("📚 Multi-Agent Pattern의 특징")
    st.markdown("""
    **Multi-Agent Pattern**은 여러 전문가 AI가 협업하는 패턴입니다:
    
    1. **전문화**: 각 에이전트가 특정 분야에 특화된 전문성 보유
    2. **협업**: 에이전트 간 정보 공유 및 순차적 협력
    3. **검증**: 다단계 검증을 통한 높은 품질 보장
    4. **확장성**: 새로운 전문가 에이전트 쉽게 추가 가능
    5. **투명성**: 각 단계별 처리 과정 및 결과 추적 가능
    6. **신뢰성**: 여러 관점에서의 종합적 분석으로 신뢰도 향상
    
    이를 통해 단일 AI로는 달성하기 어려운 전문성과 신뢰성을 제공할 수 있습니다.
    """)


def display_financial_analysis(financial_data: Dict[str, Any]):
    """재무 분석 결과 표시 (간략 버전)"""
    st.markdown('<div class="step-header">💰 재무 분석 결과 (Lab 1)</div>', unsafe_allow_html=True)
    
    if not financial_data or 'analysis' not in financial_data:
        st.warning("재무 분석 데이터가 없습니다.")
        return
    
    analysis = financial_data['analysis']
    
    # 핵심 메트릭만 표시
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("위험 성향", analysis.get('risk_profile', 'N/A'))
    
    with col2:
        return_rate = analysis.get('required_annual_return_rate', 0)
        st.metric("필요 수익률", f"{return_rate:.2f}%")
    
    with col3:
        validation_status = "✅ 검증 통과" if financial_data.get('is_valid') else "❌ 검증 실패"
        st.metric("Reflection 검증", validation_status)


def display_portfolio_analysis(portfolio_data: Dict[str, Any]):
    """포트폴리오 분석 결과 표시 (간략 버전)"""
    st.markdown('<div class="step-header">📈 포트폴리오 설계 결과 (Lab 2)</div>', unsafe_allow_html=True)
    
    if not portfolio_data or 'portfolio' not in portfolio_data:
        st.warning("포트폴리오 데이터가 없습니다.")
        return
    
    portfolio = portfolio_data['portfolio']
    allocation = portfolio.get('portfolio_allocation', {})
    
    if allocation:
        # 간단한 파이 차트
        fig_pie = px.pie(
            values=list(allocation.values()),
            names=list(allocation.keys()),
            title="포트폴리오 자산 배분"
        )
        st.plotly_chart(fig_pie, use_container_width=True)


def display_risk_analysis(risk_data: Dict[str, Any]):
    """리스크 분석 결과 표시 (간략 버전)"""
    st.markdown('<div class="step-header">⚠️ 리스크 분석 결과 (Lab 3)</div>', unsafe_allow_html=True)
    
    if not risk_data or 'risk_analysis' not in risk_data:
        st.warning("리스크 분석 데이터가 없습니다.")
        return
    
    risk_analysis = risk_data['risk_analysis']
    
    # 시나리오 개수만 표시
    scenario_count = len([k for k in risk_analysis.keys() if k.startswith('scenario')])
    st.metric("도출된 시나리오 수", f"{scenario_count}개")
    
    # 시나리오 이름만 표시
    for i, scenario_key in enumerate(['scenario1', 'scenario2'], 1):
        if scenario_key in risk_analysis:
            scenario = risk_analysis[scenario_key]
            st.write(f"**시나리오 {i}**: {scenario.get('name', '')}")


def display_comprehensive_visualization(user_input: Dict[str, Any], result: Dict[str, Any]):
    """종합 시각화"""
    st.markdown('<div class="step-header">📊 종합 분석 시각화</div>', unsafe_allow_html=True)
    
    # 전체 프로세스 요약
    col1, col2 = st.columns(2)
    
    with col1:
        # 투자 목표 vs 현실
        target_return = ((user_input['target_amount'] - user_input['total_investable_amount']) / user_input['total_investable_amount']) * 100
        
        fig_target = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = target_return,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "목표 수익률 (%)"},
            gauge = {
                'axis': {'range': [None, 50]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 10], 'color': "lightgray"},
                    {'range': [10, 20], 'color': "yellow"},
                    {'range': [20, 30], 'color': "orange"},
                    {'range': [30, 50], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': target_return
                }
            }
        ))
        fig_target.update_layout(height=300)
        st.plotly_chart(fig_target, use_container_width=True)
    
    with col2:
        # 에이전트 성공률
        success_data = {
            "재무 분석가": 1 if result.get('financial_analysis', {}).get('is_valid') else 0,
            "포트폴리오 설계사": 1 if result.get('portfolio_result', {}).get('status') == 'success' else 0,
            "리스크 관리사": 1 if result.get('risk_result', {}).get('status') == 'success' else 0,
            "보고서 생성가": 1 if result.get('final_report') else 0
        }
        
        fig_success = px.bar(
            x=list(success_data.keys()),
            y=list(success_data.values()),
            title="에이전트별 성공률",
            labels={'x': '에이전트', 'y': '성공 (1) / 실패 (0)'},
            color=list(success_data.values()),
            color_continuous_scale='RdYlGn'
        )
        fig_success.update_layout(height=300)
        st.plotly_chart(fig_success, use_container_width=True)
    
    # 전체 결과 요약 테이블
    st.subheader("📋 분석 결과 요약")
    
    summary_data = {
        "항목": ["투자 가능 금액", "목표 금액", "필요 수익률", "위험 성향", "제안 ETF 수", "리스크 시나리오"],
        "값": [
            f"{user_input['total_investable_amount']:,}원",
            f"{user_input['target_amount']:,}원", 
            f"{target_return:.1f}%",
            result.get('financial_analysis', {}).get('analysis', {}).get('risk_profile', 'N/A'),
            len(result.get('portfolio_result', {}).get('portfolio', {}).get('portfolio_allocation', {})),
            len([k for k in result.get('risk_result', {}).get('risk_analysis', {}).keys() if k.startswith('scenario')])
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True)


if __name__ == "__main__":
    main()