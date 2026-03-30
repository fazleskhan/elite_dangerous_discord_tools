#!/bin/bash
# [README:SCRIPTS]
# ### `build_and_push.sh`
#
# Builds the Docker image for this repository, tags it for the selected deployment
# environment, tags the same image as `latest`, and pushes both tags to the configured
# registry namespace.
#
# Usage:
# - `bash scripts/build_and_push.sh`
# - `DOCKER_ENV=dev bash scripts/build_and_push.sh`
# - `DOCKER_ENV=test bash scripts/build_and_push.sh`
# - `DOCKER_ENV=prod bash scripts/build_and_push.sh`
#
# Arguments:
# - This script takes no positional command-line arguments.
#
# Environment variables:
# - `DOCKER_ENV`: Selects the image tag to build and push. Supported values are
#   `dev`, `test`, and `prod`. If unset, the script defaults to `dev`.
# [/README]

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

# Define variables
IMAGE_NAME="public-images"
DOCKER_ENV="${DOCKER_ENV:-dev}"

case "${DOCKER_ENV}" in
  prod)
    TAG="elite-dangerous-discord-tools"
    ;;
  dev)
    TAG="elite-dangerous-discord-tools-dev"
    ;;
  test)
    TAG="elite-dangerous-discord-tools-test"
    ;;
  *)
    echo "Error: DOCKER_ENV must be one of: dev, test, prod. Got: ${DOCKER_ENV}" >&2
    exit 1
    ;;
esac

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
