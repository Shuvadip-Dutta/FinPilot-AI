# FinPilot Architecture Overview

FinPilot is an AI-powered financial research, market intelligence, and portfolio optimization system built on Django, LangGraph, Qdrant RAG, and Groq LLMs.

## High-Level Architecture

```
Frontend (React Dashboard)
  ↓
Django REST API
  ↓
LangGraph Orchestrator
  ↓
Router
  ↓
Specialized Agents
  ├── Financial Analysis Agent
  ├── Market Analysis Agent
  ├── News Intelligence Agent
  ├── Risk Assessment Agent
  ├── Portfolio Optimization Agent
  └── Synthesis Agent
  ↓
MCP / Financial & Market APIs / Qdrant RAG
  ↓
LLMService
  ↓
TokenBudgetManager
  ↓
GroqProvider
```

## System Components

### 1. Frontend & API Layer
- **Frontend**: React Dashboard delivering interactive financial research interfaces and real-time visualization.
- **Django REST API**: Core backend exposing endpoints for Authentication, Portfolio management, Research sessions, and AI Agent interactions.
- **Persistence**: PostgreSQL backend persisting application domain models, `ResearchSession`, `ResearchEvidence`, and LangGraph state checkpoints.

### 2. Orchestration & Agent Workflow
- **LangGraph**: Stateful multi-agent graph orchestrator using PostgreSQL checkpoint persistence (`PostgresSaver`) for resumable research workflows.
- **Router**: Directs user queries to appropriate individual agents or full multi-agent orchestration flows.
- **Specialized Agents**:
  - **Financial Analysis Agent** (`qwen/qwen3.6-27b`): Analyzes income statements, balance sheets, cash flows, and key financial ratios. Uses Qdrant-based RAG for SEC filings and PDF reports.
  - **Market Analysis Agent** (`qwen/qwen3.6-27b`): Retrieves live exchange quotes, historical price series, and market statistics via Finnhub, Upstox, and Indian API providers.
  - **News Intelligence Agent** (`qwen/qwen3.8-27b`): Aggregates market news, performs relevance filtering and deduplication, and computes authoritative sentiment scores using FinBERT (`ProsusAI/finbert`).
  - **Risk Assessment Agent** (`qwen/qwen3.8-27b`): Evaluates financial statement risk factors, market volatility metrics, and news sentiment signals into structured risk indicators.
  - **Portfolio Optimization Agent** (`qwen/qwen3.8-27b`): Runs deterministic mean-variance optimization, Sharpe ratio calculations, and asset allocation algorithms.
  - **Synthesis Agent** (`qwen/qwen3.8-27b`): Merges multi-agent outputs into unified, grounded financial research reports.

### 3. Data & RAG Infrastructure
- **Qdrant Vector Database**: Vector storage for semantic document chunk search (`BAAI/bge-small-en-v1.5` embeddings) powering RAG workflows.
- **FinBERT Sentiment**: Authoritative deterministic sentiment model (`ProsusAI/finbert`) for news articles and market sentiment aggregation.
- **External Market APIs & MCP**: Integrations with Finnhub, Marketaux, Upstox, Tavily, and Indian stock market providers.

### 4. LLM Infrastructure & Token Budget Management
- **LLMService**: Central abstraction layer managing LLM interactions, model switching, output token bounds, and provider delegation.
- **TokenBudgetManager**: Process-level manager enforcing token limits and tracking quotas across:
  - Max Request Tokens (default: `32768`)
  - Safety Reserve Tokens (default: `1024`)
  - Tool Call Completion Tokens (default: `4096`)
  - TPM Limit (Tokens Per Minute, optional configurable)
  - TPD Limit (Tokens Per Day, optional configurable)
- **GroqProvider**: Provider implementation managing API execution to Groq models.

## Quota-Aware Token Degradation Architecture

FinPilot features a centralized, deterministic token budget degradation framework based on `DegradationTier`:

| Degradation Tier | Remaining Quota Threshold | Agent Adaptation Behavior |
| :--- | :--- | :--- |
| **`NORMAL`** | > 30% quota remaining | Standard execution with full context and normal output token limits. |
| **`CONSTRAINED`** | > 10% and <= 30% quota remaining | Compact context windows, cap output budgets (512–2000 tokens), preserve structured evidence. |
| **`CRITICAL`** | > 0% and <= 10% quota remaining | Minimal context windows, minimal output budgets (256–1000 tokens), preserve key metrics. |
| **`EXHAUSTED`** | 0% quota remaining | Zero LLM calls performed. Activates budget exhaustion fallback strategy. |

### Budget Exhaustion Fallback Behaviors
- **Market, News, Portfolio Agents**: Fall back to 100% deterministic outputs computed from market tools, FinBERT sentiment, and portfolio optimization algorithms without making any LLM calls.
- **Financial, Risk, Synthesis Agents**: Return explicit incomplete-analysis status indicating quota exhaustion, preserving structured numerical evidence without fabricating financial, risk, or synthesis conclusions.

## Per-Agent Model Assignment Matrix

| Agent | Configured Model | Assignment Rationale |
| :--- | :--- | :--- |
| **Financial Analysis Agent** | `qwen/qwen3.6-27b` | High reasoning capacity for complex financial statement analysis |
| **Market Analysis Agent** | `qwen/qwen3.6-27b` | High precision for market trends and quantitative metrics |
| **News Intelligence Agent** | `qwen/qwen3.8-27b` | Efficient execution paired with FinBERT sentiment |
| **Risk Assessment Agent** | `qwen/qwen3.8-27b` | Fast evaluation across cross-domain evidence |
| **Portfolio Optimization Agent** | `qwen/qwen3.8-27b` | Fast summarization of deterministic optimization outputs |
| **Synthesis Agent** | `qwen/qwen3.8-27b` | Balanced output generation for multi-agent synthesis |