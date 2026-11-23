#!/usr/bin/env bash
# PROTOTYPE (throwaway) for "Which database do we use?" (issue #8).
# Installs scratch PostgreSQL (via the pgserver wheel, which bundles PG binaries), the Python drivers,
# and the official MongoDB 8.0 tarball, all inside PROTOTYPE-wipe-me/. Nothing system-wide; no sudo.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p PROTOTYPE-wipe-me/bin
python3 -m venv PROTOTYPE-wipe-me/venv
PROTOTYPE-wipe-me/venv/bin/pip install -q pgserver 'psycopg[binary]' pymongo
cd PROTOTYPE-wipe-me/bin
curl -sSL -o mongo.tgz https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2404-8.0.4.tgz
tar xzf mongo.tgz && rm mongo.tgz
./mongodb-linux-x86_64-ubuntu2404-8.0.4/bin/mongod --version | head -1
echo "setup done"
