import os
import json
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

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

if __name__ == "__main__":
    main()
