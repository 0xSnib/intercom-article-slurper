#!/usr/bin/env python3
"""
Intercom Article Slurper

A tool to download all Intercom Help articles in Markdown format with images
for easy importing into Notion or other platforms.
"""

import os
import json
import re
import time
import requests
import base64
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Config
API_TOKEN = os.getenv("INTERCOM_API_TOKEN")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
ARTICLES_DIR = os.path.join(OUTPUT_DIR, "articles")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
RATE_LIMIT_DELAY = 1  # seconds between API calls to avoid rate limiting

if not API_TOKEN:
    print("Error: INTERCOM_API_TOKEN environment variable is required.")
    print("Create a .env file with your Intercom API token or set it when running Docker.")
    exit(1)

# Create output directories
Path(ARTICLES_DIR).mkdir(parents=True, exist_ok=True)
Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)

# API endpoints
INTERCOM_API_URL = "https://api.intercom.io"
HELP_COLLECTIONS_ENDPOINT = f"{INTERCOM_API_URL}/help_center/collections"
HELP_SECTIONS_ENDPOINT = f"{INTERCOM_API_URL}/help_center/sections"
HELP_ARTICLES_ENDPOINT = f"{INTERCOM_API_URL}/articles"

# Headers for API requests
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def sanitize_filename(name):
    """Convert a string to a safe filename."""
    return re.sub(r'[^\w\-\.]', '_', name)

def download_image(image_url, image_name=None):
    """Download an image and return its local path."""
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code != 200:
            print(f"Failed to download image: {image_url}")
            return None
        
        if not image_name:
            # Extract image name from URL
            parsed_url = urlparse(image_url)
            image_name = os.path.basename(parsed_url.path)
            # If no extension or questionable extension, use a default
            if not os.path.splitext(image_name)[1] or len(os.path.splitext(image_name)[1]) > 5:
                image_name = f"{base64.urlsafe_b64encode(image_url.encode()).decode()[:10]}.jpg"

        image_name = sanitize_filename(image_name)
        image_path = os.path.join(IMAGES_DIR, image_name)
        
        with open(image_path, 'wb') as f:
            f.write(response.content)
        
        return image_path
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
        return None

def convert_html_to_markdown(html_content):
    """
    Convert HTML content to Markdown, downloading and replacing image URLs.
    Returns the markdown content and a list of downloaded image paths.
    """
    downloaded_images = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Process images
    for img in soup.find_all('img'):
        if img.get('src'):
            image_url = img['src']
            local_path = download_image(image_url)
            if local_path:
                img['src'] = os.path.basename(local_path)
                downloaded_images.append(local_path)
    
    # Convert to markdown (simplified approach)
    # In a real-world scenario, you might want to use a dedicated HTML-to-Markdown converter
    markdown_content = str(soup)
    
    # Basic HTML to Markdown conversions
    markdown_content = re.sub(r'<h1>(.*?)</h1>', r'# \1', markdown_content)
    markdown_content = re.sub(r'<h2>(.*?)</h2>', r'## \1', markdown_content)
    markdown_content = re.sub(r'<h3>(.*?)</h3>', r'### \1', markdown_content)
    markdown_content = re.sub(r'<h4>(.*?)</h4>', r'#### \1', markdown_content)
    markdown_content = re.sub(r'<h5>(.*?)</h5>', r'##### \1', markdown_content)
    markdown_content = re.sub(r'<h6>(.*?)</h6>', r'###### \1', markdown_content)
    markdown_content = re.sub(r'<p>(.*?)</p>', r'\1\n\n', markdown_content)
    markdown_content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', markdown_content)
    markdown_content = re.sub(r'<em>(.*?)</em>', r'*\1*', markdown_content)
    markdown_content = re.sub(r'<a href="(.*?)">(.*?)</a>', r'[\2](\1)', markdown_content)
    markdown_content = re.sub(r'<img src="(.*?)".*?>', r'![](\1)', markdown_content)
    markdown_content = re.sub(r'<ul>(.*?)</ul>', lambda m: m.group(1), markdown_content, flags=re.DOTALL)
    markdown_content = re.sub(r'<ol>(.*?)</ol>', lambda m: m.group(1), markdown_content, flags=re.DOTALL)
    markdown_content = re.sub(r'<li>(.*?)</li>', r'- \1\n', markdown_content)
    markdown_content = re.sub(r'<code>(.*?)</code>', r'`\1`', markdown_content)
    markdown_content = re.sub(r'<pre>(.*?)</pre>', r'```\n\1\n```', markdown_content, flags=re.DOTALL)
    
    # Clean up any remaining HTML tags
    markdown_content = re.sub(r'<.*?>', '', markdown_content)
    
    return markdown_content, downloaded_images

