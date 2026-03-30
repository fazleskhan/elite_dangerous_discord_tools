#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

# Define variables
IMAGE_NAME="public-images"
TAG="elite-dangerous-discord-tools" # Use the first argument as the tag, or default to 'latest'
#TAG="elite-dangerous-discord-tools-test"
#TAG="elite-dangerous-discord-tools-dev"

REGISTRY_USER="fazleskhan" # Replace with your registry username or full registry path (e.g., ghcr.io/user)
FULL_IMAGE_NAME="${REGISTRY_USER}/${IMAGE_NAME}"

echo "--- Building Docker image: ${FULL_IMAGE_NAME}:${TAG} ---"
# Build the Docker image, tagging it with the full name and tag simultaneously
docker build -t "${FULL_IMAGE_NAME}:${TAG}" .

echo "--- Tagging image as latest ---"
# Optionally, tag the image with 'latest' as well
docker tag "${FULL_IMAGE_NAME}:${TAG}" "${FULL_IMAGE_NAME}:latest"

echo "--- Pushing images to registry ---"
# Push the specific version tag
docker push "${FULL_IMAGE_NAME}:${TAG}"

# Push the 'latest' tag
docker push "${FULL_IMAGE_NAME}:latest"

echo "--- Successfully built, tagged, and pushed images ---"
