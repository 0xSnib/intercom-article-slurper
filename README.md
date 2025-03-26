# Intercom Article Slurper

A containerized tool to download all Intercom Help articles in Markdown format with their images. Perfect for importing into Notion or other documentation platforms.

## Features

- Downloads all Intercom Help articles via their API
- Converts HTML content to Markdown format
- Downloads and includes all images
- Organizes content by collections and sections
- Containerized solution - no need to install dependencies on your local machine

## Prerequisites

- Docker installed on your machine
- Intercom API token with access to your Help Center

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/intercom-article-slurper.git
   cd intercom-article-slurper
   ```

2. Create a `.env` file with your Intercom API token:
   ```bash
   cp .env.example .env
   ```
   Then edit the `.env` file to add your Intercom API token.

## Usage

### Build and run with Docker

```bash
# Build the Docker image
docker build -t intercom-slurper .

# Run the container with your API token
docker run --rm -v /Users/jamesevans/intercom_articles:/app/output --env-file .env intercom-slurper
```

### What happens

1. The tool will fetch all collections, sections, and articles from your Intercom Help Center
2. It will convert each article to Markdown format
3. Images will be downloaded and stored in the `output/images` directory
4. Articles will be stored in the `output/articles` directory, organized by collection and section
5. A metadata file (`output/articles_metadata.json`) will be created with information about all downloaded articles

## Output Structure

```
output/
├── articles/
│   ├── Collection_Name_1/
│   │   ├── Section_Name_1/
│   │   │   ├── Article_Title_1.md
│   │   │   ├── Article_Title_2.md
│   │   │   └── ...
│   │   └── Section_Name_2/
│   │       └── ...
│   └── Collection_Name_2/
│       └── ...
├── images/
│   ├── image1.jpg
│   ├── image2.png
│   └── ...
└── articles_metadata.json
```

## Importing to Notion

After running the tool, you'll have a complete set of Markdown files with images that can be imported into Notion:

1. In Notion, click "Import" in the sidebar
2. Select "Markdown & CSV"
3. Choose the files or directories from the `output/articles` directory
4. Images referenced in the Markdown files will be automatically imported

## License

MIT 