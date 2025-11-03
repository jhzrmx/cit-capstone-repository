import requests
from config import OllamaConfig

def summarize_with_ollama(query: str, passages: list[dict]) -> str:
    blocks = [f"[{i}] {p['title']} ({p.get('year') or 'n.d.'}) :: {p['content'][:1200]}" for i,p in enumerate(passages,1)]
    prompt = f"""You are an academic assistant. Synthesize a concise overview.

QUERY: {query}

Use ONLY these snippets. Cite with [1], [2], etc. End with a bullet list "Sources used" with titles and years.

Sources:
{chr(10).join(blocks)}"""

    r = requests.post(f"{OllamaConfig.URL}/api/generate",
                      json={"model": OllamaConfig.MODEL, "prompt": prompt, "stream": False},
                      timeout=120)
    r.raise_for_status()
    return r.json().get("response","").strip()

