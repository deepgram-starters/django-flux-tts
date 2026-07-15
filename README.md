# Django Flux Text-to-Speech

Get started using Deepgram's **Flux streaming text-to-speech** (v2 speak) with this Django (Channels) demo app.

Unlike the Flux **transcription** starter ([`django-flux`](https://github.com/deepgram-starters/django-flux)), which is a raw `websockets` proxy in its Channels consumer, this starter uses the official [`deepgram-sdk`](https://github.com/deepgram/deepgram-python-sdk) async `AsyncDeepgramClient` + `speak.v2` API.

## How it works

```
Browser  ──(JSON: Speak/Flush/Close)──▶  Django Channels consumer  ──(SDK speak.v2)──▶  Deepgram Flux TTS
Browser  ◀──(binary audio + JSON control)──  Django Channels consumer  ◀──(SDK speak.v2)──  Deepgram Flux TTS
```

- The API key stays server-side; the browser authenticates with a short-lived JWT (`/api/session`) on the `access_token.<jwt>` WebSocket subprotocol.
- `TtsConsumer` (an `AsyncWebsocketConsumer`) opens the SDK connection on `connect`, forwards Deepgram audio (`bytes`) to the browser as binary and control messages as JSON via a background task, and dispatches browser `Speak`/`Flush`/`Close` in `receive`.

### Client → backend message protocol

Send JSON text frames on the `/api/tts` WebSocket:

```jsonc
{ "type": "Speak", "text": "Hello from Flux." }
{ "type": "Flush" }
{ "type": "Close" }
```

## Prerequisites

- Python 3.10+
- A Deepgram API key ([console.deepgram.com](https://console.deepgram.com/))


## Local Development

```bash
make init
cp sample.env .env   # add your DEEPGRAM_API_KEY
make start           # backend (Daphne) on http://localhost:8081
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DEEPGRAM_API_KEY` | — | **Required.** Your Deepgram API key. |
| `PORT` | `8081` | Backend port. |
| `HOST` | `0.0.0.0` | Backend host. |
| `DEEPGRAM_TTS_MODEL` | `flux-alexis-en` | Flux voice (`flux-{voice}-{language}`). |
| `SESSION_SECRET` | random per boot | Set in production for stable JWT signing. |
| `DJANGO_SECRET_KEY` | dev default | Set in production. |

`model`, `encoding`, and `sample_rate` may also be passed as query params on `/api/tts`.

## License

MIT - See [LICENSE](./LICENSE)
