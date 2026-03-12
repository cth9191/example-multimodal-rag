# Multimodal RAG — Claude Code Blueprint

Copy the prompt below into Claude Code. It will build the entire project, pause to collect your API keys, and walk you through the Supabase setup.

---

## Copy Everything Below This Line Into Claude Code

```
Build me a multimodal RAG system using Gemini Embedding 2 + Supabase + Gradio. This system embeds text, images, and video NATIVELY using Google's multimodal embedding model, stores everything in Supabase (Postgres + pgvector), and provides a Gradio web UI with search + upload/ingest tabs.

Follow these steps exactly. Pause and ask me for input where indicated.

---

### Step 1: Project Setup

Create a project directory called `multimodal-rag` with this structure:

```
multimodal-rag/
├── .env
├── config.py
├── migration.sql
├── video_chunker.py
├── ingest.py
├── query.py
├── app.py
└── assets/
    ├── docs/
    ├── images/
    └── video/
```

Install these Python packages:
```
pip install google-genai supabase python-dotenv gradio opencv-python
```

Also confirm ffmpeg is available (needed for video chunking):
```
ffmpeg -version
```
If ffmpeg is not installed, tell me how to install it for my OS before continuing.

---

### Step 2: Credentials (ASK ME)

**Pause here and ask me for these three values:**

1. **Gemini API Key** — from https://aistudio.google.com/apikey (free tier available)
2. **Supabase Project URL** — from https://supabase.com/dashboard → Settings → API
3. **Supabase Anon Key** — same page as above

Create `.env` with:
```
GEMINI_API_KEY=<my key>
SUPABASE_URL=<my url>
SUPABASE_KEY=<my anon key>
```

---

### Step 3: Config

Create `config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

