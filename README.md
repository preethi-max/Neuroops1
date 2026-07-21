# NeuroOps - Autonomous AI Workforce for Software Teams

An autonomous multi-agent AI system. A user submits one request; a CEO Agent
analyzes it, a Task Planner builds a DAG, a Scheduler activates only the
required agents, agents collaborate in parallel, and the CEO merges all
outputs into a final report — all streamed in real time.

## Tech Stack

- **Backend**: Python, Flask, Flask-SocketIO, LangGraph, SQLAlchemy, SQLite
- **Frontend**: HTML, CSS, Vanilla JavaScript, Three.js
- **No React, Next.js, Firebase, or Supabase**

## Architecture

```
User Request
  -> CEO Agent (analyze intent, identify departments)
  -> Task Planner (build task DAG with dependencies)
  -> Scheduler (wake only required agents, execute in parallel, respect deps)
  -> AI Agents (Engineering, Design, Research, Management, Communication, Memory)
  -> Result Collection
  -> CEO Agent (synthesize final report)
  -> Final Response
```

## Folder Structure

```
backend/
├── app.py                  # Flask + Socket.IO entry point
├── config.py               # Configuration
├── requirements.txt
├── core/                   # Phase 2 intelligence layer
│   ├── models.py            # Task, AgentState, AgentResult, TimelineEvent
│   ├── storage.py           # In-memory SessionStore (isolated, DB-ready)
│   ├── event_bus.py         # Socket.IO event broadcaster
│   ├── base_agent.py        # BaseAgent contract (think, emit, return result)
│   ├── ceo_agent.py         # CEO: analyze, plan, delegate, synthesize
│   ├── task_planner.py      # Request -> structured task DAG
│   ├── scheduler_service.py # Parallel exec, deps, retries, timeouts
│   └── workflow.py          # LangGraph StateGraph workflow
├── agents/                 # AI agents (one contract, 11 types)
│   ├── registry.py          # agent_type -> class mapping
│   ├── engineering.py       # CodeWriter, Debugger, Reviewer, Documentation
│   ├── design.py            # UISuggestion, Wireframe
│   ├── research.py          # DocumentSearch, Summarizer
│   └── support_agents.py    # TaskPlanner, Notification, Memory
├── api/                    # REST blueprints
│   ├── routes.py            # Phase 1 health/stats/tasks
│   └── workflow_routes.py   # Phase 2 workflow endpoints
├── scheduler/              # Phase 1 cron-style scheduler
├── services/               # Phase 1 agent/task services
├── memory/                 # Phase 1 memory service
├── database/               # SQLAlchemy connection
├── models/                 # Phase 1 ORM models
└── utils/                  # Logging, error handling
frontend/
├── index.html              # Dashboard with 3D viz
├── style.css               # Dark theme, responsive
└── script.js               # REST + Socket.IO + Three.js client
assets/
```

## AI Agents

| Department | Agent | Purpose |
|-----------|-------|---------|
| Engineering | CodeWriter | Writes code from specs |
| Engineering | Debugger | Finds and fixes bugs |
| Engineering | Reviewer | Reviews code quality |
| Engineering | Documentation | Generates docs |
| Design | UISuggestion | Suggests UI improvements |
| Design | Wireframe | Text-based wireframes |
| Research | DocumentSearch | Searches documents |
| Research | Summarizer | Condenses text |
| Management | TaskPlanner | Decomposes requests |
| Communication | Notification | Formats notifications |
| Memory | Memory | Stores session summaries |

Every agent follows the same contract: receive structured task, think, return
output + confidence + logs + execution time, emit state transitions.

## Agent States

`sleeping` -> `thinking` -> `working` -> `completed` | `failed` | `waiting_approval`

Every transition is emitted via Socket.IO as `neuroops:event`.

## REST API (Phase 2)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/workflow/submit` | Submit a request to the autonomous workflow |
| GET | `/api/workflow/tasks` | Get current tasks |
| GET | `/api/workflow/agents` | Get agent states + registry |
| GET | `/api/workflow/timeline` | Get timeline events |
| GET | `/api/workflow/session` | Get session info + conversation + memory |
| POST | `/api/workflow/reset` | Reset the session |
| GET | `/api/workflow/registry` | List all agent types |

## Socket.IO Events

All events broadcast on the `neuroops:event` channel:
- `workflow:started`, `workflow:completed`, `workflow:failed`
- `ceo:started`, `ceo:analysis`, `ceo:planning`, `ceo:completed`
- `planner:started`, `planner:completed`
- `task:created`, `task:finished`, `task:failed`, `task:retry`, `task:timeout`
- `scheduler:started`, `scheduler:wave`, `scheduler:completed`
- `agent:activated`, `agent:thinking`, `agent:working`, `agent:completed`, `agent:failed`

## Getting Started

```bash
pip install -r backend/requirements.txt
python3 backend/app.py
```

Open `http://localhost:5000`, type a request, and click "Deploy Workforce".

## Design for Future Phases

The storage layer (`core/storage.py`) is isolated behind `SessionStore`. To add
SQLite/PostgreSQL, replace the in-memory dicts with DB queries — agent and
workflow logic stays unchanged. Vector DB and long-term memory can plug into
the Memory agent. Auth can wrap the workflow blueprint.
