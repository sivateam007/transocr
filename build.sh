#!/usr/bin/env bash
set -e

# Install pycryptodome first (builds fine on Python 3.14)
pip install pycryptodome

# Install mega.py without its broken pycrypto dependency
# We set MEGA_USE_CRYPTO_DOME so mega.py uses pycryptodome instead
MEGA_USE_CRYPTO_DOME=1 pip install --no-deps mega.py

# Install remaining dependencies
pip install -r requirements.txt
