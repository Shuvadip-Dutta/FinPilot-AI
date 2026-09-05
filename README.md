# FinPilot AI

> An agentic financial research and portfolio optimization platform built with Django, LangGraph, RAG, and LLMs.

FinPilot AI is a modular financial research and decision-support platform that combines structured market data, financial research providers, multi-agent orchestration, large language models, retrieval-augmented generation, deterministic portfolio optimization, provenance tracking, and persistent research sessions.

The platform is designed to demonstrate how an agentic AI system can combine deterministic financial computation with LLM-based reasoning while maintaining structured evidence and traceability.

---

## Project Status

FinPilot AI is currently in active development.

The research and multi-agent backend is substantially implemented and validated. Portfolio workflow integration, SEC filing ingestion, frontend interfaces, and portfolio monitoring are the remaining major product areas.

### Current Status

| Area | Status |
|---|---|
| Research Platform | ✅ Implemented |
| Company Research | ✅ Implemented |
| Financial Analysis | ✅ Implemented |
| Market Analysis | ✅ Implemented |
| News Intelligence | ✅ Implemented |
| Financial Sentiment Analysis | ✅ Implemented |
| Risk Analysis | ✅ Implemented |
| Multi-Agent LangGraph Workflow | ✅ Implemented |
| Authentication | ✅ Implemented |
| Session & Evidence Persistence | ✅ Implemented |
| Provider Fallback & Provenance | ✅ Implemented |
| Model Routing | ✅ Implemented |
| Token Budget Management | ✅ Implemented |
| Observability | ✅ Implemented |
| Model Evaluation | ✅ Implemented |
| RAG Foundation | ✅ Implemented |
| Portfolio Intelligence | ⚠️ Partial |
| Portfolio Optimization Engine | ✅ Implemented |
| Portfolio Optimization Workflow | 🚧 In Progress |
| SEC Filing RAG | 🚧 In Progress |
| Frontend | 🚧 In Progress |
| Portfolio Dashboard | 🚧 In Progress |
| Portfolio Monitoring | 🚧 In Progress |
| Background Processing | 🚧 In Progress |

---

## Table of Contents

