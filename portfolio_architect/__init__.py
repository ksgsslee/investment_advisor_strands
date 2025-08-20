"""
__init__.py
Portfolio Architect 패키지 초기화

Lab 2: Portfolio Architect with Tool Use Pattern
포트폴리오 설계사 + Tool Use 패턴 구현 (AgentCore Runtime 버전)

실시간 시장 데이터를 분석하여 맞춤형 투자 포트폴리오를 제안하는
AI 에이전트 시스템입니다.
"""

from .portfolio_architect import PortfolioArchitect

__version__ = "1.0.0"
__author__ = "Portfolio Architect Team"
__description__ = "AI-powered portfolio design system with real-time market data analysis"

__all__ = ['PortfolioArchitect']