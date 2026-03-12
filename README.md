# Multimodal RAG — Gemini Embedding 2 + Supabase

Search across text, images, and video using native multimodal embeddings. One model, one vector space, no conversion step.

**Stack:** Gemini Embedding 2 + Supabase (pgvector) + Gradio

## Quick Start

**Option A — Claude Code blueprint (recommended):**
Copy the contents of [`CLAUDE-CODE-BLUEPRINT.md`](CLAUDE-CODE-BLUEPRINT.md) into Claude Code. It builds and configures everything step by step.

**Option B — Manual setup:**

1. Clone this repo
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your keys
4. Paste `migration.sql` into your Supabase SQL Editor
5. `python app.py` — opens at http://localhost:7860
6. Upload files via the Upload tab, query via the Search tab

## Prerequisites

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) (for video chunking)
- [Gemini API key](https://aistudio.google.com/apikey) (free tier available)
- [Supabase project](https://supabase.com/dashboard) (free tier — 500MB)
