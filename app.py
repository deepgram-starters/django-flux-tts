"""
Django Flux TTS Starter - Application Entry Point

Launches the Daphne ASGI server for Django Channels.

Routes:
  GET  /api/session   - Issue JWT session token
  GET  /api/metadata  - Project metadata from deepgram.toml
  WS   /api/tts       - Streaming TTS bridge to Deepgram Flux (auth required)
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("DEEPGRAM_API_KEY"):
    print("\n" + "=" * 70)
    print("ERROR: Deepgram API key not found!")
    print("=" * 70)
    print("\nCreate a .env file with:\n   DEEPGRAM_API_KEY=your_api_key_here")
    print("\nGet your API key at: https://console.deepgram.com")
    print("=" * 70 + "\n")
    sys.exit(1)

port = int(os.environ.get("PORT", 8081))
host = os.environ.get("HOST", "0.0.0.0")

print("\n" + "=" * 70)
print("Django Flux TTS Server (Backend API)")
print("=" * 70)
print(f"Server:   http://{host}:{port}")
print("")
print("GET  /api/session")
print("WS   /api/tts (auth required)")
print("GET  /api/metadata")
print("=" * 70 + "\n")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from daphne.cli import CommandLineInterface

CommandLineInterface().run(["-b", host, "-p", str(port), "config.asgi:application"])