def fetch_all_collections():
    """Fetch all help center collections."""
    try:
        response = requests.get(HELP_COLLECTIONS_ENDPOINT, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        print(f"Error fetching collections: {e}")
        return []

def fetch_sections_by_collection(collection_id):
    """Fetch all sections for a given collection."""
    try:
        params = {'collection_id': collection_id}
        response = requests.get(HELP_SECTIONS_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        print(f"Error fetching sections for collection {collection_id}: {e}")
        return []

def fetch_articles_by_section(section_id):
    """Fetch all articles for a given section."""
    try:
        url = f"{HELP_SECTIONS_ENDPOINT}/{section_id}/articles"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        print(f"Error fetching articles for section {section_id}: {e}")
        return []

def fetch_article_content(article_id):
    """Fetch the full content of an article."""
    try:
        url = f"{HELP_ARTICLES_ENDPOINT}/{article_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching article {article_id}: {e}")
        return None

def save_article_as_markdown(article, collection_name, section_name):
    """Save an article as a Markdown file."""
    try:
        article_id = article.get('id')
        article_title = article.get('title', 'Untitled Article')
        article_data = fetch_article_content(article_id)
        
        if not article_data:
            print(f"Skipping article {article_id}: No content found")
            return None
        
        html_content = article_data.get('body', '')
        markdown_content, downloaded_images = convert_html_to_markdown(html_content)
        
        # Create collection and section directories
        collection_dir = sanitize_filename(collection_name)
        section_dir = sanitize_filename(section_name)
        article_dir = os.path.join(ARTICLES_DIR, collection_dir, section_dir)
        Path(article_dir).mkdir(parents=True, exist_ok=True)
        
        # Create a safe filename for the article
        safe_title = sanitize_filename(article_title)
        article_path = os.path.join(article_dir, f"{safe_title}.md")
        
        # Add frontmatter with metadata
        frontmatter = f"""---
title: "{article_title}"
collection: "{collection_name}"
section: "{section_name}"
intercom_id: "{article_id}"
---

"""
        
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter + markdown_content)
        
        return {
            'path': article_path,
            'title': article_title,
            'images': downloaded_images
        }
    except Exception as e:
        print(f"Error saving article {article.get('id')}: {e}")
        return None

def main():
    print("Starting Intercom Article Slurper...")
    articles_metadata = []
    
    # Fetch all collections
    collections = fetch_all_collections()
    print(f"Found {len(collections)} collections")
    
    for collection in collections:
        collection_id = collection.get('id')
        collection_name = collection.get('name', 'Unnamed Collection')
        print(f"Processing collection: {collection_name}")
        
        # Fetch sections for this collection
        sections = fetch_sections_by_collection(collection_id)
        print(f"Found {len(sections)} sections in collection '{collection_name}'")
        
        for section in sections:
            section_id = section.get('id')
            section_name = section.get('name', 'Unnamed Section')
            print(f"Processing section: {section_name}")
            
            # Fetch articles for this section
            articles = fetch_articles_by_section(section_id)
            print(f"Found {len(articles)} articles in section '{section_name}'")
            
            # Process each article
            for article in tqdm(articles, desc=f"Processing articles in {section_name}"):
                # Rate limit to avoid API throttling
                time.sleep(RATE_LIMIT_DELAY)
                
                result = save_article_as_markdown(article, collection_name, section_name)
                if result:
                    articles_metadata.append(result)
    
    # Save metadata for all articles
    metadata_path = os.path.join(OUTPUT_DIR, 'articles_metadata.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(articles_metadata, f, indent=2)
    
    print(f"Completed! Downloaded {len(articles_metadata)} articles with their images.")
    print(f"Articles and images saved to '{OUTPUT_DIR}' directory.")

if __name__ == "__main__":
    main() 