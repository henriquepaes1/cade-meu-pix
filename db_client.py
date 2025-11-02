"""
File client for saving processed data to text files.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any


def save_to_txt(fraud_cases: List[Dict[str, Any]]) -> None:
    """
    Save filtered fraud cases to a text file in the results folder.
    
    Args:
        fraud_cases: List of fraud cases with scores above threshold
    """
    if not fraud_cases:
        print("\n⚠ No fraud cases to save")
        return
    
    # Create results folder if it doesn't exist
    os.makedirs("results", exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results/fraud_cases_{timestamp}.json"
    
    print(f"\n💾 Saving {len(fraud_cases)} fraud cases to {filename}...")
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(fraud_cases, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully saved {len(fraud_cases)} fraud cases to {filename}")
        
    except Exception as e:
        print(f"✗ Failed to save fraud cases: {str(e)}")

