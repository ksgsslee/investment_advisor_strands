"""
Lab 1: Financial Analyst Streamlit App
재무 분석가 + Reflection 패턴 시연 앱
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
    page_title="Lab 1: AI 재무 분석가 (Reflection Pattern)",
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
    st.markdown('<div class="main-header">🔄 Lab 1: AI 재무 분석가 (Reflection Pattern)</div>', unsafe_allow_html=True)
    
    # 패턴 설명
    st.markdown("""
    ### 🎯 Reflection Pattern이란?
    AI가 자신의 분석 결과를 스스로 검증하는 패턴입니다. 
    - **1단계**: 재무 분석가 AI가 사용자 정보를 분석
    - **2단계**: Reflection AI가 분석 결과의 정확성을 검증
    - **결과**: 검증을 통과한 신뢰할 수 있는 분석 제공
    """)
    
    # 사이드바 - 사용자 입력
    with st.sidebar:
        st.header("📊 투자 정보 입력")
        
        # 사용자 입력 폼
        with st.form("financial_analysis_form"):
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
            
            submitted = st.form_submit_button("🔍 재무 분석 시작", use_container_width=True)
        
        # Reflection Pattern 설명
        st.markdown("---")
        st.subheader("🔄 Reflection Pattern 단계")
        st.markdown("""
        1. **분석**: 재무 상황 종합 분석
        2. **검증**: AI 자체 검증 수행
        3. **결과**: 검증된 신뢰할 수 있는 분석
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
        
        # 재무 분석 실행
        run_financial_analysis(user_input)
    else:
        # 초기 화면
        show_welcome_screen()


def show_welcome_screen():
    """초기 환영 화면"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ### 🎯 Lab 1: AI 재무 분석가에 오신 것을 환영합니다!
        
        이 시스템은 **Reflection Pattern**을 활용한 AI 재무 분석 서비스입니다.
        
        #### 🚀 주요 기능
        - **개인 맞춤형 위험 성향 평가**: 나이, 경험, 목표를 종합 분석
        - **필요 수익률 계산**: 목표 달성을 위한 연간 수익률 산출
        - **AI 자체 검증**: Reflection Pattern으로 분석 결과 검증
        - **신뢰성 보장**: 검증을 통과한 분석만 제공
        
        #### 🔄 Reflection Pattern의 장점
        - **정확성 향상**: AI가 스스로 오류를 찾아 수정
        - **신뢰성 증대**: 이중 검증으로 결과의 신뢰도 향상
        - **품질 보장**: 일정 기준을 만족하는 분석만 제공
        
        **👈 왼쪽 사이드바에서 투자 정보를 입력하고 분석을 시작하세요!**
        """)
        
        # Reflection Pattern 플로우차트
        st.markdown("---")
        st.subheader("🔄 Reflection Pattern 처리 흐름")
        
        # 간단한 플로우차트 시각화
        fig = go.Figure()
        
        # 노드 위치 정의
        nodes = {
            "사용자 입력": (1, 3),
            "재무 분석가 AI": (2, 3),
            "분석 결과": (3, 3),
            "Reflection AI": (4, 3),
            "검증 결과": (5, 3),
            "최종 결과": (6, 3)
        }
        
        colors = {
            "사용자 입력": "lightblue",
            "재무 분석가 AI": "lightgreen", 
            "분석 결과": "lightyellow",
            "Reflection AI": "lightcoral",
            "검증 결과": "lightpink",
            "최종 결과": "lightgray"
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
                textfont=dict(size=10)
            ))
        
        # 연결선 추가
        connections = [
            ("사용자 입력", "재무 분석가 AI"),
            ("재무 분석가 AI", "분석 결과"),
            ("분석 결과", "Reflection AI"),
            ("Reflection AI", "검증 결과"),
            ("검증 결과", "최종 결과")
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
            title="Reflection Pattern 처리 흐름",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)


