import os
import json
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
import asyncio
import json
import os
from typing import List, Dict, Any

from config import validate_config, FRAUD_PROBABILITY_THRESHOLD
from llm_client import process_all_batches
from db_client import save_to_txt

load_dotenv()

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "100"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TWITTER_API_URL = "https://api.twitter.com/2/tweets/search/recent"
REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"


def fetch_tweets(query, max_results=100):
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    params = {
        "query": query,
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,lang,text",
        "expansions": "author_id",
        "user.fields": "username,location,name"
    }

    response = requests.get(TWITTER_API_URL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    tweets = []
    users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}

    for tweet in data.get("data", []):
        author_id = tweet.get("author_id")
        user = users.get(author_id, {})

        tweets.append({
            "text": tweet.get("text"),
            "username": user.get("username"),
            "name": user.get("name"),
            "location": user.get("location"),
            "source": "twitter"
        })

    return tweets


def fetch_reddit_posts(query, max_results=100):
    headers = {"User-Agent": "pix-scam-detector/1.0"}
    params = {
        "q": query,
        "limit": min(max_results, 100),
        "sort": "new",
        "restrict_sr": "on"  # Only works if fetching from specific subreddit endpoint
    }

    posts = []
    target_subreddits = ["ConselhosLegais", "golpe"]
    
    for subreddit in target_subreddits:
        # Fetch from each subreddit's search endpoint
        subreddit_url = f"https://www.reddit.com/r/{subreddit}/search.json"
        response = requests.get(subreddit_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            text = post.get("title", "")
            if post.get("selftext"):
                text += f"\n{post.get('selftext')}"

            posts.append({
                "text": text,
                "username": post.get("author"),
                "name": post.get("author"),
                "location": None,
                "source": "reddit"
            })
    
    return posts[:max_results]

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

def save_to_supabase():
    """
    Reads data from filtered_data.txt and saves it to the bot_occurences table in Supabase.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_KEY not set in .env")
        return False

    # Create Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Read data from filtered_data.txt
    try:
        with open("filtered_data.txt", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: filtered_data.txt not found")
        return False
    except json.JSONDecodeError:
        print("Error: filtered_data.txt contains invalid JSON")
        return False

    # Insert data into bot_occurences table
    try:
        response = supabase.table("bot_occurences").insert(data).execute()
        print(f"Successfully inserted {len(data)} record(s) into bot_occurences table")
        return True
    except Exception as e:
        print(f"Error inserting data into Supabase: {e}")
        return False


def main():
    if not TWITTER_BEARER_TOKEN:
        print("Error: TWITTER_BEARER_TOKEN not set")
        return

    print(f"Fetching tweets...")
    query = '"golpe do pix" OR "me roubaram no pix"'
    tweets = fetch_tweets(query, max_results=MAX_RESULTS)
    print(f"Found {len(tweets)} tweets")

    print(f"Fetching Reddit posts...")
    reddit_query = "sofri golpe pix"
    reddit_posts = fetch_reddit_posts(reddit_query, max_results=MAX_RESULTS)
    print(f"Found {len(reddit_posts)} Reddit posts")

    all_posts = tweets + reddit_posts

    output_file = "posts_data.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(all_posts, indent=2, ensure_ascii=False))

    print(f"\nTotal: {len(all_posts)} posts ({len(tweets)} tweets + {len(reddit_posts)} reddit)")

    # Save filtered data to Supabase
    print("\nSaving filtered data to Supabase...")
    save_to_supabase()

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

if __name__ == "__main__":
    main()
