"""
Strands Agent 기반 AI 투자 어드바이저 Streamlit 앱
"""
import streamlit as st
import json
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any

# 페이지 설정
st.set_page_config(
    page_title="AI 투자 어드바이저 (Strands Agent)",
    page_icon="💰",
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
</style>
""", unsafe_allow_html=True)

def main():
    # 메인 헤더
    st.markdown('<div class="main-header">🤖 AI 투자 어드바이저 (Strands Agent)</div>', unsafe_allow_html=True)
    
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
            
            submitted = st.form_submit_button("🚀 투자 분석 시작", use_container_width=True)
        
        # 분석 패턴 설명
        st.markdown("---")
        st.subheader("🔍 Agentic AI 4가지 패턴")
        st.markdown("""
        - **Reflection**: 재무 분석 자체 검증
        - **Tool Use**: 실시간 시장 데이터 활용
        - **Planning**: 시나리오 기반 리스크 관리
        - **Multi-Agent**: 전문가 에이전트 협업
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
        ### 🎯 AI 투자 어드바이저에 오신 것을 환영합니다!
        
        이 시스템은 **Strands Agent**를 활용한 차세대 투자 상담 서비스입니다.
        
        #### 🚀 주요 기능
        - **개인 맞춤형 재무 분석**: AI가 당신의 투자 성향을 정확히 분석
        - **실시간 포트폴리오 설계**: 최신 시장 데이터 기반 투자 전략 수립
        - **지능형 리스크 관리**: 뉴스 분석을 통한 시나리오별 대응 전략
        - **종합 투자 보고서**: 전문가 수준의 상세한 투자 가이드 제공
        
        #### 🤖 Agentic AI 기술
        - **Reflection Pattern**: 분석 결과의 정확성을 자체 검증
        - **Tool Use Pattern**: 실시간 데이터와 외부 API 활용
        - **Planning Pattern**: 체계적인 리스크 시나리오 계획
        - **Multi-Agent Pattern**: 전문 에이전트들의 협업
        
        **👈 왼쪽 사이드바에서 투자 정보를 입력하고 분석을 시작하세요!**
        """)
        
        # 시스템 아키텍처 다이어그램
        st.markdown("---")
        st.subheader("🏗️ 시스템 아키텍처")
        
        # 간단한 플로우차트 시각화
        fig = go.Figure()
        
        # 노드 위치 정의
        nodes = {
            "사용자 입력": (1, 4),
            "재무 분석가": (2, 4),
            "Reflection": (3, 4),
            "포트폴리오 설계사": (4, 4),
            "리스크 관리사": (5, 4),
            "최종 보고서": (6, 4)
        }
        
        # 노드 추가
        for name, (x, y) in nodes.items():
            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode='markers+text',
                marker=dict(size=50, color='lightblue'),
                text=name,
                textposition="middle center",
                showlegend=False
            ))
        
        # 연결선 추가
        connections = [
            ("사용자 입력", "재무 분석가"),
            ("재무 분석가", "Reflection"),
            ("Reflection", "포트폴리오 설계사"),
            ("포트폴리오 설계사", "리스크 관리사"),
            ("리스크 관리사", "최종 보고서")
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
            title="AI 투자 어드바이저 처리 흐름",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)


def run_investment_analysis(user_input: Dict[str, Any]):
    """투자 분석 실행"""
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 투자 어드바이저 import 및 초기화
        status_text.text("🔧 AI 에이전트 시스템 초기화 중...")
        progress_bar.progress(10)
        
        from agents.lab4_investment_advisor import InvestmentAdvisor
        advisor = InvestmentAdvisor()
        
        # 분석 실행
        status_text.text("🤖 AI 투자 분석 수행 중...")
        progress_bar.progress(30)
        
        result = advisor.process_investment_request(user_input)
        progress_bar.progress(100)
        status_text.text("✅ 분석 완료!")
        
        # 결과 표시
        display_analysis_results(user_input, result)
        
    except Exception as e:
        st.error(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")
        st.markdown("""
        ### 🔧 문제 해결 방법
        1. `.env` 파일에 `ANTHROPIC_API_KEY`가 올바르게 설정되어 있는지 확인하세요
        2. 필요한 패키지가 모두 설치되어 있는지 확인하세요: `pip install -r requirements.txt`
        3. 인터넷 연결을 확인하세요 (실시간 데이터 조회 필요)
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 최종 보고서", 
        "💰 재무 분석", 
        "📈 포트폴리오", 
        "⚠️ 리스크 분석",
        "🔍 상세 데이터"
    ])
    
    with tab1:
        display_final_report(result.get('final_report', ''))
    
    with tab2:
        display_financial_analysis(result.get('financial_analysis', {}))
    
    with tab3:
        display_portfolio_analysis(result.get('portfolio_result', {}))
    
    with tab4:
        display_risk_analysis(result.get('risk_result', {}))
    
    with tab5:
        display_detailed_data(user_input, result)


def display_final_report(report: str):
    """최종 보고서 표시"""
    st.markdown('<div class="step-header">📋 투자 포트폴리오 분석 보고서</div>', unsafe_allow_html=True)
    
    if report:
        st.markdown(report)
    else:
        st.warning("보고서를 생성할 수 없습니다.")


