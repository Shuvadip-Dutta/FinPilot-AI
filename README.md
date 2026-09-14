# FinPilot AI

> An agentic financial research and portfolio optimization platform built with Django, LangGraph, RAG, and LLMs.

FinPilot AI is a modular financial research and decision-support platform that combines structured market data, financial research providers, multi-agent orchestration, large language models, retrieval-augmented generation, deterministic portfolio optimization, provenance tracking, and persistent research sessions.

The platform is designed to demonstrate how an agentic AI system can combine deterministic financial computation with LLM-based reasoning while maintaining structured evidence and traceability.

---

## Project Status

FinPilot AI is now in the integration and deployment-hardening stage.

The core research platform, multi-agent LangGraph workflow, RAG foundation, authentication and authorization, evidence/provenance persistence, deterministic portfolio optimization, quantitative risk analysis, walk-forward backtesting, SEC filing RAG, conversational backtest activation, portfolio monitoring, background processing, and the portfolio frontend and authenticated frontend workflows are implemented and validated.

Current work is focused on production containerization, deployment hardening, and final end-to-end integration.

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
| Authentication & Authorization | ✅ Implemented |
| Session & Evidence Persistence | ✅ Implemented |
| Provider Fallback & Provenance | ✅ Implemented |
| Model Routing | ✅ Implemented |
| Token Budget Management | ✅ Implemented |
| Observability | ✅ Implemented |
| Model Evaluation | ✅ Implemented |
| Generic RAG Foundation | ✅ Implemented |
| SEC Filing RAG | ✅ Implemented |
| Portfolio Intelligence | ✅ Implemented |
| Portfolio Optimization Engine | ✅ Implemented |
| Portfolio Quantitative Risk Engine | ✅ Implemented |
| Portfolio Walk-Forward Backtesting | ✅ Implemented |
| Portfolio REST API | ✅ Implemented |
| Portfolio LangGraph Integration | ✅ Implemented |
| Conversational Backtest Activation | ✅ Implemented |
| Portfolio Monitoring | ✅ Implemented |
| Background Processing | ✅ Implemented |
| Portfolio Alerts | ✅ Implemented |
| Portfolio Dashboard / Frontend | ✅ Implemented |
| Production Backend Container | ✅ Implemented |
| Full Production Deployment | 🚧 In Progress |
| Final End-to-End Integration | 🚧 Planned |

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
- [Docker Build & Deployment](#docker-build--deployment)
- [API Overview](#api-overview)
- [Example Research Workflow](#example-research-workflow)
- [Portfolio Workflow](#portfolio-workflow)
- [Backtesting](#backtesting)
- [Portfolio Monitoring & Alerts](#portfolio-monitoring--alerts)
- [Frontend](#frontend)
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

#### SEC Filing RAG

Built on top of the Qdrant RAG foundation, the SEC filing workflow adds:

- SEC filing source integration
- filing retrieval and parsing
- CIK-based company identification
- filing metadata
- document chunking and embedding generation for filings
- Qdrant indexing
- metadata-aware retrieval
- provenance tracking
- integration with the research/agent architecture

SEC documents are treated as grounded retrieval sources, not authoritative numerical calculators.

#### Portfolio Suite

FinPilot includes a complete, deterministic portfolio quantitative stack, integrated end-to-end through the authenticated API and the LangGraph workflow.

**Portfolio Intelligence**

- portfolio and holding persistence (Django models)
- authenticated portfolio CRUD API
- invested value, current value, profit/loss
- holding-level and portfolio-level aggregation
- portfolio market-data adapter with date-aware historical alignment
- `PortfolioWorkflowInputBuilder` for constructing workflow input

**Portfolio Optimization**

- deterministic `PortfolioOptimizationEngine`
- portfolio return and covariance-based risk calculation
- bounded long-only allocation with minimum/maximum constraints
- feasibility and numerical input validation

**Quantitative Risk**

- deterministic `PortfolioRiskEngine`
- volatility and Sharpe ratio
- structured, computed risk evidence rather than LLM-narrated risk

**Walk-Forward Backtesting**

- deterministic `PortfolioBacktestEngine`
- rolling in-sample/out-of-sample evaluation
- date-aware historical alignment
- transaction-cost-aware simulation
- uses the portfolio's actual persisted initial weights

**Buy-and-Hold Baseline**

- every backtest is compared against a simple buy-and-hold baseline for the same holdings

**Benchmark Comparison**

- backtest results are also compared against a market benchmark

**Relative Metrics**

- `PortfolioBacktestEvaluator` computes strategy, benchmark, and relative performance metrics

**Backtest REST API**

- authenticated `POST /api/v1/portfolio/<portfolio_id>/backtest/`
- `PortfolioBacktestInputBuilder` for constructing backtest inputs
- validated against live Upstox data

**LangGraph Backtest Integration**

- dedicated LangGraph portfolio backtest node
- conditional backtest routing (`include_backtest`, default `False`)
- structured Portfolio Backtest Evidence
- synthesis integration, so backtest results are explained rather than computed by the LLM

**Conversational Backtest Activation**

- natural-language backtest requests interpreted and routed through the AI workflow
- intent interpretation in the conversational/agent layer, parameter extraction in the workflow layer
- numerical simulation still runs entirely in `PortfolioBacktestEngine` / `PortfolioBacktestEvaluator`

**Portfolio Monitoring & Alerts**

- deterministic monitoring checks (concentration, drawdown, unrealized loss) against configurable thresholds
- alert persistence, acknowledgement, and cooldown/deduplication
- concurrency-safe alert creation

**Background Processing**

- Celery workers and Celery Beat scheduling, backed by Redis
- periodic portfolio monitoring fan-out with retry handling for transient failures

All optimization, risk, backtest, and monitoring results can be interpreted by an LLM, but the underlying calculations remain fully deterministic. See [Backtesting](#backtesting) and [Portfolio Monitoring & Alerts](#portfolio-monitoring--alerts) for details.

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

#### Frontend

A React/Vite frontend covers the implemented research and portfolio workflows, including:

- authentication
- portfolio views and portfolio dashboard
- portfolio optimization interface
- quantitative risk presentation
- backtest interaction
- portfolio alerts and monitoring actions, including alert acknowledgement
- integration with the authenticated backend APIs

See [Frontend](#frontend) for more detail.

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
                    ┌─────────────────────────────────┐
                    │ Portfolio / Optimization / Risk  │
                    │      / Optional Backtest         │
                    └────────────────┬──────────────────┘
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

The Portfolio Intelligence layer is fully connected to the authenticated public API and to the LangGraph workflow, including the optimization, quantitative risk, and optional backtest stages.

### Portfolio Optimization Agent

The Portfolio Optimization Agent does not perform the mathematical optimization, quantitative risk calculation, or backtesting itself.

Instead:

```text
 Portfolio Data
      ↓
Deterministic Optimizer
      ↓
 OptimizationResult
      ↓
Deterministic Risk Engine
      ↓
 RiskResult
      ↓
Optional Backtest Engine
      ↓
 BacktestResult (if requested)
      ↓
 LLM Explanation
```

This keeps numerical optimization, quantitative risk, and backtesting deterministic while allowing the LLM to explain:

- allocation
- expected return
- volatility
- Sharpe ratio
- backtest performance (when requested)
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

### SEC Filing RAG

FinPilot now includes an SEC filing retrieval workflow built on top of the Qdrant RAG foundation.

The SEC workflow includes:

- SEC filing source integration
- filing retrieval
- filing parsing
- CIK-based company identification
- filing metadata
- document chunking
- embedding generation
- Qdrant indexing
- metadata-aware retrieval
- provenance tracking
- SEC-specific retrieval workflow
- integration with the research/agent architecture

SEC documents remain grounded retrieval sources rather than authoritative numerical calculators.

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

The last fully verified full-suite baseline was:

| Metric | Value |
|---|---:|
| Tests | 705 |
| Passed | 705 |
| Failures | 0 |
| Errors | 0 |

The suite has since expanded through Phases 13–16. A fresh complete-suite count will be recorded after final deployment integration.

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
- portfolio optimization, risk, and walk-forward backtesting
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

**Phase 13 — SEC Filing RAG ✅**
SEC filing ingestion and retrieval workflow, SEC document processing, CIK-based identification, filing metadata, document indexing, Qdrant integration, SEC-specific retrieval, provenance, and integration with the research workflow.

**Phase 14 — Conversational Backtest ✅**
Natural-language backtest activation, conversational parameter handling, routing into the deterministic portfolio backtest workflow, and LLM explanation of structured backtest results.

**Phase 15 — Portfolio Monitoring & Background Processing ✅**
Deterministic portfolio monitoring, configurable monitoring thresholds, portfolio concentration detection, drawdown detection, unrealized loss detection, alert persistence, acknowledgement, cooldown/deduplication, concurrency-safe alert creation, Celery worker tasks, Celery Beat scheduling, Redis integration, retry handling, and portfolio monitoring fan-out.

**Phase 16 — Deployment Hardening 🚧**
Production Django configuration hardening, startup secret validation, production `DEBUG`/`ALLOWED_HOSTS` handling, static-file configuration, Gunicorn integration, production backend Docker image, non-root container execution, startup migrations, `collectstatic`, container health checks, and deployment preparation.

**Phase 17 — Final Integration & Evaluation ⏳**
Full backend/frontend integration, complete container stack validation, production deployment, end-to-end user workflow verification, final regression suite, performance checks, failure handling verification, and final project demonstration.

**Test suite status:** 705 tests / 705 passed / 0 failures / 0 errors was the last fully verified full-suite count, taken after the portfolio optimization, quantitative risk, and walk-forward backtesting work was completed. The suite has grown further through Phases 13–15, but a fresh full-suite count has not yet been confirmed — this README will be updated with the final verified number once deployment work (Phases 16–17) completes. See [Testing and Evaluation](#testing-and-evaluation).

---

## Current Limitations

FinPilot is feature-complete across the core research, portfolio, RAG, monitoring, and conversational workflows, but final production integration is still in progress.

### Production Deployment

The backend production container is implemented and validated locally.

Remaining deployment work includes:

- production Compose integration
- frontend production container
- Celery worker and Beat services as part of the orchestrated stack
- complete multi-service integration
- managed PostgreSQL / Redis configuration
- production Qdrant configuration
- cloud deployment
- production environment configuration
- deployment smoke tests

### Final Integration

The remaining work focuses on validating the complete system as a single deployable platform rather than adding major new application capabilities.

### Minor Technical Debt

Some smaller technical improvements remain and will be addressed incrementally without changing the core architecture.

---

## Roadmap

### Completed

- Core financial research platform
- Provider abstraction and provenance
- Multi-agent LangGraph workflow
- Model evaluation
- Evidence and session persistence
- Authentication and authorization
- RAG foundation
- SEC Filing RAG
- Portfolio intelligence
- Portfolio optimization
- Quantitative portfolio risk
- Walk-forward backtesting
- Conversational backtest activation
- Portfolio monitoring
- Alerts
- Celery/Redis background processing
- Portfolio frontend
- Production backend containerization

### Current

**Module 16 — Deployment**

Current focus:

- production configuration
- backend containerization
- Gunicorn
- production startup
- frontend production container
- full service orchestration
- container integration testing
- cloud deployment preparation

### Final

**Module 17 — Final Integration & Evaluation**

Planned:

- full-stack integration
- complete end-to-end workflow
- deployment verification
- regression testing
- performance and reliability validation
- final evaluation
- final project demonstration

See [Development Phases](#development-phases) for the detailed phase-by-phase history behind this roadmap.

---

## Running the Project

### Prerequisites

Recommended environment:

- Python 3.12
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

### Collect Static Files

For local/manual execution:

```bash
python manage.py collectstatic --noinput
```

Static files are collected into Django's configured `STATIC_ROOT`. The production Docker image runs `collectstatic` automatically during container startup, before Gunicorn launches.

### Run Development Server

```bash
python manage.py runserver
```

The API is available under `/api/v1/`.

### Run Tests

Run the full application suite:

```bash
python manage.py test apps.core apps.portfolio apps.ai apps.research --verbosity=1
```

Expected current result:

```text
705 tests
705 passed
0 failures
0 errors
```

---

## Docker Build & Deployment

FinPilot AI includes a production-oriented Docker image for the Django backend.

The current backend container:

- uses Python 3.12
- runs Django through Gunicorn
- runs database migrations automatically at startup
- runs `collectstatic` automatically at startup
- uses a non-root runtime user
- exposes port `8000`
- includes a container health check
- supports `SKIP_DJANGO_STARTUP=true` for future Celery worker/Beat containers

### Build the Backend Image

From the repository root:

```bash
docker build -f Dockerfile -t finpilot-backend:phase2 .
```

### Run the Backend Container

The backend requires a Django secret key and PostgreSQL host.

```bash
docker run -p 8000:8000 \
  -e DJANGO_SECRET_KEY=<your-secret> \
  -e POSTGRES_HOST=<postgres-host> \
  finpilot-backend:phase2
```

The example above demonstrates the required startup variables. A fully functional deployment also requires the configured PostgreSQL, Qdrant, Redis, provider, and LLM environment variables.

### Container Startup

The container starts through `backend/docker/entrypoint.sh`.

Startup sequence:

```text
Container Start
      ↓
Environment Validation
      ↓
Django Migrations
      ↓
Collect Static Files
      ↓
   Gunicorn
      ↓
Django WSGI Application
```

Gunicorn serves `config.wsgi:application` on `0.0.0.0:8000`.

### Celery Worker / Beat Extension

The backend image is designed to be reusable for future Celery worker and Beat services.

Set `SKIP_DJANGO_STARTUP=true` to skip automatic migrations and static-file collection and directly execute the supplied container command.

### Container Health Check

The image uses the existing health endpoint, `GET /api/v1/health/`, and exposes a Docker `HEALTHCHECK` against that endpoint.

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

### Portfolio

Authenticated portfolio CRUD endpoints are available under `/api/v1/portfolio/`.

The backtest endpoint is:

```text
POST /api/v1/portfolio/<portfolio_id>/backtest/
```

It returns structured, deterministic backtest results — strategy metrics, buy-and-hold baseline, benchmark comparison, and relative performance — computed by the `PortfolioBacktestEngine` and `PortfolioBacktestEvaluator`. The LLM interprets these results; it does not compute them.

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

The current, implemented portfolio flow is:

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
   Optimization
      ↓
 Quantitative Risk
      ↓
Optional Backtest
      ↓
   Synthesis
      ↓
Evidence + Provenance
      ↓
  Persistence
      ↓
 API Response
```

The mathematical optimizer, risk engine, and backtest engine all remain deterministic. The LLM is responsible for explaining the results rather than producing authoritative portfolio weights, risk figures, or performance metrics.

The backtest stage is **opt-in**: it only runs when the request explicitly sets `include_backtest=True`. The default is `include_backtest=False`, so a standard portfolio optimization/risk request does not run a backtest unless asked for.

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

## Backtesting

FinPilot's portfolio backtesting is a deterministic, quantitative simulation layer — the LLM only interprets and explains the results; it does not compute them.

Key characteristics:

- **Date-aware historical data** — the portfolio market-data adapter aligns historical prices to the actual date range being backtested.
- **Walk-forward evaluation** — a rolling in-sample/out-of-sample split is used rather than a single static backtest window, so the strategy is evaluated on data it was not fit to.
- **Transaction costs** — the simulation accounts for transaction costs rather than assuming frictionless trading.
- **Actual portfolio weights** — the backtest uses the portfolio's actual persisted initial weights, not synthetic or idealized weights.
- **Buy-and-hold baseline** — every backtest is compared against a simple buy-and-hold baseline for the same holdings.
- **Benchmark comparison** — results are also compared against a market benchmark.
- **Strategy / benchmark / relative metrics** — the `PortfolioBacktestEvaluator` computes metrics for the strategy, the benchmark, and the relative performance between them.

Architecture:

```text
Portfolio + Date Range
        ↓
PortfolioBacktestInputBuilder
        ↓
PortfolioBacktestEngine
   (walk-forward, deterministic)
        ↓
PortfolioBacktestEvaluator
        ↓
Strategy / Benchmark / Relative Metrics
        ↓
Structured Portfolio Backtest Evidence
        ↓
LLM Interpretation (Synthesis)
```

Backtesting is available through:

- the authenticated `POST /api/v1/portfolio/<portfolio_id>/backtest/` REST endpoint, and
- an optional LangGraph portfolio backtest node, gated by `include_backtest` (default `False`), so it only runs when explicitly requested.

### Conversational Backtest Activation

FinPilot supports conversational activation of portfolio backtesting through the AI workflow.

Natural-language backtest requests can be interpreted and routed into the existing deterministic portfolio backtest engine.

The architecture keeps:

- intent interpretation in the conversational/agent layer
- parameter extraction in the workflow layer
- numerical simulation in `PortfolioBacktestEngine`
- metric calculation in `PortfolioBacktestEvaluator`
- final explanation in the LLM layer

The LLM does not calculate authoritative backtest metrics.

---

## Portfolio Monitoring & Alerts

FinPilot includes deterministic portfolio monitoring and alert generation.

Current monitoring checks include:

- portfolio concentration above the configured threshold
- historical maximum drawdown above the configured threshold
- unrealized portfolio loss below the configured threshold

Monitoring thresholds are configurable through `MonitoringConfig`.

Alerts support:

- authenticated portfolio ownership checks
- alert persistence
- acknowledgement
- cooldown / duplicate suppression
- ticker-aware concentration deduplication
- concurrency-safe alert creation

Monitoring can be triggered through the portfolio API and is also integrated with background processing.

### Background Processing

FinPilot includes Celery and Redis for scheduled portfolio monitoring.

Current background-processing architecture includes:

- Redis as the broker/backend infrastructure
- Celery worker tasks
- Celery Beat scheduling
- periodic portfolio monitoring
- portfolio-level monitoring fan-out
- retry handling for transient failures

The current production containerization work is preparing the backend image for separate web, worker, and Beat services. The full production Compose stack that orchestrates all three together is the next deployment phase — see [Current Limitations](#current-limitations).

---

## Frontend

The repository includes a React/Vite frontend for the implemented research and portfolio workflows.

Current frontend capabilities include:

- authentication
- portfolio views
- portfolio dashboard
- portfolio optimization interface
- quantitative risk presentation
- backtest interaction
- portfolio alerts
- monitoring actions
- alert acknowledgement
- integration with authenticated backend APIs

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
│   │   ├── portfolio/
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   ├── services/
│   │   │   ├── migrations/
│   │   │   └── tests/
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
│   ├── docker/
│   │   └── entrypoint.sh
│   │
│   └── manage.py
│
├── frontend/
│
├── Dockerfile
│
├── .dockerignore
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

### Backend Server

- Django
- Django REST Framework
- Gunicorn

### Background Processing

- Celery
- Redis

### Containerization

- Docker
- Docker Compose

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

- richer financial document RAG
- additional quantitative risk metrics
- additional financial-data providers
- expanded geographic market support
- richer frontend visualizations
- report export
- stronger model routing
- improved live evaluation infrastructure
- production observability and tracing
- scalability and performance optimization
- additional portfolio monitoring rules

These are secondary to the currently implemented core platform.

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
                    Quantitative Risk Engine
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