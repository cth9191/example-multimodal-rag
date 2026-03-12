"""Gradio web UI for the multimodal RAG system — search + upload/ingest."""

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


# ── Search tab ──────────────────────────────────────────────────────

def search(question: str, top_k: int, source_filter: str):
    if not question.strip():
        return "Please enter a question.", "", None, []

    filter_type = None if source_filter == "All" else source_filter.lower()
    answer, matches = query_rag(question, top_k=int(top_k), source_type=filter_type)

    # Build sources markdown
    sources_md = ""
    top_video = None
    image_previews = []

    for m in matches:
        sim_pct = m["similarity"] * 100
        icon = {"text": "\U0001f4c4", "image": "\U0001f5bc\ufe0f", "video": "\U0001f3ac"}.get(m["source_type"], "\U0001f4ce")
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


# ── Upload / ingest tab ────────────────────────────────────────────

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
        # ── Text ────────────────────────────────────────────────
        if ext in (".md", ".txt"):
            log(f"\U0001f4c4 Detected text file: {filename}")
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
            log(f"  \u2705 Ingested ({len(vector)} dims)")

        # ── Image ───────────────────────────────────────────────
        elif ext in (".png", ".jpg", ".jpeg"):
            mime = "image/png" if ext == ".png" else "image/jpeg"
            log(f"\U0001f5bc\ufe0f Detected image: {filename}")

            # Save to assets/images/ for later preview
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
            log(f"  \u2705 Ingested ({len(vector)} dims)")

        # ── Video ───────────────────────────────────────────────
        elif ext == ".mp4":
            log(f"\U0001f3ac Detected video: {filename}")

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
                log(f"    \u2705 Chunk {i+1} ingested ({len(vector)} dims)")

                shutil.copy2(cpath, os.path.join(ASSETS_VIDEO, chunk_name))

            shutil.rmtree(chunk_dir, ignore_errors=True)
            log(f"  \u2705 All {len(chunk_paths)} chunks ingested")

        else:
            log(f"\u274c Unsupported file type: {ext}")
            log("   Supported: .md, .txt, .png, .jpg, .jpeg, .mp4")

    except Exception as e:
        log(f"\u274c Error: {e}")

    return "\n".join(log_lines)


# ── Gradio app ──────────────────────────────────────────────────────

with gr.Blocks(title="Multimodal RAG") as demo:
    gr.Markdown("# Multimodal RAG — Gemini Embedding 2 + Supabase")

    with gr.Tabs():
        # ── Tab 1: Search ───────────────────────────────────────
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

        # ── Tab 2: Upload & Ingest ──────────────────────────────
        with gr.TabItem("Upload & Ingest"):
            gr.Markdown(
                "Upload files to add them to the knowledge base. "
                "Supported: `.md`, `.txt`, `.png`, `.jpg`, `.mp4`\n\n"
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
