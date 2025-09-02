"""
financial_analyst.py

Financial Analyst - Calculator 도구 활용 재무 분석
"""

import json
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import calculator
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class Config:
    """Financial Analyst 설정"""
    MODEL_ID = "openai.gpt-oss-120b-1:0"
    TEMPERATURE = 0.1
    MAX_TOKENS = 3000

def extract_json_from_text(text_content):
    """AI 응답에서 JSON 부분만 추출"""
    if not isinstance(text_content, str):
        return text_content
    
    start_idx = text_content.find('{')
    end_idx = text_content.rfind('}') + 1
    
    if start_idx != -1 and end_idx > start_idx:
        return text_content[start_idx:end_idx]
    
    return text_content

class FinancialAnalyst:
    """Calculator 도구를 활용한 AI 재무 분석사"""
    
    def __init__(self):
        self.analyst_agent = Agent(
            name="financial_analyst",
            model=BedrockModel(
                model_id=Config.MODEL_ID,
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS
            ),
            tools=[calculator],
            system_prompt=self._get_analyst_prompt()
        )
        
    def _get_analyst_prompt(self) -> str:
        return """재무분석 전문가로서 개인 맞춤형 투자 분석을 수행합니다.

입력 데이터:
- total_investable_amount: 투자 가능 금액
- target_amount: 1년 후 목표 금액
- age: 나이  
- stock_investment_experience_years: 투자 경험 연수
- investment_purpose: 투자 목적
- preferred_sectors: 관심 투자 분야

분석 과정:
1. "calculator" 도구를 사용하여 수익률을 계산하세요: ((목표금액/투자금액)-1)*100
2. 나이, 경험, 목적, 관심분야를 종합한 위험성향 평가하세요.
3. 수익률, 위험성향을 고려한 종합 평가하세요.

출력:
{
"risk_profile": "매우 보수적|보수적|중립적|공격적|매우 공격적",
"risk_profile_reason": "위험성향 평가 근거 (2-3문장)",
"required_annual_return_rate": 수익률(소수점2자리),
"return_rate_reason": "수익률 계산 과정",
"summary": "종합 총평 (3-4문장)"
}"""

    async def analyze_financial_situation_async(self, user_input):
        """Calculator 도구를 활용한 실시간 스트리밍 재무 분석"""
        try:
            user_input_str = json.dumps(user_input, ensure_ascii=False)

            async for event in self.analyst_agent.stream_async(user_input_str):
                if "data" in event:
                    yield {"type": "text_chunk", "data": event["data"]}
                
                if "message" in event:
                    message = event["message"]
                    
                    if message.get("role") == "assistant":
                        for content in message.get("content", []):
                            if "toolUse" in content:
                                tool_use = content["toolUse"]
                                yield {
                                    "type": "tool_use",
                                    "tool_name": tool_use.get("name"),
                                    "tool_use_id": tool_use.get("toolUseId"),
                                    "tool_input": tool_use.get("input", {})
                                }
                    
                    if message.get("role") == "user":
                        for content in message.get("content", []):
                            if "toolResult" in content:
                                tool_result = content["toolResult"]
                                yield {
                                    "type": "tool_result",
                                    "tool_use_id": tool_result["toolUseId"],
                                    "status": tool_result["status"],
                                    "content": tool_result["content"]
                                }
                
                if "result" in event:
                    raw_result = str(event["result"])
                    clean_json = extract_json_from_text(raw_result)
                    yield {"type": "streaming_complete", "result": clean_json}

        except Exception as e:
            yield {"type": "error", "error": str(e), "status": "error"}

analyst = None

@app.entrypoint
async def financial_analyst(payload):
    """AgentCore Runtime 엔트리포인트"""
    global analyst
    
    if analyst is None:
        analyst = FinancialAnalyst()

    user_input = payload.get("input_data")
    async for chunk in analyst.analyze_financial_situation_async(user_input):
        yield chunk

if __name__ == "__main__":
    app.run()