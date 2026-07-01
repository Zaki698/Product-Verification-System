from google.adk.agents import Agent
from backend.reporting_service.prompts import reporting_prompt

reporting_agent = Agent(
    name="reporting_agent",
    model="gemini-2.5-flash",
    description="Root agent for verification reporting (Quality Assurance Manager).",
    instruction=reporting_prompt,
)