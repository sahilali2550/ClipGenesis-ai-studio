import xml.etree.ElementTree as ET
import requests
from loguru import logger
from typing import List

def get_google_trends(geo: str = "US") -> List[str]:
    """
    Fetch trending search terms from Google Trends RSS feed.
    Does not require any API keys.
    """
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        logger.info(f"Fetching Google Trends for geo={geo}")
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch Google Trends, status: {response.status_code}")
            return []
        
        # Parse XML
        root = ET.fromstring(response.content)
        trends = []
        for item in root.findall(".//item"):
            title = item.find("title")
            if title is not None and title.text:
                trends.append(title.text.strip())
        return trends
    except Exception as e:
        logger.error(f"Error fetching Google Trends: {str(e)}")
        return []

def get_reddit_trends(subreddit: str = "Showerthoughts") -> List[str]:
    """
    Fetch hot post titles from a given subreddit using Atom RSS feed (bypasses JSON blocks).
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot.rss"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        logger.info(f"Fetching Reddit hot posts from r/{subreddit} RSS")
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch Reddit RSS, status: {response.status_code}")
            return []
        
        # Parse XML (Reddit uses Atom feed namespaces)
        root = ET.fromstring(response.content)
        
        # Atom namespace: {http://www.w3.org/2005/Atom}
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        posts = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            if title is not None and title.text:
                posts.append(title.text.strip())
        return posts
    except Exception as e:
        logger.error(f"Error fetching Reddit RSS trends: {str(e)}")
        return []

if __name__ == "__main__":
    print("Testing Google Trends:")
    print(get_google_trends()[:5])
    print("\nTesting Reddit r/Showerthoughts:")
    print(get_reddit_trends()[:5])
