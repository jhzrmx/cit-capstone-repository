# CIT Capstone Repository

A web-based capstone storage repository for CIT, written in Python with FastAPI<br>
This also utilize smart searching with Sentence Transformer using model `all-MiniLM-L6-v2`

## How to use?

1. Clone this repository
2. Go to the working directory:
   ```
   cd cit-capstone-repository
   ```
3. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
4. **Download Local LLM Model**:
   ```bash
   python download_model.py granite   # 241 MB
   # OR
   python download_model.py qwen      # 424 MB
   ```
   
5. Configure environment variables in `config_local.py`:
   ```python
   OPENAI_API_KEY = "your-api-key-here"
   LLM_PROVIDER = "local" # or "openai"
   LOCAL_MODEL_NAME = "qwen"
   RAG_ENABLE_SUMMARY = "true"
   RAG_TOP_K = 5
   RAG_CACHE_TTL = 3600
   ```
   
6. Run seed data:
   ```
   python seed.py
   ```
7. Run the FastAPI Uvicorn server:
   ```
   uvicorn main:app --reload
   ```
