"""
Lab 3: Risk Manager Streamlit App
리스크 관리사 + Planning 패턴 시연 앱
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
    page_title="Lab 3: AI 리스크 관리사 (Planning Pattern)",
    page_icon="⚠️",
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
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .scenario-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e2e3e5;
        border: 1px solid #d6d8db;
        color: #383d41;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # 메인 헤더
    st.markdown('<div class="main-header">📋 Lab 3: AI 리스크 관리사 (Planning Pattern)</div>', unsafe_allow_html=True)
    
    # 패턴 설명
    st.markdown("""
    ### 🎯 Planning Pattern이란?
    AI가 체계적인 계획과 워크플로우를 통해 복잡한 작업을 수행하는 패턴입니다.
    - **1단계**: 뉴스 분석을 통한 시장 상황 파악
    - **2단계**: 시장 지표 데이터 수집 및 분석
    - **3단계**: 경제 시나리오 도출 및 계획 수립
    - **4단계**: 시나리오별 포트폴리오 조정 전략 제시
    """)
    
    # 사이드바 - 포트폴리오 입력
    with st.sidebar:
        st.header("📈 포트폴리오 정보 입력")
        
        # 포트폴리오 입력 폼
        with st.form("risk_analysis_form"):
            st.subheader("Lab 2 결과 또는 직접 입력")
            
            # ETF 선택
            st.write("**포트폴리오 구성 (3개 ETF)**")
            etf1 = st.selectbox("ETF 1", ["QQQ", "SPY", "MCHI", "ICLN", "GLD", "VNQ"], index=0)
            ratio1 = st.number_input("비율 1 (%)", min_value=0, max_value=100, value=40, step=5)
            
            etf2 = st.selectbox("ETF 2", ["QQQ", "SPY", "MCHI", "ICLN", "GLD", "VNQ"], index=2)
            ratio2 = st.number_input("비율 2 (%)", min_value=0, max_value=100, value=30, step=5)
            
            etf3 = st.selectbox("ETF 3", ["QQQ", "SPY", "MCHI", "ICLN", "GLD", "VNQ"], index=3)
            ratio3 = st.number_input("비율 3 (%)", min_value=0, max_value=100, value=30, step=5)
            
            # 비율 검증
            total_ratio = ratio1 + ratio2 + ratio3
            if total_ratio != 100:
                st.warning(f"⚠️ 총 비율이 {total_ratio}%입니다. 100%가 되도록 조정해주세요.")
            
            strategy = st.text_area(
                "투자 전략",
                value="공격적인 투자 전략을 채택하여 높은 수익률을 목표로 합니다.",
                help="포트폴리오의 투자 전략 설명"
            )
            
            reason = st.text_area(
                "구성 근거",
                value="기술주와 신흥시장, 클린에너지 섹터의 성장 잠재력을 활용한 분산 투자 전략입니다.",
                help="포트폴리오 구성 근거"
            )
            
            submitted = st.form_submit_button("⚠️ 리스크 분석 시작", use_container_width=True)
        
        # Planning Pattern 설명
        st.markdown("---")
        st.subheader("📋 Planning 단계")
        st.markdown("""
        1. **뉴스 분석**: 각 ETF 관련 뉴스 수집
        2. **시장 지표**: 주요 경제 지표 분석
        3. **시나리오 도출**: 가능한 경제 상황 예측
        4. **조정 전략**: 시나리오별 대응 방안
        """)
    
    # 메인 컨텐츠
    if submitted and total_ratio == 100:
        # 포트폴리오 데이터 구성
        portfolio_data = {
            "portfolio": {
                "portfolio_allocation": {
                    etf1: ratio1,
                    etf2: ratio2,
                    etf3: ratio3
                },
                "strategy": strategy,
                "reason": reason
            }
        }
        
        # 리스크 분석 실행
        run_risk_analysis(portfolio_data)
    elif submitted and total_ratio != 100:
        st.error("❌ 포트폴리오 비율의 총합이 100%가 되어야 합니다.")
    else:
        # 초기 화면
        show_welcome_screen()


def show_welcome_screen():
    """초기 환영 화면"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ### 🎯 Lab 3: AI 리스크 관리사에 오신 것을 환영합니다!
        
        이 시스템은 **Planning Pattern**을 활용한 AI 리스크 분석 서비스입니다.
        
        #### 🚀 주요 기능
        - **뉴스 기반 분석**: 실시간 뉴스를 통한 시장 상황 파악
        - **시장 지표 모니터링**: VIX, 국채수익률 등 주요 지표 추적
        - **시나리오 플래닝**: 가능한 경제 상황별 대응 전략 수립
        - **포트폴리오 조정**: 시나리오별 최적 자산 배분 제안
        
        #### 📋 Planning Pattern의 장점
        - **체계적 접근**: 단계별 계획적 분석 수행
        - **종합적 판단**: 다양한 정보원을 통합 분석
        - **미래 대비**: 가능한 시나리오에 대한 사전 준비
        - **리스크 관리**: 체계적인 위험 요소 식별 및 대응
        
        **👈 왼쪽 사이드바에서 포트폴리오 정보를 입력하고 분석을 시작하세요!**
        """)
        
        # Planning Pattern 플로우차트
        st.markdown("---")
        st.subheader("📋 Planning Pattern 처리 흐름")
        
        # 간단한 플로우차트 시각화
        fig = go.Figure()
        
        # 노드 위치 정의
        nodes = {
            "포트폴리오 입력": (1, 4),
            "리스크 관리사": (2, 4),
            "뉴스 분석": (3, 5),
            "시장 지표 분석": (3, 3),
            "시나리오 도출": (4, 4),
            "조정 전략 수립": (5, 4),
            "최종 리포트": (6, 4)
        }
        
        colors = {
            "포트폴리오 입력": "lightblue",
            "리스크 관리사": "lightgreen",
            "뉴스 분석": "lightyellow",
            "시장 지표 분석": "lightyellow",
            "시나리오 도출": "lightcoral",
            "조정 전략 수립": "lightpink",
            "최종 리포트": "lightgray"
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
            ("포트폴리오 입력", "리스크 관리사"),
            ("리스크 관리사", "뉴스 분석"),
            ("리스크 관리사", "시장 지표 분석"),
            ("뉴스 분석", "시나리오 도출"),
            ("시장 지표 분석", "시나리오 도출"),
            ("시나리오 도출", "조정 전략 수립"),
            ("조정 전략 수립", "최종 리포트")
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
            title="Planning Pattern 처리 흐름",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=350,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)


def run_risk_analysis(portfolio_data: Dict[str, Any]):
    """리스크 분석 실행"""
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 리스크 관리사 import 및 초기화
        status_text.text("🔧 AI 리스크 관리사 초기화 중...")
        progress_bar.progress(15)
        
        from agent import RiskManager
        risk_manager = RiskManager()
        
        # Planning 단계별 표시
        status_text.text("📰 뉴스 분석 수행 중...")
        progress_bar.progress(35)
        
        status_text.text("📊 시장 지표 데이터 수집 중...")
        progress_bar.progress(55)
        
        status_text.text("🎯 경제 시나리오 도출 중...")
        progress_bar.progress(75)
        
        status_text.text("📋 포트폴리오 조정 전략 수립 중...")
        progress_bar.progress(90)
        
        result = risk_manager.analyze_risk(portfolio_data)
        progress_bar.progress(100)
        status_text.text("✅ 리스크 분석 완료!")
        
        # 결과 표시
        display_risk_results(portfolio_data, result)
        
    except Exception as e:
        st.error(f"❌ 리스크 분석 중 오류가 발생했습니다: {str(e)}")
        st.markdown("""
        ### 🔧 문제 해결 방법
        1. `.env` 파일에 `ANTHROPIC_API_KEY`가 올바르게 설정되어 있는지 확인하세요
        2. 인터넷 연결을 확인하세요 (뉴스 및 시장 데이터 조회 필요)
        3. yfinance 패키지가 설치되어 있는지 확인하세요
        """)


def display_risk_results(portfolio_data: Dict[str, Any], result: Dict[str, Any]):
    """리스크 분석 결과 표시"""
    
    if result['status'] != 'success':
        st.markdown(f'<div class="error-box">❌ 리스크 분석 실패: {result.get("error", "Unknown error")}</div>', unsafe_allow_html=True)
        
        # 원시 응답 표시
        if result.get('raw_response'):
            with st.expander("🔍 AI 응답 내용 보기"):
                st.text(result['raw_response'])
        return
    
    st.markdown('<div class="success-box">✅ Planning Pattern으로 리스크 분석 완료!</div>', unsafe_allow_html=True)
    
    risk_analysis = result['risk_analysis']
    
    # 탭으로 결과 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "⚠️ 리스크 시나리오", 
        "📋 Planning 과정", 
        "📊 시각화",
        "📋 상세 데이터"
    ])
    
    with tab1:
        display_risk_scenarios(risk_analysis, portfolio_data)
    
    with tab2:
        display_planning_process(result)
    
    with tab3:
        display_risk_visualization(risk_analysis, portfolio_data)
    
    with tab4:
        display_detailed_data(portfolio_data, result)


def display_risk_scenarios(risk_analysis: Dict[str, Any], portfolio_data: Dict[str, Any]):
    """리스크 시나리오 표시"""
    st.markdown('<div class="step-header">⚠️ 리스크 시나리오 분석</div>', unsafe_allow_html=True)
    
    original_allocation = portfolio_data['portfolio']['portfolio_allocation']
    
    # 시나리오별 분석
    for i, scenario_key in enumerate(['scenario1', 'scenario2'], 1):
        if scenario_key not in risk_analysis:
            continue
            
        scenario = risk_analysis[scenario_key]
        
        st.markdown(f'<div class="scenario-box"><h3>🎯 시나리오 {i}: {scenario.get("name", "")}</h3></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📝 시나리오 설명**")
            st.write(scenario.get('description', ''))
            
            st.markdown("**💡 대응 전략**")
            st.write(scenario.get('reason', ''))
        
        with col2:
            # 조정된 포트폴리오 배분
            adjusted_allocation = scenario.get('allocation_management', {})
            if adjusted_allocation:
                # 변화량 계산
                changes = {}
                for ticker in adjusted_allocation:
                    original = original_allocation.get(ticker, 0)
                    adjusted = adjusted_allocation[ticker]
                    change = adjusted - original
                    changes[ticker] = change
                
                # 변화량 표시
                st.markdown("**📊 포트폴리오 조정**")
                for ticker, change in changes.items():
                    original = original_allocation.get(ticker, 0)
                    adjusted = adjusted_allocation[ticker]
                    
                    if change > 0:
                        st.write(f"• **{ticker}**: {original}% → {adjusted}% (+{change}%)")
                    elif change < 0:
                        st.write(f"• **{ticker}**: {original}% → {adjusted}% ({change}%)")
                    else:
                        st.write(f"• **{ticker}**: {original}% → {adjusted}% (변화없음)")
        
        # 시나리오별 포트폴리오 비교 차트
        col1, col2 = st.columns(2)
        
        with col1:
            # 원래 포트폴리오
            fig_original = px.pie(
                values=list(original_allocation.values()),
                names=list(original_allocation.keys()),
                title="현재 포트폴리오",
                color_discrete_sequence=px.colors.qualitative.Set1
            )
            st.plotly_chart(fig_original, use_container_width=True)
        
        with col2:
            # 조정된 포트폴리오
            if adjusted_allocation:
                fig_adjusted = px.pie(
                    values=list(adjusted_allocation.values()),
                    names=list(adjusted_allocation.keys()),
                    title=f"시나리오 {i} 조정 포트폴리오",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                st.plotly_chart(fig_adjusted, use_container_width=True)
        
        st.markdown("---")


def display_planning_process(result: Dict[str, Any]):
    """Planning 과정 표시"""
    st.markdown('<div class="step-header">📋 Planning Pattern 실행 과정</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="warning-box">이 리스크 분석은 다음과 같은 체계적인 Planning 과정을 거쳐 수행되었습니다:</div>', unsafe_allow_html=True)
    
    # Planning 단계들
    planning_steps = [
        {
            "단계": "1. 뉴스 분석",
            "도구": "get_product_news()",
            "목적": "각 ETF 관련 최신 뉴스 수집 및 분석",
            "설명": "포트폴리오에 포함된 각 ETF의 최근 뉴스를 분석하여 시장 상황과 리스크 요인을 파악합니다.",
            "상태": "✅ 완료"
        },
        {
            "단계": "2. 시장 지표 분석",
            "도구": "get_market_data()",
            "목적": "주요 경제 지표 데이터 수집",
            "설명": "VIX 지수, 국채 수익률, 달러 지수 등 주요 시장 지표를 분석하여 거시경제 상황을 파악합니다.",
            "상태": "✅ 완료"
        },
        {
            "단계": "3. 시나리오 도출",
            "도구": "AI 분석 엔진",
            "목적": "가능한 경제 시나리오 도출",
            "설명": "수집된 뉴스와 시장 데이터를 종합하여 발생 가능성이 높은 경제 시나리오를 도출합니다.",
            "상태": "✅ 완료"
        },
        {
            "단계": "4. 조정 전략 수립",
            "도구": "AI 전략 엔진",
            "목적": "시나리오별 포트폴리오 조정 방안 제시",
            "설명": "각 시나리오에 대응하는 최적의 포트폴리오 조정 전략을 수립합니다.",
            "상태": "✅ 완료"
        }
    ]
    
    for step in planning_steps:
        with st.expander(f"📋 {step['단계']}"):
            st.write(f"**도구**: {step['도구']}")
            st.write(f"**목적**: {step['목적']}")
            st.write(f"**설명**: {step['설명']}")
            st.write(f"**상태**: {step['상태']}")
    
    # Planning Pattern 설명
    st.subheader("📚 Planning Pattern의 특징")
    st.markdown("""
    **Planning Pattern**은 AI가 체계적인 계획을 통해 복잡한 작업을 수행하는 패턴입니다:
    
    1. **단계별 접근**: 복잡한 문제를 여러 단계로 나누어 체계적으로 해결
    2. **정보 통합**: 다양한 데이터 소스를 통합하여 종합적 판단
    3. **시나리오 기반**: 가능한 미래 상황을 예측하고 대비책 마련
    4. **전략적 사고**: 단순한 분석을 넘어 전략적 대응 방안 제시
    5. **리스크 관리**: 체계적인 위험 요소 식별 및 관리 방안 수립
    
    이를 통해 더 신뢰할 수 있고 실용적인 리스크 관리 서비스를 제공할 수 있습니다.
    """)


def display_risk_visualization(risk_analysis: Dict[str, Any], portfolio_data: Dict[str, Any]):
    """리스크 시각화"""
    st.markdown('<div class="step-header">📊 리스크 분석 시각화</div>', unsafe_allow_html=True)
    
    original_allocation = portfolio_data['portfolio']['portfolio_allocation']
    
    # 시나리오별 배분 변화 히트맵
    st.subheader("🔥 시나리오별 포트폴리오 변화 히트맵")
    
    # 데이터 준비
    scenarios_data = []
    tickers = list(original_allocation.keys())
    
    # 원래 포트폴리오
    scenarios_data.append(['현재'] + [original_allocation[ticker] for ticker in tickers])
    
    # 각 시나리오
    for i, scenario_key in enumerate(['scenario1', 'scenario2'], 1):
        if scenario_key in risk_analysis:
            scenario = risk_analysis[scenario_key]
            adjusted_allocation = scenario.get('allocation_management', {})
            scenario_name = f"시나리오 {i}"
            scenarios_data.append([scenario_name] + [adjusted_allocation.get(ticker, 0) for ticker in tickers])
    
    # DataFrame 생성
    df_scenarios = pd.DataFrame(scenarios_data, columns=['시나리오'] + tickers)
    df_scenarios = df_scenarios.set_index('시나리오')
    
    # 히트맵
    fig_heatmap = px.imshow(
        df_scenarios.values,
        labels=dict(x="ETF", y="시나리오", color="배분 비율 (%)"),
        x=df_scenarios.columns,
        y=df_scenarios.index,
        color_continuous_scale='RdYlBu_r',
        aspect="auto"
    )
    fig_heatmap.update_layout(title="시나리오별 포트폴리오 배분 히트맵")
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # 변화량 바 차트
    st.subheader("📊 시나리오별 배분 변화량")
    
    for i, scenario_key in enumerate(['scenario1', 'scenario2'], 1):
        if scenario_key not in risk_analysis:
            continue
            
        scenario = risk_analysis[scenario_key]
        adjusted_allocation = scenario.get('allocation_management', {})
        scenario_name = scenario.get('name', f'시나리오 {i}')
        
        # 변화량 계산
        changes = []
        for ticker in tickers:
            original = original_allocation.get(ticker, 0)
            adjusted = adjusted_allocation.get(ticker, 0)
            change = adjusted - original
            changes.append(change)
        
        # 바 차트
        fig_changes = px.bar(
            x=tickers,
            y=changes,
            title=f"{scenario_name} - 배분 변화량 (%)",
            labels={'x': 'ETF', 'y': '변화량 (%)'},
            color=changes,
            color_continuous_scale='RdBu'
        )
        fig_changes.add_hline(y=0, line_dash="dash", line_color="black")
        st.plotly_chart(fig_changes, use_container_width=True)


def display_detailed_data(portfolio_data: Dict[str, Any], result: Dict[str, Any]):
    """상세 데이터 표시"""
    st.markdown('<div class="step-header">📋 상세 분석 데이터</div>', unsafe_allow_html=True)
    
    # 입력 데이터
    st.subheader("📥 포트폴리오 입력 데이터")
    st.json(portfolio_data)
    
    # AI 원시 응답
    st.subheader("🤖 AI 원시 응답")
    if result.get('raw_response'):
        st.text_area("AI 응답 전문", result['raw_response'], height=300)
    
    # 전체 결과 데이터
    st.subheader("📊 전체 결과 데이터")
    display_result = result.copy()
    if 'raw_response' in display_result:
        display_result['raw_response'] = "... (위에서 확인)"
    st.json(display_result)


if __name__ == "__main__":
    main()