from typing import List
from openai import OpenAI
import requests
from config import OllamaConfig, OpenAiConfig

def summarize_with_ollama(query: str, passages: List[dict]) -> str:
    blocks = [f"[{i}] {p['title']} ({p.get('year') or 'n.d.'}) :: {p['content'][:1200]}" for i,p in enumerate(passages,1)]
    prompt = f"""You are an academic assistant. Synthesize a concise overview.

QUERY: {query}

Use ONLY these snippets. Cite with [1], [2], etc. End with a bullet list "Sources used" with titles and years. Return HTML format.

Sources:
{chr(10).join(blocks)}"""

    r = requests.post(f"{OllamaConfig.URL}/api/generate",
                      json={"model": OllamaConfig.MODEL, "prompt": prompt, "stream": False},
                      timeout=120)
    r.raise_for_status()
    return r.json().get("response","").strip()


def summarize_with_openai(query: str, passages: List[dict]) -> str:
    try:
        client = OpenAI(
            api_key=OpenAiConfig.OPENAI_KEY
        )
        context = "\n".join([f"[{i+1}] {p['title']} :: {p['content'][:1200]}" for i,p in enumerate(passages)])
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"You synthesize with [#] citations only from provided snippets."},
                {"role":"user","content": f"Topic: {query}\n\nSources:\n{context}"}
            ]
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        return f"(OpenAI fallback error: {e})"