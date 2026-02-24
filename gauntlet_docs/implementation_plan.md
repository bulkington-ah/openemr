# OpenEMR Healthcare AI Agent — Implementation Plan

## Context

We are building a healthcare AI agent that integrates with OpenEMR (an open-source electronic medical records system). The agent lets clinicians ask natural language questions about patients, medications, allergies, appointments, etc. and get answers backed by real data from OpenEMR's API.

This is part of the AgentForge project with three deadlines:
- **MVP (Tuesday):** Working agent with tools, basic eval, deployed
- **Early (Friday):** Verification layer, eval framework, observability
- **Final (Sunday):** Production-ready, open source contribution, all deliverables

The developer is new to AI agents, LLMs, and AI development. Each implementation session should both produce working code AND teach the underlying concepts.

---

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Agent framework | LangGraph | Manages the ReAct loop + state; upgradable to verification graph later |
| LLM | Claude Sonnet | Strong tool use, large context window |
| Backend | Python / FastAPI | Best LangGraph support |
| Frontend | Streamlit | Fast to ship for MVP |
| Observability | LangSmith | Automatic tracing with LangGraph, built-in eval runner |
| Verification | LangGraph nodes | No extra framework; verification as graph nodes |
| Deployment | Existing AWS EC2 + Docker (already provisioned) | Infrastructure already exists in `/infra/` |

---

## Project Structure

```
agent/
├── app.py                ← FastAPI server (entry point)
├── agent.py              ← LangGraph agent (graph, state, ReAct loop)
├── tools/
│   ├── patient.py        ← patient_search, get_patient_details
│   ├── clinical.py       ← get_allergies, get_medications, get_vitals, get_medical_problems
│   ├── scheduling.py     ← get_appointments, search_practitioners
│   ├── billing.py        ← get_insurance
│   └── drug_interactions.py ← drug_interaction_check (NLM RxNorm API)
├── verification/         ← Verification node logic (post-MVP)
├── evals/
│   └── test_cases.json   ← 50+ eval test cases
├── config.py             ← API URLs, keys, settings
├── requirements.txt      ← Python dependencies
├── Dockerfile            ← Container packaging
├── streamlit_app.py      ← Frontend chat UI
└── .env                  ← Secrets (not committed)
```

---

## Key Concepts (for reference)

- **ReAct loop:** Reason → Act (call a tool) → Observe (see result) → Repeat until done. LangGraph implements this for us.
- **Tool use:** We define Python functions with descriptions. Claude reads the descriptions, decides which tool to call, and returns a structured request. LangGraph intercepts Claude's response, runs the function, and feeds the result back to Claude.
- **State:** A Python dictionary that LangGraph passes between steps. Tracks conversation history and current patient context.
- **Verification:** Extra checks that run before a response reaches the user. Implemented as nodes in the LangGraph graph.
- **LangSmith:** Observability platform that auto-traces every step. Set 2 env vars and it works.

---

## Implementation Phases

### Phase 1: MVP (by Tuesday)

#### Step 1: Project scaffolding
- Create `agent/` directory with the structure above
- Set up `requirements.txt` (langgraph, langchain-anthropic, fastapi, uvicorn, streamlit, requests, python-dotenv)
- Create `.env` template for ANTHROPIC_API_KEY, OPENEMR_BASE_URL, LANGCHAIN_API_KEY

#### Step 2: OpenEMR API client
- Create a base HTTP client that authenticates with OpenEMR's OAuth2 API
- OpenEMR API uses OAuth2 bearer tokens
- Registration endpoint: `POST /oauth2/{site}/registration`
- Token endpoint: `POST /oauth2/{site}/token`
- All API calls need `Authorization: Bearer {token}` header

#### Step 3: Build tools (10 OpenEMR tools)
Each tool is a Python function decorated with `@tool` that calls an OpenEMR API endpoint:

1. `patient_search` — `GET /api/patient` (search by name, DOB)
2. `get_patient_details` — `GET /api/patient/:puuid`
3. `get_allergies` — `GET /api/patient/:puuid/allergy`
4. `get_medications` — `GET /api/patient/:pid/medication`
5. `get_vitals` — `GET /api/patient/:pid/encounter/:eid/vital`
6. `get_appointments` — `GET /api/patient/:pid/appointment`
7. `get_medical_problems` — `GET /api/patient/:puuid/medical_problem`
8. `get_encounters` — `GET /api/patient/:puuid/encounter`
9. `get_insurance` — `GET /api/patient/:puuid/insurance`
10. `search_practitioners` — `GET /api/practitioner`

