# LangGraph Workflow — Research report tool

## Current flow

```text
1) Gather (fast)
   POST /api/research/multi
   START → tavily / news / papers → gather → END

2) Report on demand
   POST /api/research/synthesize
   { sources…, use_llm?: false|true }
   → compile (default) or Gemini enhance
   → structured ResearchReport

3) Export
   POST /api/research/export/markdown
   POST /api/research/export/html   (Print → Save as PDF)
   POST /api/research/export/json
```

### Report sections
Source mix chart · Executive summary · Key findings · News · Academic · Gaps · Media gallery · Sources

### Keys
| Need | Env |
|---|---|
| Web | `TAVILY_API_KEY` |
| Report AI enhance | `GOOGLE_API_KEY` (optional) |

See README for run instructions.