- [Overview](#overview)
- [Core Objectives](#core-objectives)
- [Features](#features)
- [Architecture](#architecture)
- [AI Agent Architecture](#ai-agent-architecture)
- [Research Data Architecture](#research-data-architecture)
- [RAG Architecture](#rag-architecture)
- [MCP Architecture](#mcp-architecture)
- [Model Architecture](#model-architecture)
- [Persistence Architecture](#persistence-architecture)
- [Authentication and Authorization](#authentication-and-authorization)
- [Observability](#observability)
- [Testing and Evaluation](#testing-and-evaluation)
- [Development Phases](#development-phases)
- [Current Limitations](#current-limitations)
- [Roadmap](#roadmap)
- [Running the Project](#running-the-project)
- [API Overview](#api-overview)
- [Example Research Workflow](#example-research-workflow)
- [Portfolio Workflow](#portfolio-workflow)
- [Engineering Principles](#engineering-principles)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Project Scope](#project-scope)
- [Future Work](#future-work)
- [Disclaimer](#disclaimer)

---

## Overview

FinPilot AI is designed as an agentic financial research platform.

A user can submit a financial research request for a company or market instrument. The request is routed through a LangGraph workflow where specialized agents perform different parts of the analysis.

The system separates:

- deterministic financial calculations
- external financial data retrieval
- LLM reasoning
- portfolio optimization
- evidence collection
- provenance tracking
- persistence
- observability
- evaluation

This separation helps keep authoritative numerical calculations outside the LLM while allowing language models to interpret and explain structured financial information.

---

## Core Objectives

The main objectives of FinPilot AI are:

1. Build a practical agentic financial research system.
2. Demonstrate multi-agent orchestration using LangGraph.
3. Combine multiple financial data providers behind normalized interfaces.
4. Provide structured financial and market analysis.
5. Use LLMs for grounded interpretation rather than authoritative numerical computation.
6. Maintain evidence and provenance for research outputs.
7. Provide deterministic portfolio optimization.
8. Introduce retrieval-augmented generation for financial documents.
9. Evaluate model quality and workflow reliability.
10. Provide a foundation for an interactive research and portfolio platform.

---

## Features

### Implemented Features

#### Company Research

- Company profile lookup
- Canonical company identification
- Ticker resolution
- ISIN resolution
- Provider-specific symbols
- Legal company name resolution
- Sector and industry information

#### Financial Research

- Financial statements
- Income statements
- Balance sheets
- Cash-flow statements
- Financial metrics
- Valuation ratios
- Profitability ratios
- Key financial indicators

#### Market Research

- Current market prices
- Exchange-specific market information
- Historical market data
- Daily OHLCV data
- High/low ranges
- Market statistics

#### News Intelligence

- Multi-source financial news
- Indian market news
- Marketaux integration
- Provider-based news aggregation
- URL-based deduplication
- News relevance classification
- News summarization
- Financial news interpretation

#### Sentiment Analysis

FinPilot includes a financial-news sentiment component based on the FinBERT model.

Current direction:

```text
Financial News
      ↓
    FinBERT
      ↓
Financial Sentiment
      ↓
  News Agent
      ↓
LLM Interpretation
```

The sentiment component is designed to provide structured sentiment evidence that can then be interpreted by the News Intelligence Agent.

#### Risk Analysis

The Risk Agent combines structured financial, market, and news evidence and generates a grounded qualitative risk assessment.

Potential evidence includes:

- profitability signals
- financial strength
- market behaviour
- news/event signals
- missing information
- provider provenance

#### Explainable AI

FinPilot uses LLMs to explain structured financial results.

The system is designed around:

```text
Structured Evidence
       ↓
 Reasoning Model
       ↓
Grounded Explanation
```

The LLM is not treated as the authoritative source for numerical financial calculations.

#### Multi-Agent Orchestration

LangGraph coordinates multiple specialized agents:

- Financial Analysis Agent
- Market Analysis Agent
- News Intelligence Agent
- Risk Analysis Agent
- Portfolio Intelligence Agent
- Portfolio Optimization Agent
- Final Synthesis Agent

#### RAG Foundation

FinPilot currently provides a Qdrant-based RAG foundation.

Implemented:

- document ingestion API at the pipeline level
- document chunking
- embeddings
- vector storage
- vector similarity retrieval
- metadata filtering
- score thresholding
- retrieval tools
- RAG-specific error handling

#### Portfolio Optimization

The deterministic portfolio optimization engine is implemented.

It includes:

- portfolio return calculation
- covariance-based risk calculation
- volatility
- Sharpe ratio
- bounded long-only allocation
- minimum allocation constraints
- maximum allocation constraints
- feasibility validation
- numerical input validation

The optimization result can also be interpreted by an LLM through the Portfolio Optimization Agent.

The public portfolio workflow is still being integrated.

#### Persistence

FinPilot stores research session information and agent evidence.

Persisted information includes:

- user
- thread ID
- ticker
- market
- route
- workflow status
- latency
- final synthesis
- agent responses
- structured data
- tool usage
- timestamps
- provenance

#### Authentication

Implemented with JWT authentication.

Features include:

- user registration
- JWT token creation
- refresh tokens
- protected APIs
- authenticated research sessions
- user-owned session filtering
- throttling
- CORS configuration

#### Observability

The AI workflow includes structured observability.

Tracked information includes:

- graph lifecycle events
- node lifecycle events
- execution duration
- errors
- safe metadata
- redacted error information
- workflow status

#### Evaluation

FinPilot includes an evaluation layer for:

- model benchmarking
- agent quality
- synthesis quality
- required concepts
- structured output reliability
- tool usage
- latency
- failure rate
- consistency
- end-to-end workflow behaviour

---

## Architecture

The high-level architecture is:

```text
                         ┌──────────────────┐
                         │      Client       │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   Django REST    │
                         │       API        │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   AgentService   │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │    LangGraph     │
                         │     Workflow     │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Workflow Router  │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
       ┌────────────┐      ┌────────────┐      ┌────────────┐
       │ Financial  │      │   Market   │      │    News    │
       │   Agent    │      │   Agent    │      │   Agent    │
       └─────┬──────┘      └─────┬──────┘      └─────┬──────┘
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 │
                                 ▼
                         ┌──────────────────┐
                         │   Risk Agent     │
                         └────────┬─────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │ Portfolio / Optimization │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                         ┌──────────────────┐
                         │ Synthesis Agent  │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Evidence +       │
                         │ Provenance       │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
             ┌──────────────┐            ┌──────────────┐
             │ PostgreSQL   │            │ Observability│
             └──────────────┘            └──────────────┘
```

---

## AI Agent Architecture

### Financial Analysis Agent

Responsible for financial information retrieval and interpretation.

Inputs can include:

- company profile
- financial statements
- key financial metrics
- canonical research context
- provenance

Typical analysis areas:

- revenue
- profitability
- margins
- EPS
- debt
- ROE
- ROCE
- valuation
- important changes

### Market Analysis Agent

Responsible for market-related research.

Inputs can include:

- current price
- daily price information
- historical data
- market statistics

Typical interpretation areas:

- price movement
- historical behaviour
- volatility context
- high/low ranges
- market signals

### News Intelligence Agent

Responsible for financial news analysis.

Inputs include:

- financial news articles
- relevance classification
- article metadata
- sentiment results

The architecture separates **Article Source** from **Data Provider Provenance**. This prevents publisher information from being confused with provider information.

### Risk Analysis Agent

The Risk Agent consumes specialist evidence.

Conceptually:

```text
Financial Evidence
        +
 Market Evidence
        +
  News Evidence
        ↓
   Risk Agent
        ↓
Risk Interpretation
```

Current risk output is qualitative. It does not replace a dedicated quantitative risk engine.

### Portfolio Intelligence Agent

The Portfolio Intelligence layer performs deterministic portfolio calculations.

Current functionality includes:

- invested value
- current portfolio value
- profit/loss
- holding-level calculations
- portfolio-level aggregation

The portfolio workflow is currently being connected to the public API.

### Portfolio Optimization Agent

The Portfolio Optimization Agent does not perform the mathematical optimization itself.

Instead:

```text
 Portfolio Data
      ↓
Deterministic Optimizer
      ↓
 OptimizationResult
      ↓
 LLM Explanation
```

This keeps numerical optimization deterministic while allowing the LLM to explain:

- allocation
- expected return
- volatility
- Sharpe ratio
- trade-offs
- optimization implications

### Final Synthesis Agent

The Synthesis Agent combines specialist outputs.

Inputs may include:

- financial analysis
- market analysis
- news intelligence
- risk analysis
- portfolio analysis
- optimization results
- provenance
- missing information
- workflow errors

The final response is grounded in supplied evidence. The system is designed to prevent the synthesis model from inventing unsupported facts.

---

## Research Data Architecture

FinPilot uses a provider-based research architecture.

```text
                  Research Service
                        │
        ┌───────────────┼─────────────────┐
        │               │                 │
        ▼               ▼                 ▼
     Finnhub         Indian API        Upstox
        │               │                 │
        │               │                 │
        └───────────────┼─────────────────┘
                        │
                        ▼
                Normalized Schemas
                        │
                        ▼
                Canonical Context
```

Additional research/news sources include:

- Marketaux
- Twelve Data
- Indian market providers

The provider layer keeps external API details away from the agents.

### Canonical Company Identity

FinPilot uses a canonical company identity layer.

A company can be identified by:

- ticker
- ISIN
- legal name
- canonical instrument key

Provider-specific symbols are stored separately.

Example concept:

```text
Canonical Company
       │
       ├── Ticker
       ├── ISIN
       ├── Instrument Key
       │
       ├── Indian API Symbol
       ├── Upstox Symbol
       ├── Marketaux Symbol
       └── Other Provider Symbols
```

This prevents provider-specific naming differences from leaking into business logic.

### Provider Reliability and Provenance

Research results include provenance information.

Typical provenance information includes:

- `primary_provider`
- `source`
- `fallback_used`
- `data_status`
- `fallback_reason`

For example:

```text
Primary Provider: Upstox
Source: upstox
Fallback Used: False
Data Status: Complete
```

When fallback occurs:

```text
Primary Provider: Upstox
Source: indian_api
Fallback Used: True
Fallback Reason: unavailable response
```

This information is carried through the research pipeline and can be persisted with research evidence.

---

## RAG Architecture

### Current RAG Foundation

FinPilot uses Qdrant as the vector database.

Current embedding model: `BAAI/bge-small-en-v1.5`

Embedding dimensions: `384`

General retrieval flow:

```text
Document
    ↓
Chunking
    ↓
Embedding
    ↓
 Qdrant
    ↓
Similarity Search
    ↓
Metadata Filtering
    ↓
Retrieved Evidence
```

Supported metadata filtering includes:

- ticker
- market
- document type
- fiscal year

Retrieval also supports a score threshold.

### Current Limitation

The RAG system currently provides a generic document retrieval foundation. It does not yet provide a complete SEC filing ingestion workflow.

The following SEC-specific components remain to be implemented:

- SEC filing source integration
- filing download
- filing parsing
- CIK-based ingestion
- filing metadata
- SEC document indexing
- SEC-specific retrieval
- production ingestion lifecycle

Therefore: the RAG foundation is implemented, but SEC filing RAG is still in progress.

---

## MCP Architecture

FinPilot includes a Model Context Protocol research layer.

The MCP system includes research tools such as:

- company profile
- market data
- financial statements
- key metrics
- historical data
- news
- financial document retrieval

The MCP layer is designed to provide structured research capabilities to AI systems.

Tool-related architecture also includes:

- tool schemas
- tool execution
- tool validation
- access policies
- execution limits
- malformed-input handling

The current canonical LangGraph workflow uses the internal research/tool layer directly. MCP remains an available protocol/tool integration layer rather than being the mandatory boundary for every agent execution.

---

## Model Architecture

FinPilot separates **Workflow routing** from **Model routing**.

Workflow routing decides: *Which agent/workflow should execute?*

Model routing decides: *Which model should perform the task?*

These are intentionally separate concerns.

### Current Model Mapping

| Agent | Model |
|---|---|
| Financial | qwen/qwen3.6-27b |
| Market | qwen/qwen3.6-27b |
| News | qwen/qwen3.8-27b |
| Risk | qwen/qwen3.8-27b |
| Portfolio | qwen/qwen3.8-27b |
| Synthesis | qwen/qwen3.8-27b |

Financial news sentiment uses: `ProsusAI/finbert`

RAG embeddings use: `BAAI/bge-small-en-v1.5`

### Reasoning Model Handling

The Groq provider uses explicit model-specific reasoning configuration.

Current behaviour:

```text
Qwen 3.6 27B
    ↓
Reasoning content preserved

Qwen 3.8 27B
    ↓
Reasoning hidden from final output
```

This avoids treating different model behaviours as if they were identical.

Model selection is configuration-driven while preserving backwards compatibility with the existing LLM abstraction.

### Token and Output Management

FinPilot includes a token budget layer.

Capabilities include:

- request token validation
- completion limits
- safety reserve
- usage tracking
- TPM/TPD budget framework
- degradation tiers
- agent-specific degradation
- provider usage snapshots

Conceptually:

```text
  Request
     ↓
Token Budget Manager
     ↓
 Budget Check
     ↓
 LLM Provider
     ↓
Usage Tracking
     ↓
Degradation if Required
```

The purpose is to avoid excessive model usage and keep the system predictable under provider limits.

---

## Persistence Architecture

FinPilot uses PostgreSQL for application persistence.

### Research Sessions

A research session stores:

- user
- thread ID
- message
- ticker
- market
- route
- status
- synthesis
- latency
- creation time

### Research Evidence

Agent-level evidence stores:

- agent name
- response
- tools used
- structured data
- timestamp

Example:

```text
Research Session
       │
       ├── Financial Evidence
       ├── Market Evidence
       ├── News Evidence
       ├── Risk Evidence
       └── Synthesis Evidence
```

### LangGraph Persistence

The LangGraph workflow supports PostgreSQL checkpoint persistence.

The architecture uses:

```text
LangGraph
    ↓
thread_id
    ↓
Postgres Checkpoint Persistence
```

Memory-based persistence is also used for isolated unit tests.

---

## Authentication and Authorization

FinPilot uses JWT authentication through Django REST Framework Simple JWT.

Authentication endpoints include:

- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/token/`
- `POST /api/v1/auth/token/refresh/`

The API is protected by default.

Research sessions are filtered by authenticated user ownership. This ensures that one user cannot retrieve another user's research sessions through the normal API workflow.

### API Architecture

The primary AI API path is:

```text
HTTP Request
      ↓
Django REST Framework
      ↓
   AIChatView
      ↓
 AgentService
      ↓
LangGraphResearchWorkflow
      ↓
 Workflow Router
      ↓
Specialized Agents
      ↓
     Risk
      ↓
  Synthesis
      ↓
Research Session
      ↓
Research Evidence
      ↓
 API Response
```

The previous direct multi-round AgentService tool loop is no longer the canonical public execution path.

---

## Observability

FinPilot includes a shared logging and observability layer.

Tracked events include:

- graph start
- graph completion
- node start
- node completion
- node failures
- duration
- error information
- safe metadata

Sensitive information is filtered/redacted where appropriate.

---

## Testing and Evaluation

FinPilot has an extensive automated test suite.

Current repository validation:

| Metric | Value |
|---|---|
| Tests | 580 |
| Passed | 580 |
| Failures | 0 |

Tests cover areas including:

- Django APIs
- research services
- provider abstractions
- authentication
- authorization
- agents
- LangGraph
- MCP
- RAG
- portfolio optimization
- token management
- provider fallback
- provenance
- session persistence
- evaluation
- model abstraction

### Test Categories

**Unit Tests** — examples: provider mapping, schemas, agents, routers, optimization, token budgets, parsers.

**API Tests** — examples: authentication, JWT, research endpoints, AI chat, session access.

**Integration Tests** — examples: workflow execution, persistence service, canonical research context, provider fallback.

**Evaluation Tests** — examples: model comparison, output validation, required concepts, tool usage, latency, structured outputs.

### Live Verification

Selected provider and LLM integrations are also tested through controlled manual/live smoke tests. This is kept separate from the default deterministic unit-test suite.

---

## Development Phases

**Phase 1 — Project Foundation ✅**
Django REST Framework backend, PostgreSQL configuration, Docker-based PostgreSQL setup, environment management, `/api/v1` API versioning, structured logging, health endpoint, modular backend structure.

**Phase 2 — Research & Market Data ✅**
Company profile research, US market data through Finnhub, Indian market data, Indian financial statements, Indian key metrics, provider abstraction, normalized schemas, research service, research endpoints, provider/API testing.

**Phase 3 — Historical Data & Multi-Source News ✅**
Historical market data, daily OHLCV, Indian market news, Indian API news, Marketaux, multi-source aggregation, URL deduplication, relevance classification, unified news schemas, Upstox market data/historical data/news, dynamic instrument resolution.

**Phase 4 — Research Platform Hardening ✅**
API standardization, automatic test discovery, lazy provider initialization, provider-specific errors, environment configuration, dynamic provider symbol resolution, API hardening, duplicate test cleanup, comprehensive tests, real provider verification, production-oriented architecture.

**Phase 5 — AI + MCP Foundation ✅**
Groq integration, Qwen integration, LLM provider abstraction, Groq validation, MCP server, MCP research tools, research tool layer, LLM tool schemas, tool-calling foundation, result contracts, prompts, AI chat API, AI tests, live Groq/provider validation.

**Phase 6 — Multi-Agent AI System ✅**
Multi-agent foundation, deterministic workflow router, LangGraph graph state, structured contracts, Financial/Market/News/Risk Agents, Portfolio Intelligence, Portfolio Optimization, Final Synthesis, parallel research workflow, canonical ResearchContext, reliability handling, observability, evaluation infrastructure.

**Phase 7 — Model Evaluation ✅**
Benchmark framework, model comparison, specialist evaluation, synthesis evaluation, tool usage evaluation, structured output checks, latency measurement, representative end-to-end evaluation. Current model matrix is configuration-driven.

**Phase 8 — Evidence & Session Persistence ✅**
ResearchSession, ResearchEvidence, session status, thread IDs, structured evidence, tool usage persistence, synthesis persistence, user filtering, session history.

**Phase 9 — Token and Output Management ✅**
Token budgeting, safety reserve, output limits, usage tracking, quota framework, degradation tiers, agent-specific degradation.

**Phase 10 — Authentication & Authorization ✅**
JWT registration, JWT token generation, refresh tokens, protected APIs, session ownership, user isolation, throttling, CORS configuration.

**Phase 11 — Canonical Provider and Identity Architecture ✅**
Canonical company identities, ISIN resolution, provider symbols, Upstox fundamentals, provider fallback, provenance metadata, normalized provider contracts.

**Phase 12 — API & Workflow Finalization ✅**
Canonical ResearchContext, canonical LangGraph API execution path, AI service facade, provider architecture, provenance integration, authenticated AI workflow, persistence integration, model-specific Groq reasoning behaviour, live workflow verification, final automated test suite.

Current validation: **580 tests, 580 passed.**

---

## Current Limitations

The following areas are intentionally not yet considered fully complete.

### Portfolio Product Integration

The optimization engine exists, but the complete product path still requires:

- portfolio database models
- portfolio API
- holding persistence
- ownership
- canonical portfolio workflow input
- LangGraph dependency injection
- end-to-end API integration
- frontend portfolio interface

### SEC Filing RAG

The current RAG implementation is a generic financial-document retrieval foundation. SEC-specific ingestion is not yet complete.

### Frontend

The current repository does not yet contain the final production frontend experience.

Planned interfaces include:

- authentication
- research chatbot
- research dashboard
- evidence display
- risk view
- portfolio optimization view
- portfolio dashboard

### Portfolio Monitoring

Automated portfolio monitoring is not yet implemented.

Future work may include:

- scheduled portfolio refreshes
- portfolio health checks
- event detection
- alerts
- background processing

### Background Processing

Celery and Redis are not currently part of the active production workflow. They should only be introduced when scheduled ingestion, portfolio monitoring, or other background processing requirements justify them.

---

## Roadmap

**Phase 13 — Documentation & Architecture Polish**
Finalize architecture documentation, document provider interfaces, document data flow, document model routing, document RAG design, document persistence, align README with implementation, finalize developer setup instructions.

**Phase 14 — Portfolio Integration**

```text
Portfolio Model
      ↓
 Holding Model
      ↓
 Portfolio API
      ↓
PortfolioWorkflowInput
      ↓
   LangGraph
      ↓
Portfolio Intelligence
      ↓
Deterministic Optimizer
      ↓
 OptimizationResult
      ↓
 LLM Explanation
      ↓
 Persistence
      ↓
 API Response
```

Tasks: portfolio models, holding models, serializers, API endpoints, user ownership, portfolio workflow input, dependency injection, portfolio evidence persistence, integration tests.

**Phase 15 — SEC Filing RAG**
Planned: SEC source integration, filing retrieval, filing parser, metadata, indexing, provenance, retrieval, financial-agent integration.

**Phase 16 — Frontend**
Planned: registration/login, JWT handling, research chatbot, research dashboard, evidence panel, provenance panel, risk summary, portfolio optimization interface, portfolio dashboard.

**Phase 17 — Portfolio Monitoring**

```text
Stored Portfolio
      ↓
Scheduled Refresh
      ↓
Market / Research Data
      ↓
Portfolio Analysis
      ↓
Risk / Change Detection
      ↓
    Alert
```

Background processing can be introduced at this stage if required.

**Phase 18 — Final Integration & Evaluation**
Final validation will include: complete backend integration, portfolio end-to-end workflow, SEC RAG workflow, frontend integration, authenticated user flow, PostgreSQL persistence, LangGraph checkpoint persistence, Qdrant retrieval, provider integration, model evaluation, token usage, latency, failure handling, final demo workflow.

---

## Running the Project

### Prerequisites

Recommended environment:

- Python 3.11+
- PostgreSQL
- Docker
- Git

### Clone Repository

```bash
git clone <repository-url>
cd FinPilot-AI
```

### Create Virtual Environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project environment.

Example:

```env
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=your-secret-key

DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

DRF_THROTTLE_ANON_RATE=100/day
DRF_THROTTLE_USER_RATE=1000/day

POSTGRES_DB=finpilot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
```

Provider-specific API keys and LLM configuration should also be supplied through environment variables.

### Docker Services

Current infrastructure includes PostgreSQL and Qdrant.

Example Qdrant startup:

```bash
docker run -d \
  --name finpilot-qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant
```

PostgreSQL is configured as the main relational persistence layer.

### Database Setup

Run migrations:

```bash
python manage.py migrate
```

Create a superuser if required:

```bash
python manage.py createsuperuser
```

### Run Development Server

```bash
python manage.py runserver
```

The API is available under `/api/v1/`.

### Run Tests

Run the full application suite:

```bash
python manage.py test apps --noinput
```

Expected current result:

```text
580 tests
580 passed
0 failures
```

---

## API Overview

### Authentication

- **Register:** `POST /api/v1/auth/register/`
- **Obtain Token:** `POST /api/v1/auth/token/`
- **Refresh Token:** `POST /api/v1/auth/token/refresh/`

### Health Check

`GET /api/v1/health/`

### Research

Research endpoints are available under `/api/v1/research/`.

Supported research domains include:

- company profile
- market data
- financial statements
- key metrics
- historical data
- news
- research sessions

### AI Chat

The canonical AI endpoint is:

```text
POST /api/v1/ai/chat/
```

Example request:

```json
{
  "message": "Give me a brief fundamental and market overview of Larsen & Toubro.",
  "ticker": "LT",
  "market": "INDIA"
}
```

The request follows the canonical workflow:

```text
  Django
    ↓
AgentService
    ↓
 LangGraph
    ↓
  Router
    ↓
Specialized Agents
    ↓
   Risk
    ↓
 Synthesis
    ↓
Persistence
    ↓
 Response
```

The response can include:

- final synthesis
- session ID
- thread ID
- route
- tools used
- provenance
- structured research data

---

## Example Research Workflow

Example user request:

> Give me a brief fundamental and market overview of Larsen & Toubro.

Conceptual execution:

```text
        User
         ↓
JWT Authentication
         ↓
Django REST API
         ↓
 LangGraph Router
         ↓
Financial Agent ──→ Financial Providers
         ↓
 Market Agent ─────→ Market Providers
         ↓
  News Agent ───────→ News Providers
         ↓
     Risk Agent
         ↓
  Synthesis Agent
         ↓
Evidence Persistence
         ↓
    PostgreSQL
         ↓
 Final Response
```

For a general research route, Financial, Market, and News agents can execute in parallel before the Risk and Synthesis stages.

---

## Portfolio Workflow

The intended portfolio flow is:

```text
 User Portfolio
      ↓
 Portfolio API
      ↓
Portfolio Workflow Input
      ↓
   LangGraph
      ↓
Portfolio Intelligence
      ↓
Deterministic Optimization
      ↓
 OptimizationResult
      ↓
Qwen Reasoning Model
      ↓
  Explanation
      ↓
 Persistence
      ↓
  Response
```

The mathematical optimizer remains deterministic. The LLM is responsible for explaining the result rather than producing authoritative portfolio weights.

### Example Optimization Concepts

The optimization engine works with concepts such as:

- Expected Return / Expected Portfolio Return
- Volatility / Portfolio Risk
- Sharpe Ratio / Risk-Adjusted Performance
- Allocation Constraints

Example:

```text
Minimum Weight ≤ Asset Weight ≤ Maximum Weight
```

The optimizer also validates feasibility and numerical input conditions.

---

## Engineering Principles

FinPilot follows several design principles.

### 1. Deterministic calculations stay deterministic

Financial calculations should not depend on LLM free-form reasoning. Examples: prices, financial metrics, portfolio values, returns, covariance, volatility, Sharpe ratio, portfolio allocation.

### 2. LLMs interpret structured evidence

LLMs are primarily responsible for reasoning, interpretation, summarization, explanation, and synthesis. They should not be treated as the authoritative numerical source.

### 3. Providers are abstracted

Agents should not depend directly on provider-specific HTTP APIs. Instead:

```text
  Provider
     ↓
Normalized Schema
     ↓
Research Service
     ↓
Research Context
     ↓
   Agent
```

### 4. Provenance is preserved

The system should be able to identify where information came from, whether fallback occurred, whether data is complete, and why fallback occurred.

### 5. Structured context is preferred over prose passing

Specialized agents communicate through structured contracts. This reduces parsing errors, hallucinated values, data loss, and provenance loss.

### 6. Workflow routing and model routing are separate

LangGraph decides *which workflow/agent should execute*. The LLM layer decides *which model should execute the reasoning task*.

### 7. Small-step development

Development follows:

```text
Architecture Decision
        ↓
   Small Change
        ↓
     Tests
        ↓
     Review
        ↓
Integration Verification
        ↓
   Next Change
```

This reduces unnecessary refactoring and makes debugging easier.

---

## Project Structure

```text
FinPilot-AI/
│
├── backend/
│   │
│   ├── apps/
│   │   │
│   │   ├── ai/
│   │   │   ├── agents/
│   │   │   │   ├── base.py
│   │   │   │   ├── financial.py
│   │   │   │   ├── market.py
│   │   │   │   ├── news.py
│   │   │   │   ├── risk.py
│   │   │   │   ├── portfolio_optimization.py
│   │   │   │   └── synthesis.py
│   │   │   │
│   │   │   ├── evaluation/
│   │   │   ├── graph/
│   │   │   │   ├── contracts.py
│   │   │   │   ├── state.py
│   │   │   │   ├── router.py
│   │   │   │   ├── langgraph.py
│   │   │   │   ├── langgraph_workflow.py
│   │   │   │   └── persistence.py
│   │   │   │
│   │   │   ├── mcp/
│   │   │   ├── services/
│   │   │   ├── observability.py
│   │   │   └── tests/
│   │   │
│   │   ├── core/
│   │   │   ├── auth_urls.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── tests.py
│   │   │
│   │   └── research/
│   │       ├── models.py
│   │       ├── serializers.py
│   │       ├── views.py
│   │       ├── urls.py
│   │       ├── services/
│   │       ├── migrations/
│   │       └── tests/
│   │
│   ├── config/
│   │   ├── settings.py
│   │   └── urls.py
│   │
│   └── manage.py
│
├── frontend/
│
├── docker-compose.yml
│
├── requirements.txt
│
└── README.md
```

---

## Technology Stack

### Vector Database

Current: **Qdrant** (original direction was ChromaDB; Qdrant is now the active implementation).

### LLM Provider

Current: **Groq**, with **Qwen** as the primary model family. Model configuration is kept configurable through the LLM abstraction.

### Embeddings

Current: `BAAI/bge-small-en-v1.5` — Device: CPU — Dimension: 384

### Database

Current relational database: **PostgreSQL**, used for application persistence, research sessions, evidence, workflow persistence, and LangGraph checkpoint storage.

### Production-Oriented Design

FinPilot is designed with production-oriented concepts even though it remains a final-year academic project. Examples include:

- provider abstraction
- structured schemas
- centralized exceptions
- authentication
- authorization
- request throttling
- provenance
- observability
- token budgets
- persistent research sessions
- checkpoint persistence
- configuration-driven model selection
- failure handling
- automated testing

The project intentionally avoids unnecessary enterprise infrastructure that is not justified by the current scope.

---

## Project Scope

FinPilot is intentionally **not** a:

- trading engine
- brokerage platform
- order execution system
- crypto trading system
- automated investment advisor
- high-frequency trading platform

The system focuses on:

```text
Financial Research
        +
Agentic Reasoning
        +
    Evidence
        +
Portfolio Analysis
        +
Portfolio Optimization
```

---

## Future Work

Potential future extensions include:

- SEC filing ingestion
- richer financial document RAG
- more sophisticated quantitative risk metrics
- portfolio monitoring
- scheduled research refreshes
- alerting
- additional providers
- expanded geographic market support
- richer frontend visualizations
- report export
- stronger model routing
- improved live evaluation infrastructure
- production deployment

These are intentionally secondary to the core research and portfolio workflow.

### Final Project Vision

The final FinPilot architecture is intended to evolve toward:

```text
                           FINPILOT AI
                               │
                               ▼
                        Django REST API
                               │
                               ▼
                          LangGraph
                               │
                               ▼
                            Router
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
       Financial            Market             News
         Agent              Agent              Agent
            │                  │                  │
            ▼                  ▼                  ▼
      Financial Data      Market Data       News + FinBERT
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                               ▼
                           Risk Agent
                               │
                               ▼
                     Portfolio Intelligence
                               │
                               ▼
                    Deterministic Optimizer
                               │
                               ▼
                       Synthesis Agent
                               │
                               ▼
                      Evidence + Context
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
               PostgreSQL           Observability
                    │
                    ▼
             Final API Response
                    │
                    ▼
                 Frontend
```

### Conclusion

FinPilot AI demonstrates how financial research can be organized as an agentic workflow combining structured financial data, multiple external providers, deterministic calculations, LLM reasoning, specialist agents, LangGraph orchestration, RAG, provenance, persistent evidence, observability, model evaluation, and portfolio optimization.

The project is being developed incrementally, with emphasis on architectural clarity, testability, traceability, and grounded AI behaviour.

The ultimate goal is a practical financial research and portfolio decision-support platform rather than an automated trading system.

---

## Disclaimer

FinPilot AI is an academic/research project intended for experimentation, software engineering study, and financial research.

It is not a licensed financial advisory service and does not provide personalized investment advice.

Portfolio optimization results are mathematical outputs based on the supplied assumptions and data. They should not be interpreted as guaranteed investment returns or recommendations to buy or sell securities.