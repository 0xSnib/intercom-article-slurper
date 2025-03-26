#!/bin/bash
# Script to build and run the Intercom Article Slurper Docker container

# Build the Docker image
echo "Building Docker image..."
docker build -t intercom-slurper .

# Run the container
echo "Running container to download Intercom articles..."
docker run --rm -v /Users/jamesevans/intercom_articles:/app/output --env-file .env intercom-slurper

echo "Done! Articles downloaded to /Users/jamesevans/intercom_articles" 