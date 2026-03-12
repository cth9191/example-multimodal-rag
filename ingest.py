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
