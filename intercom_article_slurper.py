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
OUTPUT_DIR = "output"  # This will be mounted to the host's directory
ARTICLES_DIR = os.path.join(OUTPUT_DIR, "articles")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
RATE_LIMIT_DELAY = 1  # seconds between API calls to avoid rate limiting

if not API_TOKEN:
    print("Error: INTERCOM_API_TOKEN environment variable is required.")
    print("Create a .env file with your Intercom API token or set it when running Docker.")
    exit(1)

# Debug paths
print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")
print(f"Articles directory: {os.path.abspath(ARTICLES_DIR)}")
print(f"Images directory: {os.path.abspath(IMAGES_DIR)}")

# Create output directories
try:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print("Successfully created output directories")
    
    # Test write permissions
    test_file = os.path.join(OUTPUT_DIR, '.test')
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    print("Write permissions confirmed")
except Exception as e:
    print(f"Error creating directories: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Directory exists: {os.path.exists(OUTPUT_DIR)}")
    print(f"Directory is writable: {os.access(OUTPUT_DIR, os.W_OK)}")
    exit(1)

# API endpoints
INTERCOM_API_URL = "https://api.intercom.io"
ARTICLES_ENDPOINT = f"{INTERCOM_API_URL}/articles"

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

def fetch_all_articles():
    """Fetch all articles using pagination."""
    all_articles = []
    page = 1
    per_page = 50  # Default is likely 50, adjust if needed
    
    while True:
        try:
            params = {'page': page, 'per_page': per_page}
            response = requests.get(ARTICLES_ENDPOINT, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = data.get('data', [])
            all_articles.extend(articles)
            
            if len(articles) < per_page:
                # No more pages
                break
                
            page += 1
            time.sleep(RATE_LIMIT_DELAY)  # Avoid rate limiting
            
        except Exception as e:
            print(f"Error fetching articles page {page}: {e}")
            break
    
    return all_articles

def fetch_article_content(article_id):
    """Fetch the full content of an article."""
    try:
        url = f"{ARTICLES_ENDPOINT}/{article_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching article {article_id}: {e}")
        return None

def save_article_as_markdown(article):
    """Save an article as a Markdown file."""
    try:
        article_id = article.get('id')
        article_title = article.get('title', 'Untitled Article')
        print(f"\nProcessing article: {article_title} (ID: {article_id})")
        
        # Get full article content
        print(f"  Fetching article content...")
        article_data = fetch_article_content(article_id)
        
        if not article_data:
            print(f"  Skipping article {article_id}: No content found")
            return None
        
        html_content = article_data.get('body', '')
        parent_id = article_data.get('parent_id')
        url = article_data.get('url', '')
        
        # Try to get category information if available
        section_name = article_data.get('section_name', 'Uncategorized')
        collection_name = article_data.get('collection_name', 'General')
        print(f"  Collection: {collection_name}, Section: {section_name}")
        
        # Convert HTML to Markdown
        print(f"  Converting HTML to Markdown...")
        markdown_content, downloaded_images = convert_html_to_markdown(html_content)
        print(f"  Downloaded {len(downloaded_images)} images")
        
        # Create directory structure
        collection_dir = sanitize_filename(collection_name)
        section_dir = sanitize_filename(section_name)
        article_dir = os.path.join(ARTICLES_DIR, collection_dir, section_dir)
        print(f"  Creating directory: {article_dir}")
        
        # Debug directory creation
        try:
            Path(article_dir).mkdir(parents=True, exist_ok=True)
            print(f"  Directory created successfully")
            
            # Test write permissions
            test_file = os.path.join(article_dir, '.test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print(f"  Write permissions confirmed")
        except Exception as e:
            print(f"  Error creating directory or testing permissions: {e}")
            print(f"  Current working directory: {os.getcwd()}")
            print(f"  Directory exists: {os.path.exists(article_dir)}")
            print(f"  Directory is writable: {os.access(article_dir, os.W_OK)}")
            raise
        
        # Create a safe filename for the article
        safe_title = sanitize_filename(article_title)
        article_path = os.path.join(article_dir, f"{safe_title}.md")
        print(f"  Saving article to: {article_path}")
        
        # Add frontmatter with metadata
        frontmatter = f"""---
title: "{article_title}"
collection: "{collection_name}"
section: "{section_name}"
intercom_id: "{article_id}"
url: "{url}"
---

"""
        
        try:
            with open(article_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter + markdown_content)
            print(f"  Successfully saved article")
            
            # Verify file was created
            if os.path.exists(article_path):
                print(f"  File exists and is {os.path.getsize(article_path)} bytes")
            else:
                print(f"  Warning: File was not created at {article_path}")
        except Exception as e:
            print(f"  Error writing file: {e}")
            print(f"  Parent directory exists: {os.path.exists(os.path.dirname(article_path))}")
            print(f"  Parent directory is writable: {os.access(os.path.dirname(article_path), os.W_OK)}")
            raise
        
        return {
            'path': article_path,
            'title': article_title,
            'images': downloaded_images,
            'url': url
        }
    except Exception as e:
        print(f"  Error saving article {article.get('id')}: {e}")
        return None

def main():
    print("Starting Intercom Article Slurper...")
    articles_metadata = []
    
    # Fetch all articles directly
    print("Fetching all articles...")
    articles = fetch_all_articles()
    print(f"Found {len(articles)} articles")
    
    # Process each article
    for article in tqdm(articles, desc="Processing articles"):
        # Rate limit to avoid API throttling
        time.sleep(RATE_LIMIT_DELAY)
        
        result = save_article_as_markdown(article)
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