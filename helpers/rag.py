import asyncio
import hashlib
import re
from typing import List, Optional
from cachetools import TTLCache

from config import RAGConfig, PathConfig
from dtos import ReferenceItem, AISummary, AbstractWithMetadata

rag_cache = TTLCache(
    maxsize=int(RAGConfig.RAG_CACHE_TTL),
    ttl=int(RAGConfig.RAG_CACHE_TTL)
)

_local_llm = None
_active_queries = set()

def get_local_llm():
    global _local_llm
    if _local_llm is None:
        from llama_cpp import Llama
        
        model_name = RAGConfig.LOCAL_MODEL_NAME.lower()
        if model_name == "granite":
            model_path = str(PathConfig.BASE_DIR / "models" / "local_llm" / "granite-4.0-h-350m-Q5_K_M.gguf")
        elif model_name == "qwen":
            model_path = str(PathConfig.BASE_DIR / "models" / "local_llm" / "Qwen3-0.6B-Q5_K_M.gguf")
        else:
            model_path = str(RAGConfig.LOCAL_MODEL_PATH)
        
        _local_llm = Llama(
            model_path=model_path,
            n_ctx=RAGConfig.LOCAL_MODEL_N_CTX,
            n_threads=RAGConfig.LOCAL_MODEL_N_THREADS,
            verbose=False
        )
    return _local_llm


async def call_local_llm(prompt: str) -> str:
    try:
        llm = get_local_llm()
        
        llm.reset()
        
        model_name = RAGConfig.LOCAL_MODEL_NAME.lower()
        
        if model_name == "granite":
            full_prompt = f"""Question: {prompt}

Answer:"""
            stop_tokens = ["Question:", "\n\n\n"]
        
        elif model_name == "qwen":
            full_prompt = f"""<|im_start|>system
You are a helpful research assistant.<|im_end|>
<|im_start|>user
{prompt} /no_think<|im_end|>
<|im_start|>assistant
"""
            stop_tokens = ["<|im_end|>"]
        
        else:
            full_prompt = f"""Question: {prompt}

Answer:"""
            stop_tokens = ["Question:", "\n\n\n"]
        
        estimated_tokens = len(full_prompt) / 4
        max_context = RAGConfig.LOCAL_MODEL_N_CTX
        
        if estimated_tokens > max_context - 500:
            raise Exception(f"Prompt too long: ~{int(estimated_tokens)} tokens (max: {max_context - 500})")
        
        response = await asyncio.to_thread(
            llm,
            full_prompt,
            max_tokens=500,
            temperature=0.7,
            stop=stop_tokens,
            echo=False
        )
        
        summary_text = response["choices"][0]["text"].strip()
        return summary_text
        
    except Exception as e:
        raise Exception(f"Failed to generate summary with local model: {str(e)}")


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


async def call_llm(prompt: str) -> str:
    if RAGConfig.LLM_PROVIDER == "local":
        return await call_local_llm(prompt)
    elif RAGConfig.LLM_PROVIDER == "openai":
        return await call_openai_llm(prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {RAGConfig.LLM_PROVIDER}")


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
    max_abstract_chars = 400
    
    for idx, abstract in enumerate(abstracts, start=1):
        abstract_text = abstract.abstract
        if len(abstract_text) > max_abstract_chars:
            abstract_text = abstract_text[:max_abstract_chars] + "..."
        
        references_text += f"[{idx}] {abstract.title}\n"
        references_text += f"    Authors: {abstract.authors}\n"
        references_text += f"    Year: {abstract.year}\n"
        references_text += f"    Abstract: {abstract_text}\n\n"
    
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
    response_text = await call_llm(prompt)
    summary = parse_llm_response(response_text, abstracts)
    return summary


async def generate_and_cache_summary(
    abstracts: List[AbstractWithMetadata],
    query_text: str,
    cache_key: str
) -> None:
    global _active_queries
    
    if cache_key in _active_queries:
        return
    
    _active_queries.add(cache_key)
    
    try:
        summary = await generate_rag_summary(abstracts, query_text)
        rag_cache[cache_key] = summary
    except Exception as e:
        import traceback
        traceback.print_exc()
        pass
    finally:
        _active_queries.discard(cache_key)


def get_cached_summary(cache_key: str) -> Optional[AISummary]:
    summary = rag_cache.get(cache_key)
    return summary


def is_query_in_progress(cache_key: str) -> bool:
    return cache_key in _active_queries