EMBEDDING_MODEL = "gemini-embedding-2-preview"
EMBEDDING_DIM = 1536
LLM_MODEL = "gemini-3.1-flash-lite-preview"
```

**IMPORTANT model notes:**
- `gemini-embedding-2-preview` is Google's first multimodal embedding model. It embeds text, images, video, and audio into the SAME vector space natively.
- `gemini-3.1-flash-lite-preview` is the cheapest Gemini LLM ($0.25/M tokens). We use it for generating text descriptions of images/video and for generating answers to queries.
- We use 1536 dimensions because pgvector's HNSW index has a 2,000-dim limit. Gemini Embedding 2 supports MRL (Matryoshka Representation Learning) so truncating to 1536 has minimal quality loss.
- Before writing any code, verify these model IDs are still current by checking Google AI Studio docs. Model IDs change.

---

### Step 4: Database Migration

Create `migration.sql` with the SQL below. Then **tell me to paste this into my Supabase dashboard SQL Editor and click Run:**

```sql
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT,
  embedding VECTOR(1536),
  source_type TEXT NOT NULL,
  source_file TEXT,
  chunk_index INT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_embedding
  ON documents USING hnsw (embedding vector_cosine_ops);

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 5,
  filter_source_type TEXT DEFAULT NULL
) RETURNS TABLE(
  id UUID,
  content TEXT,
  source_type TEXT,
  source_file TEXT,
  chunk_index INT,
  metadata JSONB,
  similarity FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id, d.content, d.source_type, d.source_file,
    d.chunk_index, d.metadata,
    1 - (d.embedding <=> query_embedding) AS similarity
  FROM documents d
  WHERE (filter_source_type IS NULL OR d.source_type = filter_source_type)
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

**Wait for me to confirm the migration is applied before continuing.**

---

### Step 5: Video Chunker

Create `video_chunker.py`. Gemini Embedding 2 can only handle 128 seconds of video per request, so we split longer videos into ~97-second segments with 15-second overlap:

```python
"""Split a video into segments for Gemini Embedding 2 (128s max per chunk)."""

import os
import subprocess
import cv2


def get_duration(video_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def chunk_video(
    input_path: str,
    output_dir: str = "assets/video",
    segment_duration: int = 97,
    overlap: int = 15,
) -> list[str]:
    """Split video into overlapping segments under 128s each."""
    os.makedirs(output_dir, exist_ok=True)
    duration = get_duration(input_path)
    chunks = []
    start = 0
    index = 0

    while start < duration:
        chunk_path = os.path.join(output_dir, f"chunk_{index:03d}.mp4")
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-t", str(segment_duration),
            "-i", input_path, "-c", "copy", chunk_path,
        ]
        subprocess.run(cmd, capture_output=True)
        chunks.append(chunk_path)
        print(f"Created {chunk_path} (start={start}s)")
        start += segment_duration - overlap
        index += 1

    return chunks


def extract_thumbnail(video_path: str, output_path: str | None = None) -> str:
    """Extract the middle frame from a video as a JPEG thumbnail."""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError(f"Failed to read frame from {video_path}")

    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_thumb.jpg"

    cv2.imwrite(output_path, frame)
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python video_chunker.py <video_file>")
        sys.exit(1)
    video_file = sys.argv[1]
    print(f"Chunking {video_file}...")
    chunk_paths = chunk_video(video_file)
    print(f"\nCreated {len(chunk_paths)} chunks.")
```

---

### Step 6: Ingestion Script

Create `ingest.py`. This is the core of the system. Key architecture decision:

**For images and video, we make TWO separate API calls:**
1. **Gemini Embedding 2** embeds the raw media natively into a vector — this powers SEARCH
2. **Gemini 3.1 Flash-Lite** watches/looks at the media and writes a text description — this goes in the `content` column so the answer-generating LLM has something to reference

The embedding and the description serve completely different purposes. The vector finds the match. The description lets the LLM talk about it. Without the description, media matches would be "ghost matches" — found by search but silent in the answer.

This is different from frameworks like RAG-Anything where the vector comes FROM the text description (lossy). In our system the vector comes from the actual media (native).

```python
"""Ingest text documents, images, and video chunks into Supabase via Gemini Embedding 2."""

import os
import glob
from google import genai
from google.genai import types
from supabase import create_client

from config import (
    GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY,
    EMBEDDING_MODEL, EMBEDDING_DIM, LLM_MODEL,
)

gemini = genai.Client(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- Embedding helpers ---

def embed_text(text: str) -> list[float]:
    result = gemini.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return result.embeddings[0].values


def embed_image(image_path: str) -> list[float]:
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    mime = "image/png" if image_path.endswith(".png") else "image/jpeg"
    result = gemini.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=types.Content(parts=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
        ]),
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    return result.embeddings[0].values


def embed_video(video_path: str) -> list[float]:
    with open(video_path, "rb") as f:
        video_bytes = f.read()
    result = gemini.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=types.Content(parts=[
            types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
        ]),
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    return result.embeddings[0].values


# --- Description generation (for content column on non-text items) ---

def describe_content(file_path: str, mime_type: str) -> str:
    """Use Gemini to generate a text description of an image or video."""
    with open(file_path, "rb") as f:
        data = f.read()
    response = gemini.models.generate_content(
        model=LLM_MODEL,
        contents=types.Content(parts=[
            types.Part.from_bytes(data=data, mime_type=mime_type),
            types.Part.from_text(text=
                "Describe this content in detail for a knowledge base. "
                "Include all key concepts, processes, and relationships shown."
            ),
        ]),
    )
    return response.text


# --- Supabase insertion ---

def insert_document(
    content: str,
    embedding: list[float],
    source_type: str,
    source_file: str,
    chunk_index: int | None = None,
    metadata: dict | None = None,
):
    supabase.table("documents").insert({
        "content": content,
        "embedding": embedding,
        "source_type": source_type,
        "source_file": source_file,
        "chunk_index": chunk_index,
        "metadata": metadata or {},
    }).execute()


# --- Ingestion pipelines ---

def ingest_text_docs(docs_dir: str = "assets/docs"):
    md_files = glob.glob(os.path.join(docs_dir, "*.md"))
    for path in md_files:
        filename = os.path.basename(path)
        print(f"Ingesting text: {filename}")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        vector = embed_text(text)
        insert_document(
            content=text,
            embedding=vector,
            source_type="text",
            source_file=filename,
        )
        print(f"  Done ({len(vector)} dims)")


def ingest_images(images_dir: str = "assets/images"):
    image_files = glob.glob(os.path.join(images_dir, "*.png")) + \
                  glob.glob(os.path.join(images_dir, "*.jpg"))
    for path in image_files:
        filename = os.path.basename(path)
        print(f"Ingesting image: {filename}")
        mime = "image/png" if path.endswith(".png") else "image/jpeg"
        description = describe_content(path, mime)
        vector = embed_image(path)
        insert_document(
            content=description,
            embedding=vector,
            source_type="image",
            source_file=filename,
            metadata={"description": description},
        )
        print(f"  Done ({len(vector)} dims)")


def ingest_video_chunks(video_dir: str = "assets/video"):
    chunk_files = sorted(glob.glob(os.path.join(video_dir, "chunk_*.mp4")))
    for i, path in enumerate(chunk_files):
        filename = os.path.basename(path)
        print(f"Ingesting video chunk: {filename}")
        description = describe_content(path, "video/mp4")
        vector = embed_video(path)
        insert_document(
            content=description,
            embedding=vector,
            source_type="video",
            source_file=filename,
            chunk_index=i,
            metadata={"description": description, "chunk_index": i},
        )
        print(f"  Done ({len(vector)} dims)")


if __name__ == "__main__":
    print("=== Ingesting text documents ===")
    ingest_text_docs()

    print("\n=== Ingesting images ===")
    ingest_images()

    print("\n=== Ingesting video chunks ===")
    ingest_video_chunks()

    print("\nIngestion complete.")
```

---

### Step 7: Query Engine

Create `query.py`:

```python
"""Query engine: embed question -> similarity search -> Gemini LLM answer."""

from google import genai
from google.genai import types
from supabase import create_client

from config import (
    GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY,
    EMBEDDING_MODEL, EMBEDDING_DIM, LLM_MODEL,
)

gemini = genai.Client(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def query_rag(
    question: str,
    top_k: int = 5,
    source_type: str | None = None,
) -> tuple[str, list[dict]]:
    """Run a RAG query: embed -> search Supabase -> generate answer."""
    # 1. Embed the question
    result = gemini.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[question],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    query_vector = result.embeddings[0].values

    # 2. Search Supabase via RPC
    rpc_params = {
        "query_embedding": query_vector,
        "match_count": top_k,
    }
    if source_type:
        rpc_params["filter_source_type"] = source_type

    matches = supabase.rpc("match_documents", rpc_params).execute()

    if not matches.data:
        return "No relevant documents found.", []

    # 3. Build context from matches
    context_parts = []
    for m in matches.data:
        label = f"[{m['source_type'].upper()}] {m['source_file']}"
        if m.get("chunk_index") is not None:
            label += f" (chunk {m['chunk_index']})"
        label += f" -- similarity: {m['similarity']:.3f}"
        context_parts.append(f"{label}\n{m['content']}")

    context = "\n\n---\n\n".join(context_parts)

    # 4. Generate answer with Gemini LLM
    prompt = (
        "You are a helpful assistant answering questions based on a multimodal "
        "knowledge base containing text documents, images, and video segments.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Provide a clear, detailed answer based on the context above. "
        "Reference specific sources when possible."
    )
    response = gemini.models.generate_content(model=LLM_MODEL, contents=prompt)

    return response.text, matches.data


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "How do we handle form validation?"
    print(f"Query: {question}\n")
    answer, sources = query_rag(question)
    print(f"Answer:\n{answer}\n")
    print(f"Sources ({len(sources)}):")
    for s in sources:
        print(f"  [{s['source_type']}] {s['source_file']} -- {s['similarity']:.3f}")
```

---

### Step 8: Gradio Web UI

Create `app.py`. This has two tabs:
- **Search** — query the knowledge base, shows answer + sources + media previews (video player, image gallery)
- **Upload & Ingest** — drag-and-drop files, auto-chunks video, embeds and stores everything

```python
"""Gradio web UI for the multimodal RAG system -- search + upload/ingest."""

import os
import shutil
import tempfile

import gradio as gr

from query import query_rag
from ingest import (
    embed_text, embed_image, embed_video,
    describe_content, insert_document,
)
from video_chunker import chunk_video

ASSETS_VIDEO = os.path.join("assets", "video")
ASSETS_IMAGES = os.path.join("assets", "images")


# -- Search tab --

def search(question: str, top_k: int, source_filter: str):
    if not question.strip():
        return "Please enter a question.", "", None, []

    filter_type = None if source_filter == "All" else source_filter.lower()
    answer, matches = query_rag(question, top_k=int(top_k), source_type=filter_type)

    sources_md = ""
    top_video = None
    image_previews = []

    for m in matches:
        sim_pct = m["similarity"] * 100
        icon = {"text": "📄", "image": "🖼️", "video": "🎬"}.get(m["source_type"], "📎")
        sources_md += f"### {icon} {m['source_file']}\n"
        sources_md += f"**Type:** {m['source_type']} | **Similarity:** {sim_pct:.1f}%"
        if m.get("chunk_index") is not None:
            sources_md += f" | **Chunk:** {m['chunk_index']}"
        sources_md += "\n\n"
        preview = m["content"][:300] + "..." if len(m["content"]) > 300 else m["content"]
        sources_md += f"{preview}\n\n---\n\n"

        # Collect media files for preview
        if m["source_type"] == "video" and top_video is None:
            path = os.path.join(ASSETS_VIDEO, m["source_file"])
            if os.path.exists(path):
                top_video = path

        if m["source_type"] == "image":
            path = os.path.join(ASSETS_IMAGES, m["source_file"])
            if os.path.exists(path):
                image_previews.append(path)

    return answer, sources_md, top_video, image_previews


# -- Upload / ingest tab --

def ingest_file(file) -> str:
    """Accept a single uploaded file, detect type, embed, and store."""
    if file is None:
        return "No file uploaded."

    filepath = file.name if hasattr(file, "name") else str(file)
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()

    log_lines: list[str] = []

    def log(msg: str):
        log_lines.append(msg)

    try:
        # -- Text --
        if ext in (".md", ".txt"):
            log(f"Detected text file: {filename}")
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            log("  Embedding text...")
            vector = embed_text(text)
            insert_document(
                content=text,
                embedding=vector,
                source_type="text",
                source_file=filename,
            )
            log(f"  Ingested ({len(vector)} dims)")

        # -- Image --
        elif ext in (".png", ".jpg", ".jpeg"):
            mime = "image/png" if ext == ".png" else "image/jpeg"
            log(f"Detected image: {filename}")

            os.makedirs(ASSETS_IMAGES, exist_ok=True)
            saved_path = os.path.join(ASSETS_IMAGES, filename)
            shutil.copy2(filepath, saved_path)
            log(f"  Saved to {saved_path}")

            log("  Generating description...")
            description = describe_content(filepath, mime)
            log("  Embedding image...")
            vector = embed_image(filepath)
            insert_document(
                content=description,
                embedding=vector,
                source_type="image",
                source_file=filename,
                metadata={"description": description},
            )
            log(f"  Ingested ({len(vector)} dims)")

        # -- Video --
        elif ext == ".mp4":
            log(f"Detected video: {filename}")

            chunk_dir = tempfile.mkdtemp(prefix="rag_chunks_")
            log("  Chunking video (97s segments, 15s overlap)...")
            chunk_paths = chunk_video(filepath, output_dir=chunk_dir)
            log(f"  Created {len(chunk_paths)} chunks")

            os.makedirs(ASSETS_VIDEO, exist_ok=True)

            for i, cpath in enumerate(chunk_paths):
                chunk_name = os.path.basename(cpath)
                log(f"  Processing chunk {i+1}/{len(chunk_paths)}: {chunk_name}")

                log("    Generating description...")
                description = describe_content(cpath, "video/mp4")
                log("    Embedding video chunk...")
                vector = embed_video(cpath)

                insert_document(
                    content=description,
                    embedding=vector,
                    source_type="video",
                    source_file=chunk_name,
                    chunk_index=i,
                    metadata={"description": description, "chunk_index": i,
                              "source_video": filename},
                )
                log(f"    Chunk {i+1} ingested ({len(vector)} dims)")

                shutil.copy2(cpath, os.path.join(ASSETS_VIDEO, chunk_name))

            shutil.rmtree(chunk_dir, ignore_errors=True)
            log(f"  All {len(chunk_paths)} chunks ingested")

        else:
            log(f"Unsupported file type: {ext}")
            log("   Supported: .md, .txt, .png, .jpg, .jpeg, .mp4")

    except Exception as e:
        log(f"Error: {e}")

    return "\n".join(log_lines)


# -- Gradio app --

with gr.Blocks(title="Multimodal RAG") as demo:
    gr.Markdown("# Multimodal RAG -- Gemini Embedding 2 + Supabase")

    with gr.Tabs():
        with gr.TabItem("Search"):
            gr.Markdown(
                "Search across text documents, images, and video segments "
                "using native multimodal embeddings."
            )
            with gr.Row():
                with gr.Column(scale=3):
                    question = gr.Textbox(
                        label="Question",
                        placeholder="e.g. How do we handle form validation?",
                        lines=2,
                    )
                with gr.Column(scale=1):
                    top_k = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1,
                        label="Results",
                    )
                    source_filter = gr.Radio(
                        choices=["All", "Text", "Image", "Video"],
                        value="All",
                        label="Filter by type",
                    )
            search_btn = gr.Button("Search", variant="primary")

            with gr.Row():
                with gr.Column():
                    answer_output = gr.Markdown(label="Answer")
                with gr.Column():
                    sources_output = gr.Markdown(label="Sources")

            gr.Markdown("### Media Preview")
            with gr.Row():
                with gr.Column():
                    video_preview = gr.Video(label="Top Video Match", visible=True)
                with gr.Column():
                    image_preview = gr.Gallery(
                        label="Matched Images",
                        columns=2,
                        height="auto",
                    )

            search_btn.click(
                fn=search,
                inputs=[question, top_k, source_filter],
                outputs=[answer_output, sources_output, video_preview, image_preview],
            )
            question.submit(
                fn=search,
                inputs=[question, top_k, source_filter],
                outputs=[answer_output, sources_output, video_preview, image_preview],
            )

        with gr.TabItem("Upload & Ingest"):
            gr.Markdown(
                "Upload files to add them to the knowledge base. "
                "Supported: .md, .txt, .png, .jpg, .mp4\n\n"
                "Videos are automatically chunked into ~97s segments before embedding."
            )
            file_input = gr.File(
                label="Drop a file here",
                file_types=[".md", ".txt", ".png", ".jpg", ".jpeg", ".mp4"],
            )
            ingest_btn = gr.Button("Ingest", variant="primary")
            ingest_log = gr.Textbox(
                label="Ingestion Log",
                lines=15,
                interactive=False,
            )
            ingest_btn.click(
                fn=ingest_file,
                inputs=[file_input],
                outputs=[ingest_log],
            )

if __name__ == "__main__":
    demo.launch()
```

---

### Step 9: Launch & Test

1. **Tell me to go paste the migration SQL into my Supabase SQL Editor** (if not done already)
2. Run `python app.py` to start the Gradio UI
3. Tell me to open http://localhost:7860
4. Tell me to go to the "Upload & Ingest" tab and upload my files:
   - Text files (.md, .txt) — these get embedded directly
   - Images (.png, .jpg) — these get a native image embedding + an LLM-generated description
   - Videos (.mp4) — these get auto-chunked into ~97s segments, each chunk gets a native video embedding + description
5. After uploading, switch to the "Search" tab and try queries like:
   - "How do we handle form validation?"
   - "What does the training cover?"
   - "What is the system architecture?"
6. Results should come back from multiple modalities — text docs, video clips, and images — all found through the same vector search

---

### Architecture Summary (for your reference, don't build anything extra)

**Two models, two jobs:**
- `gemini-embedding-2-preview` = the search engine. Turns any content into 1,536 numbers. Same vector space for text, images, video.
- `gemini-3.1-flash-lite-preview` = the reader. Describes media content and generates answers from retrieved context.

**Database columns serve different purposes:**
- `embedding` column = native vector from the RAW media. Used ONLY for similarity search.
- `content` column = text description (or raw text for text docs). Used ONLY so the LLM can reference it in answers.

**Why 1536 dimensions:** pgvector HNSW index limit is 2,000. Gemini Embedding 2 supports MRL so truncating to 1536 has minimal quality loss.

**Why 97s video chunks with 15s overlap:** Gemini Embedding 2 maxes out at 128s per video input. 97s gives headroom, 15s overlap prevents losing context at cut points.
```
