"""
__init__.py
Financial Analyst 패키지 초기화

Lab 1: Financial Analyst with Reflection Pattern
재무 분석가 + Reflection 패턴 구현 (AgentCore Runtime 버전)

개인의 재무 상황을 종합적으로 분석하여 투자 성향과 목표 수익률을 계산하는
AI 에이전트 시스템입니다. Reflection 패턴을 통해 분석 결과의 품질을 보장합니다.
"""

from .financial_analyst import FinancialAnalyst

__version__ = "1.0.0"
__author__ = "Financial Analyst Team"
__description__ = "AI-powered financial analysis system with reflection pattern for quality assurance"

__all__ = ['FinancialAnalyst']