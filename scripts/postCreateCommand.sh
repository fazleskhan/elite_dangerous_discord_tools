#!/bin/bash
# [README:SCRIPTS]
# ### `postCreateCommand.sh`
#
# Prepares a development container or workstation by refreshing the Yarn apt key,
# updating system packages, installing `austin`, and installing both runtime and
# development Python dependencies for the project.
#
# Usage:
# - `bash scripts/postCreateCommand.sh`
#
# Arguments:
# - This script takes no positional command-line arguments.
#
# Environment variables:
# - This script does not currently read any custom environment variables.
# [/README]
#
# [README:STARTING]
# When loading Python dependencies for a development environment, install both:
#
# `pip install -r requirements.txt`
#
# `pip install -r dev-requirements.txt`
#
# To enable repository spell checking with `cspell`, run:
#
# `npm run spellcheck`
# [/README]

echo "Executing ./scripts/postCreateCommand.sh"

# apt update is not working because the pub key has expired
curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/yarn.gpg >/dev/null

echo "deb [signed-by=/usr/share/keyrings/yarn.gpg] https://dl.yarnpkg.com/debian stable main" | sudo tee /etc/apt/sources.list.d/yarn.list

sudo apt update

sudo apt upgrade -y

sudo apt install austin -y

# production/runtime requirements
pip install -r requirements.txt

# development environments must load both runtime and development requirements
pip install -r dev-requirements.txt
