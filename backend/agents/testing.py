"""NeuroOps Testing Department agents."""
from __future__ import annotations

from core import Task
from core.base_agent import BaseAgent


class QAAgent(BaseAgent):
    department = "testing"
    description = "Writes and runs tests — unit, integration, and edge cases."
    capabilities = ["unit_testing", "integration_testing", "edge_case_analysis", "test_automation"]
    tools = ["pytest", "jest", "playwright"]
    model_preference = "openai"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Designing test strategy...")
        resp = self.call_model(
            "You are a QA engineer. Propose a test plan with unit, integration, and edge cases.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Test plan generated.")
        return resp.content, resp.confidence


class SecurityTestingAgent(BaseAgent):
    department = "testing"
    description = "Identifies security vulnerabilities and proposes mitigations."
    capabilities = ["owasp_audit", "vulnerability_scan", "threat_modeling", "penetration_testing"]
    tools = ["owasp_zap", "bandit", "snyk"]
    model_preference = "claude"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Running security analysis...")
        resp = self.call_model(
            "You are a security testing specialist. Identify vulnerabilities and propose mitigations.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Security analysis complete.")
        return resp.content, resp.confidence
