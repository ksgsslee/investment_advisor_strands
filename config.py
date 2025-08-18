"""
Configuration settings for the Investment Advisor system
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Model configurations
MODELS = {
    "financial_analyst": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "temperature": 0.2,
        "max_tokens": 2000
    },
    "reflection": {
        "provider": "anthropic", 
        "model": "claude-3-5-sonnet-20241022",
        "temperature": 0.2,
        "max_tokens": 2000
    },
    "portfolio_architect": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022", 
        "temperature": 0.3,
        "max_tokens": 3000
    },
    "risk_manager": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "temperature": 0.2,
        "max_tokens": 3000
    },
    "report_generator": {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "temperature": 0.3,
        "max_tokens": 2000
    }
}

# Available investment products
AVAILABLE_PRODUCTS = {
    "SPY": "SPDR S&P 500 ETF Trust (미국 대형주)",
    "QQQ": "Invesco QQQ Trust (미국 기술주)",
    "IWM": "iShares Russell 2000 ETF (미국 소형주)",
    "VGK": "Vanguard FTSE Europe ETF (유럽 주식)",
    "EWJ": "iShares MSCI Japan ETF (일본 주식)",
    "MCHI": "iShares MSCI China ETF (중국 주식)",
    "EEM": "iShares MSCI Emerging Markets ETF (신흥국 주식)",
    "AGG": "iShares Core U.S. Aggregate Bond ETF (미국 종합 채권)",
    "TLT": "iShares 20+ Year Treasury Bond ETF (미국 장기 국채)",
    "LQD": "iShares iBoxx $ Investment Grade Corporate Bond ETF (미국 우량 회사채)",
    "HYG": "iShares iBoxx $ High Yield Corporate Bond ETF (미국 하이일드 채권)",
    "EMB": "iShares J.P. Morgan USD Emerging Markets Bond ETF (신흥국 채권)",
    "GLD": "SPDR Gold Shares (금)",
    "SLV": "iShares Silver Trust (은)",
    "VNQ": "Vanguard Real Estate ETF (미국 부동산 리츠)",
    "RWX": "SPDR Dow Jones International Real Estate ETF (국제 부동산)",
    "USO": "United States Oil Fund (원유)",
    "VTIP": "Vanguard Short-Term Inflation-Protected Securities ETF (물가연동채권)",
    "XLF": "Financial Select Sector SPDR Fund (금융 섹터)",
    "ICLN": "iShares Global Clean Energy ETF (클린에너지)"
}

# API Keys (set in .env file)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")