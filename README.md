# Twitter ETL Pipeline

Async ETL pipeline that processes Twitter data through an LLM and stores results in Supabase.

## Features

- ✅ **Async processing** with rate limiting using `asyncio.Semaphore`
- ✅ **Batch processing**: 20 items per LLM call
- ✅ **Concurrent requests**: Configurable rate limit (default: 5 concurrent)
- ✅ **Automatic retries**: 3 attempts with exponential backoff
- ✅ **Bulk database inserts**: Up to 1000 records per batch
- ✅ **Error handling**: Tracks failures without stopping the pipeline
- ✅ **Modular architecture**: Clean separation of concerns

## Project Structure

```
SundAI - ETL Twitter/
├── config.py           # Configuration & constants
├── llm_client.py       # LLM API logic (OpenRouter)
├── db_client.py        # Database logic (Supabase)
├── main.py             # Main orchestration
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in repo)
└── README.md          # This file
```

## Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure environment variables**:
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
```

Required variables:
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/service key
- `SUPABASE_TABLE`: Table name (default: `processed_data`)

3. **Update the prompt**:
Edit the `PROMPT_TEMPLATE` in `config.py` with your actual prompt.

## Usage

### Option 1: Import and use in your code

```python
import asyncio
from main import run_pipeline

# Your Twitter data
input_data = [
    {
        "text": "Example tweet text",
        "username": "user123",
        "name": "John Doe",
        "location": "New York, NY"
    },
    # ... more items
]

# Run the pipeline
asyncio.run(run_pipeline(input_data))
```

### Option 2: Run the example directly

```bash
python main.py
```

## Configuration

Edit these constants in `config.py`:

```python
LLM_BATCH_SIZE = 20              # Items per LLM request
DB_BATCH_SIZE = 1000             # Records per DB insert
MAX_CONCURRENT_REQUESTS = 5      # Rate limit (concurrent API calls)
MAX_RETRIES = 3                  # Retry attempts for failed requests
```

## Module Documentation

### `config.py`
- Contains all configuration constants and environment variables
- Validates required environment variables with `validate_config()`

### `llm_client.py`
- Handles all OpenRouter API communication
- Implements async batch processing with Semaphore rate limiting
- Includes retry logic with exponential backoff

### `db_client.py`
- Manages Supabase database operations
- Performs bulk inserts in batches of up to 1000 records

### `main.py`
- Main orchestration - coordinates the entire pipeline
- Clean entry point for running the ETL process

## Pipeline Flow

```
Input Data (List of Dicts)
    ↓
Split into batches of 20
    ↓
Process concurrently with LLM (rate-limited to 5 concurrent)
    ↓
Collect all results
    ↓
Split into batches of 1000
    ↓
Save to Supabase
    ↓
Complete ✓
```

## Error Handling

- **LLM failures**: Retried 3 times with exponential backoff
- **Failed batches**: Logged but don't stop the pipeline
- **DB failures**: Logged per batch, pipeline continues

## Example Output

```
============================================================
🚀 Starting ETL Pipeline
============================================================

📊 Processing 100 items in 5 batches of 20
🔒 Rate limit: 5 concurrent requests

✓ Batch 1 processed successfully
✓ Batch 2 processed successfully
✓ Batch 3 processed successfully
✓ Batch 4 processed successfully
✓ Batch 5 processed successfully

✓ Successfully processed: 5/5 batches

💾 Saving 5 results to Supabase...
✓ DB Batch 1: Saved 5 records

💾 Database Summary:
  ✓ Saved: 5 records

============================================================
✅ ETL Pipeline Complete
============================================================
```

