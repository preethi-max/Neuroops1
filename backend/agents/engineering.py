"""NeuroOps Engineering Department agents."""
from __future__ import annotations

from core import Task
from core.base_agent import BaseAgent


class SoftwareEngineerAgent(BaseAgent):
    department = "engineering"
    description = "Generalist software engineer — designs and implements full features."
    capabilities = ["architecture", "implementation", "code_review", "refactoring"]
    tools = ["code_editor", "git", "linter"]
    model_preference = "openai"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Analyzing feature requirements...")
        resp = self.call_model(
            "You are a senior software engineer. Produce a concise implementation plan.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Generated implementation plan.")
        return resp.content, resp.confidence


class BackendAgent(BaseAgent):
    department = "engineering"
    description = "Builds server-side APIs, data models, and business logic."
    capabilities = ["api_design", "database_modeling", "authentication", "performance"]
    tools = ["code_editor", "api_tester", "database_client"]
    model_preference = "openai"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Designing backend architecture...")
        resp = self.call_model(
            "You are a backend engineer. Design the API and data layer for the request.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Backend design complete.")
        return resp.content, resp.confidence


class FrontendAgent(BaseAgent):
    department = "engineering"
    description = "Builds client-side UI components and pages."
    capabilities = ["ui_implementation", "responsive_design", "state_management", "accessibility"]
    tools = ["code_editor", "browser_devtools", "css_preprocessor"]
    model_preference = "claude"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Building frontend components...")
        resp = self.call_model(
            "You are a frontend engineer. Describe the component structure and implementation.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Frontend components designed.")
        return resp.content, resp.confidence


class DebuggingAgent(BaseAgent):
    department = "engineering"
    description = "Analyzes failures, finds root causes, and proposes fixes."
    capabilities = ["root_cause_analysis", "stack_trace_analysis", "fix_proposal", "regression_testing"]
    tools = ["debugger", "logger", "profiler"]
    model_preference = "claude"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Scanning for bugs and root causes...")
        resp = self.call_model(
            "You are a debugging specialist. Identify the root cause and propose a fix.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Debug analysis complete.")
        return resp.content, resp.confidence
