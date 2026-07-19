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