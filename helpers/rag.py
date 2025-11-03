import asyncio
import hashlib
import re
from typing import List, Optional
from cachetools import TTLCache

from config import RAGConfig
from dtos import ReferenceItem, AISummary, AbstractWithMetadata

rag_cache = TTLCache(
    maxsize=int(RAGConfig.RAG_CACHE_TTL),
    ttl=int(RAGConfig.RAG_CACHE_TTL)
)

async def call_openai_llm(prompt: str) -> str:
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(
        api_key=RAGConfig.OPENAI_API_KEY,
        timeout=float(RAGConfig.OPENAI_TIMEOUT)
    )
    
    try:
        response = await client.chat.completions.create(
            model=RAGConfig.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful research assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        summary_text = response.choices[0].message.content.strip()
        return summary_text
        
    except Exception as e:
        raise Exception(f"Failed to generate summary with OpenAI: {str(e)}")


def get_cache_key(capstone_ids: List[int], query_text: str) -> str:
    sorted_ids = sorted(capstone_ids)
    key_string = f"{sorted_ids}:{query_text.lower().strip()}"
    hash_obj = hashlib.sha256(key_string.encode('utf-8'))
    cache_key = hash_obj.hexdigest()
    return cache_key


def build_rag_prompt(
    abstracts: List[AbstractWithMetadata],
    query_text: str
) -> str:
    references_text = ""
    for idx, abstract in enumerate(abstracts, start=1):
        references_text += f"[{idx}] {abstract.title}\n"
        references_text += f"    Authors: {abstract.authors}\n"
        references_text += f"    Year: {abstract.year}\n"
        references_text += f"    Abstract: {abstract.abstract}\n\n"
    
    prompt = f"""Based on the following research capstone abstracts, provide a comprehensive summary that answers the user's query: "{query_text}"

References:
{references_text}

Instructions:
1. Synthesize information from the provided abstracts to answer the query
2. Use [N] format to cite specific capstones (e.g., [1], [2], [3])
3. Include multiple citations when combining information from different sources
4. Keep the summary concise (2-3 paragraphs maximum)
5. Focus on directly addressing the user's query

Generate a well-structured summary with proper citations:"""
    
    return prompt


def parse_llm_response(
    response_text: str,
    abstracts: List[AbstractWithMetadata]
) -> AISummary:
    citation_pattern = r'\[(\d+)\]'
    citations = re.findall(citation_pattern, response_text)
    
    references = []
    seen_indices = set()
    
    for citation in citations:
        index = int(citation)
        
        if index in seen_indices or index < 1 or index > len(abstracts):
            continue
            
        seen_indices.add(index)
        abstract = abstracts[index - 1]
        
        reference = ReferenceItem(
            index=index,
            capstone_id=abstract.capstone_id,
            title=abstract.title,
            authors=abstract.authors,
            year=abstract.year
        )
        references.append(reference)
    
    references.sort(key=lambda r: r.index)
    
    return AISummary(
        summary_text=response_text,
        references=references
    )


async def generate_rag_summary(
    abstracts: List[AbstractWithMetadata],
    query_text: str
) -> AISummary:
    prompt = build_rag_prompt(abstracts, query_text)
    response_text = await call_openai_llm(prompt)
    summary = parse_llm_response(response_text, abstracts)
    return summary


async def generate_and_cache_summary(
    abstracts: List[AbstractWithMetadata],
    query_text: str,
    cache_key: str
) -> None:
    try:
        summary = await generate_rag_summary(abstracts, query_text)
        rag_cache[cache_key] = summary
    except Exception as e:
        pass


def get_cached_summary(cache_key: str) -> Optional[AISummary]:
    summary = rag_cache.get(cache_key)
    return summary

