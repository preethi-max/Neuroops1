# NeuroOps - Autonomous AI Workforce for Software Teams

An autonomous multi-agent AI system. A user submits one request; the CEO Agent
analyzes it, queries the Agent Registry to dynamically form a team, the Scheduler
activates only the required agents, agents collaborate in parallel, the Memory
System stores results, and the CEO merges all outputs into a final report —
all streamed in real time.

## Tech Stack

- **Backend**: Python, Flask, Flask-SocketIO, LangGraph, SQLAlchemy
- **Frontend**: HTML, CSS, Vanilla JavaScript, Three.js
- **No React, Next.js, or Firebase**

## Phase 3 Architecture

```
User Request
  -> CEO Agent (analyze intent, identify required skills)
  -> Agent Registry (query for suitable agents by skills, performance, workload)
  -> Dynamic Team Formation (CEO selects optimized team)
  -> Task Planner (build task DAG with dependencies)
  -> Scheduler (select best agent per task, execute in parallel, respect deps)
  -> AI Agents (work, emit state transitions, call Model Provider Layer)
  -> Memory System (episodic, semantic, project, agent memory)
  -> Result Collection
  -> CEO Agent (synthesize final report)
  -> Final Response
```

## Folder Structure

```
backend/
├── app.py                  # Flask + Socket.IO entry point
├── config.py               # Configuration (model provider, thresholds)
├── requirements.txt
├── core/                   # Intelligence layer
│   ├── models.py            # Task, AgentState, AgentResult, TimelineEvent, MemoryEntry, ApprovalRequest
│   ├── storage.py           # In-memory SessionStore (isolated, DB-ready)
│   ├── event_bus.py          # Socket.IO event broadcaster with trace_id
│   ├── base_agent.py         # BaseAgent contract (think, emit, call model, return result)
│   ├── model_provider.py     # Model Provider Layer (OpenAI/Gemini/Claude/Stub)
│   ├── ceo_agent.py          # CEO: analyze, query registry, form team, delegate, synthesize
│   ├── task_planner.py       # Request -> structured task DAG with skills
│   ├── scheduler_service.py # Intelligent routing, parallel exec, retries, human approval
│   ├── approval_service.py   # Human-in-the-Loop approval system
│   ├── memory_service.py     # Episodic, Semantic, Project, Agent memory
│   ├── performance_analytics.py # Per-agent + system metrics
│   └── workflow.py          # LangGraph StateGraph workflow
├── agents/                 # AI agents (one contract, 13 types)
│   ├── registry.py          # Advanced Agent Registry (capabilities, workload, performance)
│   ├── engineering.py       # SoftwareEngineer, Backend, Frontend, Debugging
│   ├── design.py            # UIUXDesigner, Accessibility
│   ├── testing.py           # QA, SecurityTesting
│   ├── research.py          # Research, Documentation
│   └── support_agents.py    # TaskPlanner, Notification, KnowledgeManager
├── api/                    # REST blueprints
│   └── routes.py            # All endpoints (workflow, registry, memory, approval, analytics)
└── utils/                  # Logging, error handling
frontend/
├── index.html              # Dashboard with 3D viz + all Phase 3 panels
├── style.css               # Dark theme, responsive
└── script.js               # REST + Socket.IO + Three.js client
```

## AI Agents

| Department | Agent | Capabilities |
|-----------|-------|-------------|
| Engineering | SoftwareEngineer | architecture, implementation, code_review, refactoring |
| Engineering | Backend | api_design, database_modeling, authentication, performance |
| Engineering | Frontend | ui_implementation, responsive_design, state_management |
| Engineering | Debugging | root_cause_analysis, stack_trace_analysis, fix_proposal |
| Design | UIUXDesigner | ui_design, ux_research, wireframing, prototyping |
| Design | Accessibility | wcag_audit, aria_review, contrast_analysis |
| Testing | QA | unit_testing, integration_testing, edge_case_analysis |
| Testing | SecurityTesting | owasp_audit, vulnerability_scan, threat_modeling |
| Research | Research | information_retrieval, literature_review, summarization |
| Research | Documentation | technical_writing, api_documentation, readme_generation |
| Management | TaskPlanner | task_decomposition, dependency_analysis |
| Communication | Notification | notification_formatting, stakeholder_communication |
| Memory | KnowledgeManager | memory_consolidation, knowledge_retrieval, checkpointing |

## Agent Lifecycle

```
SLEEPING -> AVAILABLE -> ASSIGNED -> THINKING -> WORKING -> WAITING -> COMPLETED -> SLEEPING
                                                                -> FAILED
                                                                -> WAITING_APPROVAL
```

Every transition emits an Event Bus event with trace_id, agent_id, previous_state, new_state.

## Model Provider Layer

Agents call AI models through a common interface (`ModelManager`). Supported providers:
- **OpenAI** (GPT-4o, etc.) — set `MODEL_PROVIDER=openai` + `OPENAI_API_KEY`
- **Google Gemini** — set `MODEL_PROVIDER=gemini` + `GEMINI_API_KEY`
- **Anthropic Claude** — set `MODEL_PROVIDER=claude` + `ANTHROPIC_API_KEY`
- **Stub** (default) — deterministic heuristic output, no API key needed

## Memory System

| Type | Stores |
|------|--------|
| Episodic | Previous conversations, execution history, agent decisions |
| Semantic | Documents, code knowledge, technical information |
| Project | Project structure, completed tasks, previous states (checkpoints) |
| Agent | Per-agent: previous tasks, success rate, learned preferences |

Supports "Continue yesterday's project" by retrieving the last checkpoint and loading previous agent activities.

## Human-in-the-Loop

When confidence < threshold (default 0.5) or a high-risk action is detected, the system enters `WAITING_FOR_HUMAN_APPROVAL`. The user can approve, reject, or request modification via the API or frontend.

## REST API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/workflow/submit` | Submit a request to the autonomous workflow |
| GET | `/api/workflow/tasks` | Get current tasks |
| GET | `/api/workflow/agents` | Get agent states + registry |
| GET | `/api/workflow/timeline` | Get timeline events |
| GET | `/api/workflow/session` | Get session info |
| POST | `/api/workflow/reset` | Reset the session |
| GET | `/api/registry` | List all registered agents |
| GET | `/api/registry/<type>` | Get a specific agent's details |
| GET | `/api/memory` | Get memory entries (filter by type) |
| POST | `/api/memory` | Store a memory entry |
| GET | `/api/memory/search` | Search memory by keyword |
| GET | `/api/approvals` | Get pending approvals |
| POST | `/api/approvals/<id>/resolve` | Resolve an approval |
| GET | `/api/analytics` | Get performance analytics |

## Socket.IO Events

All events broadcast on `neuroops:event` with: `event_id, timestamp, trace_id, agent_id, event_type, previous_state, new_state, message, data`.

Key event types: `agent:registered`, `agent:selected`, `agent:activated`, `agent:thinking`, `agent:working`, `agent:completed`, `agent:failed`, `task:created`, `task:finished`, `task:retry`, `task:timeout`, `human:approval_required`, `memory:accessed`, `workflow:started`, `workflow:completed`.

## Getting Started

```bash
pip install -r backend/requirements.txt
python3 backend/app.py
```

Open `http://localhost:5000`, type a request, and click "Deploy Workforce".

## Future Scalability

The storage layer (`core/storage.py`) is isolated behind `SessionStore`. To add SQLite/PostgreSQL, replace the in-memory dicts with DB queries — agent and workflow logic stays unchanged. Vector DB can plug into the Memory Service for semantic search. The Model Provider Layer already supports swapping AI providers via environment variables.
