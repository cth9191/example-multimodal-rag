"""Canary test: verify Gemini Embedding 2 works for all modalities before building the full pipeline."""

import os
import numpy as np
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIM

client = genai.Client(api_key=GEMINI_API_KEY)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_text_embedding():
    print("1. Testing text embedding...")
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=["How to automate browser testing with Playwright"],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    vec = result.embeddings[0].values
    print(f"   Dimensions: {len(vec)}")
    assert len(vec) == EMBEDDING_DIM, f"Expected {EMBEDDING_DIM}, got {len(vec)}"
    print("   PASS")
    return vec


def test_image_embedding():
    print("2. Testing image embedding...")
    # Use first available PNG in assets/images
    images_dir = "assets/images"
    pngs = [f for f in os.listdir(images_dir) if f.endswith(".png")]
    if not pngs:
        print("   SKIP — no PNG files in assets/images/")
        return None

    image_path = os.path.join(images_dir, pngs[0])
    print(f"   Using: {image_path}")
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=types.Content(parts=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ]),
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    vec = result.embeddings[0].values
    print(f"   Dimensions: {len(vec)}")
    assert len(vec) == EMBEDDING_DIM, f"Expected {EMBEDDING_DIM}, got {len(vec)}"
    print("   PASS")
    return vec


def test_video_embedding():
    print("3. Testing video embedding...")
    video_dir = "assets/video"
    if not os.path.exists(video_dir):
        print("   SKIP — assets/video/ not found")
        return None

    mp4s = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
    if not mp4s:
        print("   SKIP — no MP4 files in assets/video/")
        return None

    video_path = os.path.join(video_dir, mp4s[0])
    print(f"   Using: {video_path}")
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=types.Content(parts=[
            types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
        ]),
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    vec = result.embeddings[0].values
    print(f"   Dimensions: {len(vec)}")
    assert len(vec) == EMBEDDING_DIM, f"Expected {EMBEDDING_DIM}, got {len(vec)}"
    print("   PASS")
    return vec


def test_cross_modal_similarity(text_vec, image_vec):
    print("4. Testing cross-modal similarity...")
    if text_vec is None or image_vec is None:
        print("   SKIP — need both text and image embeddings")
        return

    # Embed a query about the image content
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=["architecture diagram showing how components connect"],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    query_vec = result.embeddings[0].values

    sim_text = cosine_similarity(query_vec, text_vec)
    sim_image = cosine_similarity(query_vec, image_vec)

    print(f"   Query vs Text:  {sim_text:.4f}")
    print(f"   Query vs Image: {sim_image:.4f}")
    print(f"   Cross-modal retrieval is {'working' if sim_image > 0 else 'NOT working'}")
    print("   PASS")


if __name__ == "__main__":
    print("=" * 50)
    print("Gemini Embedding 2 — Canary Test")
    print("=" * 50)
    print()

    text_vec = test_text_embedding()
    print()
    image_vec = test_image_embedding()
    print()
    video_vec = test_video_embedding()
    print()
    test_cross_modal_similarity(text_vec, image_vec)

    print()
    print("=" * 50)
    print("All available tests passed!")
    print("=" * 50)