#### Step 4: Build the ReAct agent
- Define `AgentState` (messages + current_patient context)
- Create the LangGraph graph with the ReAct pattern
- System prompt: clinical assistant role, safety guidelines, disclaimer requirements
- Wire up all 10 tools
- Conversation history maintained via LangGraph state

#### Step 5: FastAPI server
- POST `/chat` endpoint — receives user message, returns agent response
- Conversation session management (maintain state across turns)
- Basic error handling (catch exceptions, return graceful errors)

#### Step 6: Streamlit frontend
- Simple chat interface with message history
- Connects to the FastAPI backend
- Display agent responses with formatting

#### Step 7: Basic eval (5 test cases)
- 5 simple test cases with expected outcomes
- Run manually to verify the agent works

#### Step 8: Deploy
- Create `agent/Dockerfile`
- Push to master → existing CI/CD deploys automatically
- Verify agent is accessible at the EC2 public URL

### Phase 2: Early Submission (by Friday)

#### Step 9: Drug interaction check tool (HARD REQUIREMENT)
- Integrate with NLM RxNorm API (free, public)
- `drug_interaction_check(patient_id, proposed_drug)` → check against current meds and allergies
- This is tool #11

#### Step 10: Verification layer (3 types)
Add verification nodes to the LangGraph graph:
- **Hallucination detection:** Compare agent's response against tool results in state. Flag claims not backed by data.
- **Domain constraints:** Enforce safety rules (check allergies before med discussions, never fabricate clinical data, include disclaimers)
- **Confidence scoring:** Tag responses as high/medium/low confidence based on data source

#### Step 11: Eval framework (50+ test cases)
- Create `evals/test_cases.json` with 50+ cases:
  - 20+ happy path (data retrieval for different patients/fields)
  - 10+ edge cases (patient not found, empty data, ambiguous queries)
  - 10+ adversarial (prompt injection, safety bypass attempts)
  - 10+ multi-step (queries requiring multiple tool chains)
- Build eval runner script using LangSmith
- Target: >80% pass rate

#### Step 12: Observability
- Enable LangSmith tracing (set env vars)
- Verify traces appear in LangSmith dashboard
- Add cost tracking (token usage × Claude pricing)
- Add thumbs up/down feedback to Streamlit UI

### Phase 3: Final Submission (by Sunday)

#### Step 13: Additional verification
- Attribution (cite data sources in responses)
- Output validation (schema checks, completeness)
- Fact checking (cross-reference claims against API data)

#### Step 14: Open source & documentation
- Package as reusable Python package
- Architecture doc (1-2 pages)
- AI cost analysis (dev spend + projections at 100/1K/10K/100K users)
- Demo video (3-5 min)
- Social post

#### Step 15: Polish
- Iterate on evals — fix failures, improve pass rate
- Performance optimization (latency targets: <5s single-tool, <15s multi-step)
- Error handling hardening
- Frontend polish

---

## Critical Files (Existing)

| File | Purpose |
|---|---|
| `/infra/main.tf` | AWS infrastructure (EC2, security groups) — already provisioned |
| `/.github/workflows/agent-deploy.yml` | CI/CD pipeline — already configured |
| `/docker/development-easy-light/docker-compose.yml` | OpenEMR + MariaDB — already working |
| `/Documentation/api/` | OpenEMR API documentation |
| `/swagger/openemr-api.yaml` | Full OpenAPI spec (321 KB) |

---

## Verification Plan

After each phase, verify by:

1. **Phase 1 (MVP):**
   - Start OpenEMR locally with `docker compose up` in `docker/development-easy-light/`
   - Run the agent: `cd agent && uvicorn app:app`
   - Open Streamlit: `streamlit run agent/streamlit_app.py`
   - Test: "Look up Phil Dixon" → should return patient data
   - Test: "What are Phil Dixon's allergies?" → should return allergy list
   - Run 5 basic eval test cases
   - Deploy and verify public accessibility

2. **Phase 2 (Early):**
   - Run drug interaction check: "Is amoxicillin safe for [patient with penicillin allergy]?"
   - Verify hallucination detection catches fabricated data
   - Run full 50+ eval suite, check >80% pass rate
   - Check LangSmith dashboard shows traces

3. **Phase 3 (Final):**
   - Full eval suite passes at >80%
   - Demo video recording
   - Package published
   - All deliverables submitted
