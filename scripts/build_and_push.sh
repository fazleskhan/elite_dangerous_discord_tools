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
# - `bash scripts/build_and_push.sh -e dev`
# - `bash scripts/build_and_push.sh docker_env test`
# - `DOCKER_ENV=dev bash scripts/build_and_push.sh`
# - `DOCKER_ENV=test bash scripts/build_and_push.sh`
# - `DOCKER_ENV=prod bash scripts/build_and_push.sh`
#
# Arguments:
# - `docker_env <value>`: Optional command-line override for the deployment
#   environment. Supported values are `dev`, `test`, and `prod`.
# - `-e <value>`: Short form of the same deployment-environment override.
#
# Environment variables:
# - `DOCKER_ENV`: Selects the image tag to build and push. Supported values are
#   `dev`, `test`, and `prod`. The command-line override wins when both are
#   provided. If neither is set, the script defaults to `dev`.
# [/README]

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

# Define variables
IMAGE_NAME="public-images"
DOCKER_ENV="${DOCKER_ENV:-dev}"

while (($# > 0)); do
  case "$1" in
    -e)
      if (($# < 2)); then
        echo "Error: -e requires one of: dev, test, prod." >&2
        exit 1
      fi
      DOCKER_ENV="$2"
      shift 2
      ;;
    docker_env)
      if (($# < 2)); then
        echo "Error: docker_env requires one of: dev, test, prod." >&2
        exit 1
      fi
      DOCKER_ENV="$2"
      shift 2
      ;;
    *)
      echo "Error: unsupported argument '$1'. Use -e <dev|test|prod> or docker_env <dev|test|prod>." >&2
      exit 1
      ;;
  esac
done

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
