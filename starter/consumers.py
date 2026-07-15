"""WebSocket consumer for Flux TTS — bridges the browser to Deepgram speak.v2 via the SDK."""
import os
import json
import asyncio

import jwt
from channels.generic.websocket import AsyncWebsocketConsumer
from dotenv import load_dotenv

from deepgram import AsyncDeepgramClient
from deepgram.environment import DeepgramClientEnvironment
from deepgram.speak.v2.types import SpeakV2Speak
from starter.views import SESSION_SECRET

load_dotenv()
API_KEY = os.environ.get("DEEPGRAM_API_KEY")
if not API_KEY:
    raise ValueError("DEEPGRAM_API_KEY required")

DEFAULT_MODEL = os.environ.get("DEEPGRAM_TTS_MODEL", "flux-alexis-en")
DEFAULT_ENCODING = "linear16"
DEFAULT_SAMPLE_RATE = "24000"

# One async SDK client, reused across connections; the browser never sees the API key.
# DEEPGRAM_BASE_URL (e.g. wss://api.staging.deepgram.com) overrides the default
# production endpoint. speak.v2 uses environment.production for the /v2/speak ws.
def _build_client():
    base_url = os.environ.get("DEEPGRAM_BASE_URL")
    if base_url:
        https = base_url.replace("wss://", "https://").replace("ws://", "http://")
        env = DeepgramClientEnvironment(
            base=https, production=base_url, agent=base_url, agent_rest=https
        )
        print(f"Using custom Deepgram base URL: {base_url}")
        return AsyncDeepgramClient(api_key=API_KEY, environment=env)
    return AsyncDeepgramClient(api_key=API_KEY)


deepgram = _build_client()


class TtsConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = None
        self._connection_cm = None
        self.forward_task = None

    async def connect(self):
        # Validate JWT from the access_token.<jwt> subprotocol
        valid_proto = None
        for proto in self.scope.get("subprotocols", []):
            if proto.startswith("access_token."):
                token = proto[len("access_token."):]
                try:
                    jwt.decode(token, SESSION_SECRET, algorithms=["HS256"])
                    valid_proto = proto
                except Exception:
                    pass
                break

        if not valid_proto:
            await self.close(code=4401)
            return

        await self.accept(subprotocol=valid_proto)
        print("Client connected to /api/tts")

        from urllib.parse import parse_qs

        params = parse_qs(self.scope.get("query_string", b"").decode("utf-8"))
        model = params.get("model", [DEFAULT_MODEL])[0]
        encoding = params.get("encoding", [DEFAULT_ENCODING])[0]
        sample_rate = params.get("sample_rate", [DEFAULT_SAMPLE_RATE])[0]
        print(f"TTS config - model={model}, encoding={encoding}, sample_rate={sample_rate}")

        try:
            # `connect()` is an async context manager; enter it manually so the
            # connection lives across the consumer's connect/disconnect lifecycle.
            self._connection_cm = deepgram.speak.v2.connect(
                model=model, encoding=encoding, sample_rate=sample_rate
            )
            self.connection = await self._connection_cm.__aenter__()
            self.forward_task = asyncio.create_task(self.forward_from_deepgram())
        except Exception as e:
            print(f"Error connecting to Deepgram: {e}")
            await self.send(text_data=json.dumps({
                "type": "Error", "description": str(e), "code": "CONNECTION_FAILED",
            }))
            await self.close(code=3000)

    async def disconnect(self, close_code):
        print(f"Client disconnected: {close_code}")
        if self.forward_task:
            self.forward_task.cancel()
            try:
                await self.forward_task
            except asyncio.CancelledError:
                pass
        if self._connection_cm:
            try:
                await self._connection_cm.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing Deepgram connection: {e}")

    async def receive(self, text_data=None, bytes_data=None):
        """Forward browser control messages (JSON) to Deepgram."""
        if not self.connection or not text_data:
            return
        try:
            data = json.loads(text_data)
        except (ValueError, TypeError):
            print("Ignoring non-JSON message from client")
            return

        msg_type = data.get("type")
        try:
            if msg_type == "Speak":
                await self.connection.send_speak(SpeakV2Speak(text=data.get("text", "")))
            elif msg_type == "Flush":
                await self.connection.send_flush()
            elif msg_type == "Close":
                await self.connection.send_close()
            else:
                print(f"Ignoring unknown client message type: {msg_type}")
        except Exception as e:
            print(f"Error forwarding to Deepgram: {e}")

    async def forward_from_deepgram(self):
        """Forward Deepgram messages to the browser: bytes as binary, models as JSON."""
        try:
            async for message in self.connection:
                if isinstance(message, (bytes, bytearray)):
                    await self.send(bytes_data=bytes(message))
                elif hasattr(message, "model_dump_json"):
                    await self.send(text_data=message.model_dump_json())
                else:
                    await self.send(text_data=json.dumps(
                        {"type": getattr(message, "type", "Unknown")}
                    ))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error forwarding from Deepgram: {e}")
        finally:
            try:
                await self.close(code=1000)
            except Exception:
                pass
