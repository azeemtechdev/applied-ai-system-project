"""PawPal+ agentic layer.

An AI agent that plans (extracts care tasks from natural language), acts
(schedules them with the deterministic ``Scheduler``), and checks its own
work (deterministic guardrails + an LLM critique) in a capped loop.
"""

from agent.planner import PawPalAgent, AgentResult

__all__ = ["PawPalAgent", "AgentResult"]
