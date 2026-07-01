import os
import re
import json
import requests
import logging
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

from app.core.prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from app.utils.llm_utils import initialize_llm_provider, extract_json_from_response

logger = logging.getLogger(__name__)

def extract_username(url: str, network: str) -> Optional[str]:
    if not url:
        return None
    
    url = url.strip()
    
    if network.lower() in ["dev community", "dev"]:
        match = re.search(r"dev\.to/([^/]+)", url)
        if match:
            return match.group(1)
            
    elif network.lower() == "medium":
        match = re.search(r"medium\.com/@([^/]+)", url)
        if match:
            return match.group(1)
        match = re.search(r"([^/]+)\.medium\.com", url)
        if match:
            return match.group(1)
            
    return None

def fetch_dev_to_articles(username: str) -> List[Dict]:
    try:
        url = f"https://dev.to/api/articles?username={username}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            articles = response.json()
            posts = []
            for article in articles[:10]:
                posts.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "description": article.get("description", ""),
                    "published_at": article.get("published_at", ""),
                    "tags": article.get("tag_list", [])
                })
            return posts
        else:
            logger.warning(f"Failed to fetch DEV.to articles for {username}: {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching DEV.to articles: {e}")
    return []

def fetch_medium_articles(username: str) -> List[Dict]:
    try:
        url = f"https://medium.com/feed/@{username}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            posts = []
            root = ET.fromstring(response.content)
            channel = root.find("channel")
            if channel is not None:
                for item in channel.findall("item")[:10]:
                    title = item.find("title")
                    link = item.find("link")
                    categories = [cat.text for cat in item.findall("category") if cat.text]
                    
                    posts.append({
                        "title": title.text if title is not None else "",
                        "url": link.text if link is not None else "",
                        "description": "Medium article",
                        "tags": categories
                    })
            return posts
        else:
            logger.warning(f"Failed to fetch Medium articles for {username}: {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching Medium articles: {e}")
    return []

def summarize_blog_posts(posts: List[Dict]) -> Dict:
    if not posts:
        return {}

    try:
        print(f"🤖 Using LLM to summarize {len(posts)} blog posts...")
        provider = initialize_llm_provider(DEFAULT_MODEL)
        model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL, {"temperature": 0.1, "top_p": 0.9})
        
        posts_json = json.dumps(posts, indent=2)
        
        system_prompt = """You are an expert technical recruiter analyzing a candidate's blog posts.
Review the provided list of blog posts and output a JSON object evaluating them.
Your JSON must match this structure exactly:
{
    "total_blogs": int,
    "blog_score": float,
    "blog_details": "A professional summary of their writing topics and technical depth",
    "blogs": [
        {
            "url": "url string",
            "score": float,
            "details": "Why this post is technically interesting or valuable"
        }
    ]
}

Return ONLY valid JSON.
"""

        chat_params = {
            "model": DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please evaluate these blog posts:\n{posts_json}"}
            ],
            "options": model_params,
        }

        response = provider.chat(**chat_params, format={"type": "json_object"})
        response_text = response["message"]["content"]
        
        response_text = extract_json_from_response(response_text)
        blog_data = json.loads(response_text)
        
        return blog_data
        
    except Exception as e:
        logger.error(f"Error summarizing blog posts: {e}")
        
    return {
        "total_blogs": len(posts),
        "blog_score": 5.0,
        "blog_details": f"Candidate has written {len(posts)} blog posts.",
        "blogs": [{"url": p.get("url", ""), "score": 5.0, "details": p.get("title", "")} for p in posts[:5]]
    }

def fetch_and_summarize_blog(blog_url: str, network: str) -> Dict:
    username = extract_username(blog_url, network)
    if not username:
        logger.warning(f"Could not extract username from {network} url: {blog_url}")
        return {}
        
    posts = []
    if network.lower() in ["dev community", "dev"]:
        posts = fetch_dev_to_articles(username)
    elif network.lower() == "medium":
        posts = fetch_medium_articles(username)
        
    if not posts:
        return {}
        
    blog_data = summarize_blog_posts(posts)
    return blog_data
