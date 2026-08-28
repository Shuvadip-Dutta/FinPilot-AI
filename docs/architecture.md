                    +----------------------+
                    |   React Dashboard    |
                    +----------+-----------+
                               |
                          REST API
                               |
+-------------------------------------------------------------+
|                      Django Backend                          |
|-------------------------------------------------------------|
| Authentication                                              |
| Portfolio API                                               |
| Research API                                                |
| Report API                                                  |
| Agent API                                                   |
+-------------------------+-----------------------------------+
                          |
                LangGraph Orchestrator
                          |
        +--------+--------+---------+---------+
        |        |                  |         |
 Research News  Financial      Sentiment   Portfolio
 Agent    Agent Statement      Agent       Agent
                          |
                  Vector Database
                     ChromaDB
                          |
                  Financial Documents
                          |
                 SEC Filings / PDFs
                          |
          Yahoo Finance / NewsAPI / Tavily


#Research Service Architecture v1
                    
                         ResearchService
                               │
                 ┌─────────────┴─────────────┐
                 ↓                           ↓
             Market.US                  Market.INDIA
                 │                           │
                 ↓                           ↓
          FinnhubProvider             IndianAPIProvider
                 │                           │
                 ↓                           ↓
             US Profile              Indian Profile


                    ┌── IndianAPI ──────┐
                    │                   │
Research Request ───┼── Marketaux ──────┼──> NewsArticle
                    │                   │
                    └── Upstox News ────┘
                              ↓
                       Deduplicate
                              ↓
                       Relevance filter
                              ↓
                       Combined News

                       

             ResearchService
                    │
              NewsAggregator
              /            \
             ↓              ↓
        IndianAPI       Marketaux
          10              N
       articles        articles
             \              /
              ↓            ↓
                Normalize
                    ↓
               Deduplicate
                    ↓
             Sort by date
                    ↓
               NewsResearch