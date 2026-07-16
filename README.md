# GEOCheck

**Measure your brand visibility in the AI search era.**

Traditional SEO tells you where Google ranks your website.

GEOCheck tells you whether AI engines recommend your brand.

> **Featured Article**: [GEO 2026: How AI Search Engines Decide Which Brands Exist](https://medium.com/@chndouyin/geo-2026-how-ai-search-engines-decide-which-brands-exist-generative-engine-optimization-guide-63dc46c35a40) — *Generative Engine Optimization Guide*

---

## Why GEOCheck?

AI assistants are becoming the new search layer. Your customers are asking ChatGPT, DeepSeek, and Gemini:

- *"What's the best product?"*
- *"Which company should I choose?"*
- *"Who are the market leaders?"*

If AI doesn't mention you, you are invisible.

## Features

✅ **AI Visibility Score** — Cross-engine brand visibility (0-100)
✅ **Citation Intelligence** — Which sources AI uses to reference you
✅ **Multi-Engine Monitoring** — ChatGPT, DeepSeek, Gemini, Claude, Kimi, Perplexity
✅ **Local AI Deployment** — Runs on Ollama, data never leaves your network
✅ **BYOK Privacy Mode** — Bring Your Own API Key / Endpoint / Model
✅ **Enterprise Integration** — Custom providers, private deployment, air-gapped

---

## Quick Start

```bash
# Windows: double-click start.bat
# Linux/Mac: ./start.sh

# Or manually:
pip install -r requirements.txt
python api/server.py
```

Open http://localhost:8020/app/dashboard.html

*Demo data is seeded automatically on first run.*

---

## Deployment Modes

| Mode | How | Cost | Privacy |
|------|-----|------|---------|
| **LOCAL** | Ollama on your machine | $0 | ✅ Air-gapped |
| **CLOUD** | Built-in API integrations | API costs | ⚠️ Via providers |
| **BYOK** | Your endpoint + key | Your infra | ✅ Full control |
| **SMART** | Auto-selects best per task | Varies | Varies |

---

## Architecture

```
Brand Name
    ↓
Provider Router ─── LOCAL / CLOUD / BYOK / SMART
    ↓
AI Engine Response (6+ engines)
    ↓
Citation Analyzer → Domain Authority
    ↓
GEO Score v2 → Mention(30%) + Citation(25%) + Position(20%) + Authority(25%)
    ↓
Visibility Index → Cross-engine ranking
    ↓
SQLite Database
    ↓
API → Dashboard / Report / Alerts
```

---

## Enterprise

- **Private Deployment**: On-premise, air-gapped, data never leaves your network
- **Custom Provider**: Connect your own LLM (vLLM, LM Studio, Xinference, Azure)
- **GEO Strategy**: Citation building, content strategy, AI exposure optimization

Contact: ieqqnet@163.com

---

## GitHub

```bash
git clone https://github.com/biuta666/geocheck
cd geocheck
python api/server.py
```

---

*GEOCheck — AI Visibility Intelligence Platform*
