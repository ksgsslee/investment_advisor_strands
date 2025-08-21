"""
__init__.py
Risk Manager 패키지 초기화

Lab 3: Risk Manager with Planning Pattern
리스크 관리사 + Planning 패턴 구현 (AgentCore Runtime 버전)

포트폴리오 제안을 바탕으로 뉴스 기반 리스크 분석을 수행하고,
경제 시나리오에 따른 포트폴리오 조정 가이드를 제공하는 AI 에이전트 시스템입니다.
"""

from .risk_manager import RiskManager

__version__ = "1.0.0"
__author__ = "Risk Manager Team"
__description__ = "AI-powered risk management system with news-based analysis and scenario planning"

__all__ = ['RiskManager']