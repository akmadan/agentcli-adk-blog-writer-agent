"""AgentCore entrypoint for the Academic Research ADK agent."""

import os
import sys

# Add the project root to sys.path so academic_research package is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set Gemini API key from AgentCore credential injection
gemini_key = os.environ.get("AGENTCORE_CREDENTIAL_GEMINI_API_KEY", "")
if gemini_key:
    os.environ.setdefault("GOOGLE_API_KEY", gemini_key)

# Use Google AI Studio (not Vertex AI) when running on AgentCore
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from academic_research.prompt import ACADEMIC_COORDINATOR_PROMPT
from academic_research.sub_agents.academic_newresearch.agent import academic_newresearch_agent
from academic_research.sub_agents.academic_websearch.agent import academic_websearch_agent

MODEL = "gemini-2.5-pro"

root_agent = LlmAgent(
    name="academic_coordinator",
    model=MODEL,
    description=(
        "analyzing seminal papers provided by the users, "
        "providing research advice, locating current papers "
        "relevant to the seminal paper, generating suggestions "
        "for new research directions, and accessing web resources "
        "to acquire knowledge"
    ),
    instruction=ACADEMIC_COORDINATOR_PROMPT,
    output_key="seminal_paper",
    tools=[
        AgentTool(agent=academic_websearch_agent),
        AgentTool(agent=academic_newresearch_agent),
    ],
)
