"""
Main ETL Pipeline: Process Twitter data through LLM and save to Supabase.
"""
import asyncio
import json
import os
from typing import List, Dict, Any

from config import validate_config, FRAUD_PROBABILITY_THRESHOLD
from llm_client import process_all_batches
from db_client import save_to_txt


def load_posts_from_txt(file_path: str) -> List[Dict[str, str]]:
    """
    Load posts from a JSON file containing an array of post objects.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of dictionaries with post data
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        posts = json.load(f)
    
    print(f"📂 Loaded {len(posts)} posts from {file_path}")
    return posts


def filter_by_fraud_probability(
    llm_results: List[Dict[str, Any]], 
    input_data: List[Dict[str, str]],
    threshold: float = FRAUD_PROBABILITY_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Filter input data by fraud probability threshold.
    
    Args:
        llm_results: Results from LLM processing (already parsed)
        input_data: Original input data array
        threshold: Minimum probability to consider as fraud (0.0 - 1.0)
        
    Returns:
        List of filtered data with fraud scores above threshold
    """
    # Collect all fraud scores from all batches
    all_fraud_scores = {}
    
    for result in llm_results:
        # Fraud scores are already parsed in llm_client
        all_fraud_scores.update(result['fraud_scores'])
    
    # Filter indices above threshold
    high_fraud_indices = [
        int(idx) 
        for idx, prob in all_fraud_scores.items() 
        if float(prob) >= threshold
    ]
    
    # Build filtered dataset with fraud scores
    filtered_data = []
    for idx in high_fraud_indices:
        if idx < len(input_data):
            fraud_case = input_data[idx].copy()
            fraud_case['fraud_probability'] = all_fraud_scores[str(idx)]
            filtered_data.append(fraud_case)
    
    print(f"\n🎯 Processing Summary:")
    print(f"  Total analyzed: {len(input_data)} items")
    print(f"  High-confidence cases (≥{threshold}): {len(filtered_data)} items")
    
    return filtered_data


async def run_pipeline(input_data: List[Dict[str, str]]) -> None:
    """
    Main orchestration function for the ETL pipeline.
    
    Args:
        input_data: List of Twitter data dictionaries with keys:
                   - text: Tweet text
                   - username: Twitter username
                   - name: Display name
                   - location: User location
    """
    print("\n" + "=" * 60)
    print("🚀 Starting ETL Pipeline")
    print("=" * 60)
    
    # Validate configuration
    validate_config()
    
    # Step 1: Process through LLM (fraud detection)
    results = await process_all_batches(input_data)
    
    # Step 2: Filter by fraud probability threshold
    filtered_data = filter_by_fraud_probability(results, input_data)
    
    # Step 3: Save high-probability fraud cases to text file
    if filtered_data:
        save_to_txt(filtered_data)
    else:
        print("\n⚠ No fraud cases above threshold to save")
    
    print("\n" + "=" * 60)
    print("✅ ETL Pipeline Complete")
    print("=" * 60)


if __name__ == "__main__":
    # Load input data from txt file
    input_file = os.path.join("input", "posts_data.txt")
    
    try:
        input_data = load_posts_from_txt(input_file)
        
        # Run the async pipeline
        asyncio.run(run_pipeline(input_data))
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("Please create the input file with one post per line.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
