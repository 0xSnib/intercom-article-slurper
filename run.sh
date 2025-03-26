#!/bin/bash
# Script to build and run the Intercom Article Slurper Docker container

# Build the Docker image
echo "Building Docker image..."
docker build -t intercom-slurper .

# Create output directory if it doesn't exist and set permissions
echo "Setting up output directory..."
mkdir -p /Users/jamesevans/intercom_articles
chmod 777 /Users/jamesevans/intercom_articles

# Run the container
echo "Running container to download Intercom articles..."
docker run --rm \
  -v /Users/jamesevans/intercom_articles:/app/output \
  --env-file .env \
  intercom-slurper

echo "Done! Articles downloaded to /Users/jamesevans/intercom_articles" 