def run_financial_analysis(user_input: Dict[str, Any]):
    """재무 분석 실행"""
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 재무 분석가 import 및 초기화
        status_text.text("🔧 AI 재무 분석가 초기화 중...")
        progress_bar.progress(20)
        
        from agent import FinancialAnalyst
        analyst = FinancialAnalyst()
        
        # 분석 실행
        status_text.text("🤖 재무 분석 수행 중...")
        progress_bar.progress(50)
        
        status_text.text("🔍 Reflection AI 검증 중...")
        progress_bar.progress(80)
        
        result = analyst.analyze(user_input)
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
        3. 인터넷 연결을 확인하세요
        """)


def display_analysis_results(user_input: Dict[str, Any], result: Dict[str, Any]):
    """분석 결과 표시"""
    
    if result['status'] == 'error':
        st.markdown(f'<div class="error-box">❌ 분석 중 오류가 발생했습니다: {result.get("error", "Unknown error")}</div>', unsafe_allow_html=True)
        return
    
    # Reflection 검증 결과에 따른 메시지
    if result['is_valid']:
        st.markdown('<div class="success-box">✅ Reflection AI 검증 통과! 신뢰할 수 있는 분석 결과입니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="error-box">❌ Reflection AI 검증 실패: {result["reflection_result"]}</div>', unsafe_allow_html=True)
        return
    
    analysis = result['analysis']
    
    # 탭으로 결과 구성
    tab1, tab2, tab3 = st.tabs([
        "📊 분석 결과", 
        "🔍 Reflection 검증", 
        "📋 상세 데이터"
    ])
    
    with tab1:
        display_financial_analysis(analysis)
    
    with tab2:
        display_reflection_results(result)
    
    with tab3:
        display_detailed_data(user_input, result)


def display_financial_analysis(analysis: Dict[str, Any]):
    """재무 분석 결과 표시"""
    st.markdown('<div class="step-header">💰 재무 분석 결과</div>', unsafe_allow_html=True)
    
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
        # 위험 성향에 따른 색상 표시
        risk_colors = {
            "매우 보수적": "🟢",
            "보수적": "🟡", 
            "중립적": "🟠",
            "공격적": "🔴",
            "매우 공격적": "🟣"
        }
        risk_profile = analysis.get('risk_profile', '')
        color = risk_colors.get(risk_profile, "⚪")
        st.metric(
            "위험 등급",
            f"{color} {risk_profile}",
            help="위험 성향 시각화"
        )
    
    # 상세 분석
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 위험 성향 분석")
        st.write(analysis.get('risk_profile_reason', ''))
    
    with col2:
        st.subheader("📊 수익률 계산 근거")
        st.write(analysis.get('return_rate_reason', ''))
    
    # 위험 성향 시각화
    st.subheader("📈 위험 성향 시각화")
    
    # 위험 성향별 점수 매핑
    risk_scores = {
        "매우 보수적": 1,
        "보수적": 2,
        "중립적": 3,
        "공격적": 4,
        "매우 공격적": 5
    }
    
    current_score = risk_scores.get(analysis.get('risk_profile', ''), 3)
    
    # 게이지 차트
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = current_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "위험 성향 등급"},
        delta = {'reference': 3},
        gauge = {
            'axis': {'range': [None, 5]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 1], 'color': "lightgray"},
                {'range': [1, 2], 'color': "yellow"},
                {'range': [2, 3], 'color': "orange"},
                {'range': [3, 4], 'color': "red"},
                {'range': [4, 5], 'color': "purple"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': current_score
            }
        }
    ))
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)


def display_reflection_results(result: Dict[str, Any]):
    """Reflection 검증 결과 표시"""
    st.markdown('<div class="step-header">🔍 Reflection AI 검증 결과</div>', unsafe_allow_html=True)
    
    # 검증 상태
    if result['is_valid']:
        st.success("✅ 검증 통과: 분석 결과가 신뢰할 수 있습니다.")
    else:
        st.error("❌ 검증 실패: 분석 결과에 문제가 있습니다.")
    
    # Reflection AI 응답
    st.subheader("🤖 Reflection AI 응답")
    st.code(result['reflection_result'])
    
    # Reflection Pattern 설명
    st.subheader("📚 Reflection Pattern이란?")
    st.markdown("""
    **Reflection Pattern**은 AI가 자신의 출력을 스스로 검증하는 패턴입니다:
    
    1. **자체 검증**: AI가 자신의 분석 결과를 다시 검토
    2. **오류 탐지**: 계산 실수나 논리적 오류를 찾아냄
    3. **품질 보장**: 일정 기준을 만족하는 결과만 제공
    4. **신뢰성 향상**: 이중 검증으로 결과의 신뢰도 증대
    
    이 방식을 통해 더 정확하고 신뢰할 수 있는 AI 서비스를 제공할 수 있습니다.
    """)


def display_detailed_data(user_input: Dict[str, Any], result: Dict[str, Any]):
    """상세 데이터 표시"""
    st.markdown('<div class="step-header">📋 상세 분석 데이터</div>', unsafe_allow_html=True)
    
    # 사용자 입력
    st.subheader("📥 사용자 입력 데이터")
    st.json(user_input)
    
    # 전체 결과 데이터
    st.subheader("📊 전체 분석 결과")
    st.json(result)


if __name__ == "__main__":
    main()