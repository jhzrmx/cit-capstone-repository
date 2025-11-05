from typing import List
from openai import OpenAI
import requests
from config import OllamaConfig, OpenAiConfig

def summarize_with_ollama(query: str, passages: List[dict]) -> str:
    blocks = [f"[{i}] {p['title']} ({p.get('year') or 'n.d.'}) :: {p['content'][:1200]}" for i,p in enumerate(passages,1)]
    prompt = f"""You are an assistant for a Capstone Project Portal. A user types a search query and you are given the most relevant capstone abstracts retrieved from a vector database.

TASK
Write a concise academic summary that directly addresses the user’s query using ONLY the provided capstones. Cite evidence inline using the bracket index of each source (e.g., [1], [2]). When synthesizing multiple sources in a sentence, include multiple citations (e.g., [1][3]).

INPUT
User Query: "{query}"

Capstone Sources (the index [N] matches each source below):
{chr(10).join(blocks)}

OUTPUT
Return a SINGLE HTML FRAGMENT (no Markdown, no code fences, no <html> or <body> tags) with EXACTLY the structure below:

<section class="ai-panel">
  <div class="ai-panel__title">AI Summary</div>
  <div class="ai-panel__content">
    <!-- Write 1–2 short paragraphs (4–8 total sentences). -->
    <!-- Every factual claim must have at least one inline citation. -->
    <!-- Inline citations MUST be clickable anchors exactly like: <a href="#ref-1">[1]</a> -->
    <p>...</p>
    <p>...</p>
  </div>

  <div class="ai-panel__refs">
    <div class="ai-panel__refs-title">References:</div>
    <ul class="ai-panel__ref-list">
      <!-- List EVERY provided source in ascending numeric order, even if not cited. -->
      <!-- Each item must have a stable anchor id="ref-N" to support the inline links above. -->
      <!-- Format: Title on the first line (as a link if a URL is provided in the source; otherwise plain text), authors on the next line, then (Year). -->
      <li id="ref-1">
        <span class="ref-title">Title of [1]</span><br/>
        <span class="ref-authors">Authors of [1]</span> (<span class="ref-year">Year of [1]</span>)
      </li>
      <li id="ref-2">...</li>
      <!-- Continue for all N -->
    </ul>
  </div>
</section>

STYLE & RULES
- Keep the summary <= 120 words per paragraph; use 1–2 paragraphs total.
- Tone: neutral, academic, concise; avoid repetition and speculation.
- Use present tense for general capabilities; past tense for completed studies if indicated.
- DO NOT invent titles, authors, years, datasets, or metrics. Use only what is provided.
- If a source is tangential, you may omit it in the prose but MUST still include it in References.
- Inline citations use ONLY the provided indices and MUST be clickable anchors exactly like <a href="#ref-N">[N]</a>.
- Escape any stray HTML from inputs if necessary; do not output raw user content that could break the HTML.
- Output NOTHING except the HTML fragment described above.

VALIDATION (perform silently before returning):
- Each factual claim has >=1 citation.
- Citations are only of the form <a href="#ref-N">[N]</a>.
- All sources appear in the References list in ascending order with id="ref-N"."""

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