def display_financial_analysis(financial_data: Dict[str, Any]):
    """재무 분석 결과 표시"""
    st.markdown('<div class="step-header">💰 재무 분석 결과 (Reflection Pattern)</div>', unsafe_allow_html=True)
    
    if not financial_data or 'analysis' not in financial_data:
        st.warning("재무 분석 데이터가 없습니다.")
        return
    
    analysis = financial_data['analysis']
    
    # 메트릭 표시
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "위험 성향",
            analysis.get('risk_profile', 'N/A'),
            help="투자자의 위험 감수 성향"
        )
    
    with col2:
        return_rate = analysis.get('required_annual_return_rate', 0)
        st.metric(
            "필요 수익률",
            f"{return_rate:.2f}%",
            help="목표 달성을 위한 연간 수익률"
        )
    
    with col3:
        validation_status = "✅ 검증 통과" if financial_data.get('is_valid') else "❌ 검증 실패"
        st.metric(
            "Reflection 검증",
            validation_status,
            help="AI 자체 검증 결과"
        )
    
    # 상세 분석
    st.subheader("📝 위험 성향 분석")
    st.write(analysis.get('risk_profile_reason', ''))
    
    st.subheader("📊 수익률 계산 근거")
    st.write(analysis.get('return_rate_reason', ''))
    
    # Reflection 결과
    st.subheader("🔍 AI 자체 검증 결과")
    reflection_result = financial_data.get('reflection_result', '')
    if financial_data.get('is_valid'):
        st.success(f"검증 통과: {reflection_result}")
    else:
        st.error(f"검증 실패: {reflection_result}")


def display_portfolio_analysis(portfolio_data: Dict[str, Any]):
    """포트폴리오 분석 결과 표시"""
    st.markdown('<div class="step-header">📈 포트폴리오 설계 (Tool Use Pattern)</div>', unsafe_allow_html=True)
    
    if not portfolio_data or 'portfolio' not in portfolio_data:
        st.warning("포트폴리오 데이터가 없습니다.")
        return
    
    portfolio = portfolio_data['portfolio']
    allocation = portfolio.get('portfolio_allocation', {})
    
    if not allocation:
        st.warning("포트폴리오 배분 데이터가 없습니다.")
        return
    
    # 포트폴리오 배분 차트
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # 파이 차트
        fig_pie = px.pie(
            values=list(allocation.values()),
            names=list(allocation.keys()),
            title="포트폴리오 자산 배분"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # 바 차트
        fig_bar = px.bar(
            x=list(allocation.keys()),
            y=list(allocation.values()),
            title="자산별 배분 비율 (%)",
            labels={'x': 'ETF', 'y': '배분 비율 (%)'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # 포트폴리오 상세 정보
    st.subheader("💡 투자 전략")
    st.write(portfolio.get('strategy', ''))
    
    st.subheader("📋 구성 근거")
    st.write(portfolio.get('reason', ''))
    
    # 배분 테이블
    st.subheader("📊 자산 배분 상세")
    df = pd.DataFrame([
        {"ETF": ticker, "배분 비율 (%)": ratio, "설명": "ETF 설명"}
        for ticker, ratio in allocation.items()
    ])
    st.dataframe(df, use_container_width=True)


def display_risk_analysis(risk_data: Dict[str, Any]):
    """리스크 분석 결과 표시"""
    st.markdown('<div class="step-header">⚠️ 리스크 분석 (Planning Pattern)</div>', unsafe_allow_html=True)
    
    if not risk_data or 'risk_analysis' not in risk_data:
        st.warning("리스크 분석 데이터가 없습니다.")
        return
    
    risk_analysis = risk_data['risk_analysis']
    
    # 시나리오별 분석
    for i, scenario_key in enumerate(['scenario1', 'scenario2'], 1):
        if scenario_key not in risk_analysis:
            continue
            
        scenario = risk_analysis[scenario_key]
        
        st.subheader(f"🎯 시나리오 {i}: {scenario.get('name', '')}")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📝 시나리오 설명**")
            st.write(scenario.get('description', ''))
            
            st.markdown("**💡 대응 전략**")
            st.write(scenario.get('reason', ''))
        
        with col2:
            # 조정된 포트폴리오 배분
            allocation = scenario.get('allocation_management', {})
            if allocation:
                fig = px.pie(
                    values=list(allocation.values()),
                    names=list(allocation.keys()),
                    title=f"시나리오 {i} 조정 포트폴리오"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")


def display_detailed_data(user_input: Dict[str, Any], result: Dict[str, Any]):
    """상세 데이터 표시"""
    st.markdown('<div class="step-header">🔍 상세 분석 데이터</div>', unsafe_allow_html=True)
    
    # 사용자 입력
    st.subheader("📥 사용자 입력 데이터")
    st.json(user_input)
    
    # 전체 결과 데이터
    st.subheader("📊 전체 분석 결과")
    
    # 민감한 정보 제거
    display_result = result.copy()
    if 'final_report' in display_result:
        display_result['final_report'] = "... (위 탭에서 확인)"
    
    st.json(display_result)


if __name__ == "__main__":
    main()