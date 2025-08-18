"""
Lab 2: Portfolio Architect Streamlit App
포트폴리오 설계사 + Tool Use 패턴 시연 앱
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
from config import AVAILABLE_PRODUCTS

# 페이지 설정
st.set_page_config(
    page_title="Lab 2: AI 포트폴리오 설계사 (Tool Use Pattern)",
    page_icon="📈",
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
    .tool-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # 메인 헤더
    st.markdown('<div class="main-header">🛠️ Lab 2: AI 포트폴리오 설계사 (Tool Use Pattern)</div>', unsafe_allow_html=True)
    
    # 패턴 설명
    st.markdown("""
    ### 🎯 Tool Use Pattern이란?
    AI가 외부 도구와 API를 활용하여 실시간 데이터를 기반으로 작업하는 패턴입니다.
    - **도구 1**: `get_available_products()` - 투자 상품 목록 조회
    - **도구 2**: `get_product_data(ticker)` - 실시간 가격 데이터 조회
    - **결과**: 실시간 시장 데이터 기반 포트폴리오 설계
    """)
    
    # 사이드바 - 재무 분석 입력
    with st.sidebar:
        st.header("💰 재무 분석 결과 입력")
        
        # 재무 분석 결과 입력 폼
        with st.form("portfolio_design_form"):
            st.subheader("Lab 1 결과 또는 직접 입력")
            
            risk_profile = st.selectbox(
                "위험 성향",
                ["매우 보수적", "보수적", "중립적", "공격적", "매우 공격적"],
                index=3,
                help="투자자의 위험 감수 성향"
            )
            
            required_return = st.number_input(
                "필요 연간 수익률 (%)",
                min_value=0.0,
                max_value=100.0,
                value=40.0,
                step=0.1,
                help="목표 달성을 위한 연간 수익률"
            )
            
            risk_reason = st.text_area(
                "위험 성향 평가 근거",
                value="나이가 35세로 젊고, 주식 투자 경험이 10년으로 상당히 많으며, 총 투자 가능 금액이 5000만원으로 상당히 높은 편입니다.",
                help="위험 성향 평가에 대한 상세한 설명"
            )
            
            return_reason = st.text_area(
                "수익률 계산 근거",
                value="필요 연간 수익률은 (70000000 - 50000000) / 50000000 * 100 = 40.00%입니다.",
                help="필요 연간 수익률 계산 과정과 의미"
            )
            
            submitted = st.form_submit_button("📈 포트폴리오 설계 시작", use_container_width=True)
        
        # Tool Use Pattern 설명
        st.markdown("---")
        st.subheader("🛠️ 사용 도구")
        st.markdown("""
        1. **상품 조회**: 20개 ETF 목록 확인
        2. **가격 조회**: 실시간 시장 데이터 수집
        3. **분석**: 데이터 기반 포트폴리오 구성
        """)
        
        # 사용 가능한 상품 미리보기
        st.subheader("📊 투자 상품 목록")
        with st.expander("사용 가능한 ETF 보기"):
            for ticker, description in list(AVAILABLE_PRODUCTS.items())[:10]:
                st.write(f"**{ticker}**: {description}")
            st.write(f"... 총 {len(AVAILABLE_PRODUCTS)}개 상품")
    
    # 메인 컨텐츠
    if submitted:
        # 재무 분석 데이터 구성
        financial_analysis = {
            "risk_profile": risk_profile,
            "risk_profile_reason": risk_reason,
            "required_annual_return_rate": required_return,
            "return_rate_reason": return_reason
        }
        
        # 포트폴리오 설계 실행
        run_portfolio_design(financial_analysis)
    else:
        # 초기 화면
        show_welcome_screen()


def show_welcome_screen():
    """초기 환영 화면"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ### 🎯 Lab 2: AI 포트폴리오 설계사에 오신 것을 환영합니다!
        
        이 시스템은 **Tool Use Pattern**을 활용한 AI 포트폴리오 설계 서비스입니다.
        
        #### 🚀 주요 기능
        - **실시간 데이터 활용**: Yahoo Finance API를 통한 최신 시장 데이터
        - **20개 ETF 분석**: 다양한 자산군의 투자 상품 비교
        - **최적 포트폴리오**: 3개 ETF 조합으로 최적 배분 제안
        - **데이터 기반 결정**: 실제 가격 데이터를 바탕으로 한 합리적 배분
        
        #### 🛠️ Tool Use Pattern의 장점
        - **실시간성**: 최신 시장 상황 반영
        - **정확성**: 실제 데이터 기반 분석
        - **확장성**: 새로운 도구 쉽게 추가 가능
        - **투명성**: 사용한 도구와 데이터 추적 가능
        
        **👈 왼쪽 사이드바에서 재무 분석 결과를 입력하고 설계를 시작하세요!**
        """)
        
        # Tool Use Pattern 플로우차트
        st.markdown("---")
        st.subheader("🛠️ Tool Use Pattern 처리 흐름")
        
        # 간단한 플로우차트 시각화
        fig = go.Figure()
        
        # 노드 위치 정의
        nodes = {
            "재무 분석 결과": (1, 4),
            "포트폴리오 설계사": (2, 4),
            "상품 목록 조회": (3, 5),
            "가격 데이터 조회": (3, 3),
            "데이터 분석": (4, 4),
            "포트폴리오 제안": (5, 4)
        }
        
        colors = {
            "재무 분석 결과": "lightblue",
            "포트폴리오 설계사": "lightgreen",
            "상품 목록 조회": "lightyellow",
            "가격 데이터 조회": "lightyellow", 
            "데이터 분석": "lightcoral",
            "포트폴리오 제안": "lightgray"
        }
        
        # 노드 추가
        for name, (x, y) in nodes.items():
            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode='markers+text',
                marker=dict(size=60, color=colors[name]),
                text=name,
                textposition="middle center",
                showlegend=False,
                textfont=dict(size=9)
            ))
        
        # 연결선 추가
        connections = [
            ("재무 분석 결과", "포트폴리오 설계사"),
            ("포트폴리오 설계사", "상품 목록 조회"),
            ("포트폴리오 설계사", "가격 데이터 조회"),
            ("상품 목록 조회", "데이터 분석"),
            ("가격 데이터 조회", "데이터 분석"),
            ("데이터 분석", "포트폴리오 제안")
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
            title="Tool Use Pattern 처리 흐름",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=350,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)


def run_portfolio_design(financial_analysis: Dict[str, Any]):
    """포트폴리오 설계 실행"""
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 포트폴리오 설계사 import 및 초기화
        status_text.text("🔧 AI 포트폴리오 설계사 초기화 중...")
        progress_bar.progress(20)
        
        from agent import PortfolioArchitect
        architect = PortfolioArchitect()
        
        # 도구 사용 단계별 표시
        status_text.text("🛠️ 투자 상품 목록 조회 중...")
        progress_bar.progress(40)
        
        status_text.text("📊 실시간 가격 데이터 수집 중...")
        progress_bar.progress(60)
        
        status_text.text("🤖 포트폴리오 설계 수행 중...")
        progress_bar.progress(80)
        
        result = architect.design_portfolio(financial_analysis)
        progress_bar.progress(100)
        status_text.text("✅ 설계 완료!")
        
        # 결과 표시
        display_portfolio_results(financial_analysis, result)
        
    except Exception as e:
        st.error(f"❌ 설계 중 오류가 발생했습니다: {str(e)}")
        st.markdown("""
        ### 🔧 문제 해결 방법
        1. `.env` 파일에 `ANTHROPIC_API_KEY`가 올바르게 설정되어 있는지 확인하세요
        2. 인터넷 연결을 확인하세요 (실시간 데이터 조회 필요)
        3. yfinance 패키지가 설치되어 있는지 확인하세요
        """)


def display_portfolio_results(financial_analysis: Dict[str, Any], result: Dict[str, Any]):
    """포트폴리오 설계 결과 표시"""
    
    if result['status'] != 'success':
        st.markdown(f'<div class="error-box">❌ 포트폴리오 설계 실패: {result.get("error", "Unknown error")}</div>', unsafe_allow_html=True)
        
        # 원시 응답 표시
        if result.get('raw_response'):
            with st.expander("🔍 AI 응답 내용 보기"):
                st.text(result['raw_response'])
        return
    
    st.markdown('<div class="success-box">✅ Tool Use Pattern으로 포트폴리오 설계 완료!</div>', unsafe_allow_html=True)
    
    portfolio = result['portfolio']
    
    # 탭으로 결과 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 포트폴리오", 
        "🛠️ 도구 사용", 
        "📊 시각화",
        "📋 상세 데이터"
    ])
    
    with tab1:
        display_portfolio_analysis(portfolio)
    
    with tab2:
        display_tool_usage(result)
    
    with tab3:
        display_portfolio_visualization(portfolio)
    
    with tab4:
        display_detailed_data(financial_analysis, result)


def display_portfolio_analysis(portfolio: Dict[str, Any]):
    """포트폴리오 분석 결과 표시"""
    st.markdown('<div class="step-header">📈 포트폴리오 구성</div>', unsafe_allow_html=True)
    
    allocation = portfolio.get('portfolio_allocation', {})
    
    if not allocation:
        st.warning("포트폴리오 배분 데이터가 없습니다.")
        return
    
    # 배분 테이블
    st.subheader("📊 자산 배분")
    df_allocation = []
    for ticker, ratio in allocation.items():
        description = AVAILABLE_PRODUCTS.get(ticker, "설명 없음")
        df_allocation.append({
            "ETF": ticker,
            "배분 비율 (%)": ratio,
            "설명": description
        })
    
    df = pd.DataFrame(df_allocation)
    st.dataframe(df, use_container_width=True)
    
    # 전략 및 근거
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💡 투자 전략")
        st.write(portfolio.get('strategy', ''))
    
    with col2:
        st.subheader("📋 구성 근거")
        st.write(portfolio.get('reason', ''))


def display_tool_usage(result: Dict[str, Any]):
    """도구 사용 내역 표시"""
    st.markdown('<div class="step-header">🛠️ Tool Use Pattern 실행 내역</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="tool-box">이 포트폴리오는 다음 도구들을 사용하여 설계되었습니다:</div>', unsafe_allow_html=True)
    
    # 사용된 도구들
    tools_used = [
        {
            "도구명": "get_available_products()",
            "목적": "투자 상품 목록 조회",
            "설명": f"총 {len(AVAILABLE_PRODUCTS)}개의 ETF 상품 정보를 조회했습니다.",
            "상태": "✅ 성공"
        },
        {
            "도구명": "get_product_data(ticker)",
            "목적": "실시간 가격 데이터 조회", 
            "설명": "선택된 ETF들의 최근 100일간 가격 데이터를 수집했습니다.",
            "상태": "✅ 성공"
        }
    ]
    
    for tool in tools_used:
        with st.expander(f"🔧 {tool['도구명']}"):
            st.write(f"**목적**: {tool['목적']}")
            st.write(f"**설명**: {tool['설명']}")
            st.write(f"**상태**: {tool['상태']}")
    
    # Tool Use Pattern 설명
    st.subheader("📚 Tool Use Pattern의 특징")
    st.markdown("""
    **Tool Use Pattern**은 AI가 외부 도구와 API를 활용하는 패턴입니다:
    
    1. **실시간 데이터**: Yahoo Finance API를 통한 최신 시장 데이터 활용
    2. **동적 분석**: 정적 데이터가 아닌 실시간 정보 기반 결정
    3. **확장성**: 새로운 데이터 소스나 도구 쉽게 추가 가능
    4. **투명성**: 어떤 도구를 사용했는지 추적 가능
    5. **정확성**: 실제 시장 상황을 반영한 포트폴리오 구성
    
    이를 통해 더 정확하고 현실적인 투자 포트폴리오를 제공할 수 있습니다.
    """)


def display_portfolio_visualization(portfolio: Dict[str, Any]):
    """포트폴리오 시각화"""
    st.markdown('<div class="step-header">📊 포트폴리오 시각화</div>', unsafe_allow_html=True)
    
    allocation = portfolio.get('portfolio_allocation', {})
    
    if not allocation:
        st.warning("시각화할 데이터가 없습니다.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 파이 차트
        fig_pie = px.pie(
            values=list(allocation.values()),
            names=list(allocation.keys()),
            title="포트폴리오 자산 배분",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # 바 차트
        fig_bar = px.bar(
            x=list(allocation.keys()),
            y=list(allocation.values()),
            title="자산별 배분 비율 (%)",
            labels={'x': 'ETF', 'y': '배분 비율 (%)'},
            color=list(allocation.values()),
            color_continuous_scale='viridis'
        )
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # 도넛 차트
    st.subheader("🍩 도넛 차트로 보는 포트폴리오")
    fig_donut = go.Figure(data=[go.Pie(
        labels=list(allocation.keys()),
        values=list(allocation.values()),
        hole=.3
    )])
    fig_donut.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>비율: %{percent}<br>값: %{value}%<extra></extra>'
    )
    fig_donut.update_layout(
        title_text="포트폴리오 구성 (도넛 차트)",
        annotations=[dict(text='Portfolio', x=0.5, y=0.5, font_size=20, showarrow=False)]
    )
    st.plotly_chart(fig_donut, use_container_width=True)


def display_detailed_data(financial_analysis: Dict[str, Any], result: Dict[str, Any]):
    """상세 데이터 표시"""
    st.markdown('<div class="step-header">📋 상세 분석 데이터</div>', unsafe_allow_html=True)
    
    # 입력 데이터
    st.subheader("📥 재무 분석 입력 데이터")
    st.json(financial_analysis)
    
    # AI 원시 응답
    st.subheader("🤖 AI 원시 응답")
    if result.get('raw_response'):
        st.text_area("AI 응답 전문", result['raw_response'], height=200)
    
    # 전체 결과 데이터
    st.subheader("📊 전체 결과 데이터")
    display_result = result.copy()
    if 'raw_response' in display_result:
        display_result['raw_response'] = "... (위에서 확인)"
    st.json(display_result)


if __name__ == "__main__":
    main()