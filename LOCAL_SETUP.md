# Running the model locally

SightMate needs a vision model to actually see the screen. This guide covers getting one
running on your own machine (free, private, offline) and, if you'd rather, pointing it at a
hosted model instead.

Anything that speaks the OpenAI chat API works here. The easiest by far is Ollama.

## Ollama (the easy path)

1. Install it from https://ollama.com/download.

2. Pull a vision model:

   ```
   ollama pull qwen3-vl:8b
   ```

   `qwen3-vl:8b` is what the app defaults to and it's good at reading screens, but it's on
   the heavier side — you'll want a GPU (or a fair bit of RAM) for it to feel responsive. If
   that's too much for your machine, `qwen3-vl:2b`, `minicpm-v`, or `moondream` are lighter
   and faster (moondream is tiny but rougher). Whatever you pull, just make sure
   `OPENAI_MODEL` in your `.env` matches it.

3. Ollama starts its own server at `http://localhost:11434` — that's already where the app
   looks, so there's nothing to configure.

4. Install the app's dependencies and run it:

   ```
   cd Seno
   pip install -r requirements.txt
   python run.py
   ```

5. Open http://localhost:5000. Check http://localhost:5000/api/health if you want to confirm
   it picked up your local model.

The `.env` here already ships set to `local` with the Ollama defaults, so once Ollama and
the model are ready it should just work.

## Using something other than Ollama

Open `.env` and change the three `OPENAI_*` lines. Some common setups:

| Provider | OPENAI_BASE_URL | OPENAI_MODEL |
| --- | --- | --- |
| Ollama (local) | `http://localhost:11434/v1` | `qwen3-vl:8b` |
| LM Studio (local) | `http://localhost:1234/v1` | whatever model you loaded |
| vLLM (local, GPU) | `http://localhost:8000/v1` | the served model id |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| OpenRouter | `https://openrouter.ai/api/v1` | e.g. `qwen/qwen-2.5-vl-7b-instruct` |

For the hosted ones, put your real key in `OPENAI_API_KEY`. (For Ollama the key is ignored,
so the placeholder is fine.)

## Things worth knowing

- Screen reading, live Q&A, and monitoring all run on whatever model you point it at.
- PDFs can't be handed to a local model as a file. Open the PDF in the browser and share the
  screen instead — it reads it like a normal page and you scroll through it.
- Speed comes down to your hardware. With a GPU it's quick. On CPU only, expect to wait for
  each answer — the bigger the model, the longer the wait.
