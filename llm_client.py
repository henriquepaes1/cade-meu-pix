"""
LLM client for processing data through OpenRouter API.
"""
import asyncio
import aiohttp
import json
from typing import List, Dict, Any

from config import (
    LLM_BATCH_SIZE,
    MAX_CONCURRENT_REQUESTS,
    MAX_RETRIES,
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
    OPENROUTER_MODEL,
    PROMPT_TEMPLATE,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
)


async def process_batch_with_llm(
    session: aiohttp.ClientSession,
    batch: List[Dict[str, str]],
    semaphore: asyncio.Semaphore,
    batch_index: int
) -> Dict[str, Any]:
    """
    Process a batch of items through the LLM with rate limiting.
    
    Args:
        session: Aiohttp client session
        batch: List of data items to process
        semaphore: Semaphore for rate limiting
        batch_index: Index of the current batch
        
    Returns:
        Dictionary with processing results
    """
    async with semaphore:  # Rate limiting
        # Format data for the prompt (global index and text)
        global_offset = batch_index * LLM_BATCH_SIZE
        formatted_data = "\n".join([
            f"<{global_offset + i}>{item['text']}</{global_offset + i}>" 
            for i, item in enumerate(batch)
        ])
        
        prompt = PROMPT_TEMPLATE.replace("DATA_PLACEHOLDER", formatted_data)
        
        # Prepare API payload
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Add delay to avoid rate limiting
        await asyncio.sleep(REQUEST_DELAY)
        
        try:
            async with session.post(
                OPENROUTER_API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                # Extract and parse LLM response
                llm_response = result["choices"][0]["message"]["content"]
                
                # Strip markdown code blocks if present
                cleaned_response = llm_response.strip()
                if cleaned_response.startswith("```"):
                    lines = cleaned_response.split('\n')
                    lines = lines[1:]  # Remove first line (```json or ```)
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]  # Remove last line (```)
                    cleaned_response = '\n'.join(lines).strip()
                
                try:
                    fraud_scores = json.loads(cleaned_response)
                    
                    return {
                        "success": True,
                        "batch_index": batch_index,
                        "fraud_scores": fraud_scores
                    }
                except json.JSONDecodeError as e:
                    # If JSON parsing fails, show the cleaned response for debugging
                    print(f"JSON parse error for batch {batch_index + 1}:")
                    print(f"Cleaned response: {cleaned_response[:200]}...")
                    raise e
                
        except Exception as e:
            print(f"✗ Batch {batch_index + 1} failed: {str(e)}")
            return {
                "success": False,
                "batch_index": batch_index,
                "error": str(e)
            }


async def process_all_batches(data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Process all data through LLM in batches with concurrent rate-limited requests.
    
    Args:
        data: List of data items to process
        
    Returns:
        List of successful processing results
    """
    # Split data into batches
    batches = [data[i:i + LLM_BATCH_SIZE] for i in range(0, len(data), LLM_BATCH_SIZE)]
    
    print(f"\n📊 Processing {len(data)} items in {len(batches)} batches of {LLM_BATCH_SIZE}")
    print(f"🔒 Rate limit: {MAX_CONCURRENT_REQUESTS} concurrent requests\n")
    
    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # Process all batches concurrently (but rate-limited)
    async with aiohttp.ClientSession() as session:
        tasks = [
            process_batch_with_llm(session, batch, semaphore, idx)
            for idx, batch in enumerate(batches)
        ]
        results = await asyncio.gather(*tasks)
    
    # Filter successful results
    successful_results = [r for r in results if r and r["success"]]
    failed_results = [r for r in results if r and not r["success"]]
    
    print(f"\n✓ Successfully processed: {len(successful_results)}/{len(batches)} batches")
    if failed_results:
        print(f"✗ Failed batches: {len(failed_results)}")
    
    return successful_results

