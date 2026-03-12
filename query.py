"""Query engine: embed question → similarity search → Gemini LLM answer."""

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
    """Run a RAG query: embed → search Supabase → generate answer.

    Returns (answer_text, list_of_matches).
    """
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
        label += f" — similarity: {m['similarity']:.3f}"
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
        print(f"  [{s['source_type']}] {s['source_file']} — {s['similarity']:.3f}")
