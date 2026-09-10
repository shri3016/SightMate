# SightMate

SightMate is a screen assistant for people who can't see the screen well (or at all). You
share your screen, and then you just talk to it. Ask "what's on this page?", "how much is
this?", "where do I click to buy?" and it answers out loud, like a sighted friend sitting
next to you describing things.

The whole thing runs on your own machine. No cloud, no API keys, no bill at the end of the
month, and nothing about your screen ever leaves your computer. The "brain" is a local
vision model served by [Ollama](https://ollama.com) — `qwen3-vl:8b` by default.

## Why I built this

Almost the entire internet was built for people who can look at it. Every price tag, every
"click the button on the right", every red error message quietly assumes you can see the
screen. If you can't, you end up asking someone else for help with small, ordinary things
that should be yours to do on your own.

For someone who is blind or has low vision, that adds up. Not being able to check a price
without handing your phone to a stranger, or fill in a form without someone reading it back
to you, chips away at something bigger than convenience. It's independence, and a bit of
dignity along with it.

Screen readers help, but they read text out one piece at a time, and they can't really tell
you what a page *means*. I wanted something you could just talk to. Something that looks at
the whole screen the way a friend leaning over your shoulder would, and simply tells you
what's going on. If it gives even one person a little more freedom to do things by
themselves, it was worth building.

## Demo

I recorded a short walkthrough so you can see it working rather than just read about it, please click below to watch the demo:

<a href="https://drive.google.com/file/d/17Wybg-dlf-yA1k0D8xiC9aRHjWGcUV1v/view?usp=sharing" target="_blank">
  <img width="800" alt="SightMate UI Demo" src="https://github.com/user-attachments/assets/61751252-590b-46b7-9932-5424f64003b2" />
</a>

## What it can do

- Look at a screen and tell you what it is and what matters on it, before you have to go
  digging for details.
- Answer follow-up questions about whatever's on screen right now. It grabs a fresh view
  each time, so if you've scrolled, it just sees the new stuff — you don't have to re-explain.
- Listen and talk back hands-free through the browser. If it starts saying something you
  don't need, say "stop" and it stops.
- Keep an eye on the screen if you ask it to ("watch my screen") and speak up when something
  worth knowing changes — an item added to the cart, a form that went through, the page
  moving somewhere new.
- Turn a confusing error message into plain English instead of reading the technical version
  at you.

## Getting it running

You need two things going: Ollama (the model) and the app itself.

**1. Install Ollama and pull the model.**

Grab Ollama from https://ollama.com/download, install it, then in a terminal:

```
ollama pull qwen3-vl:8b
```

`qwen3-vl:8b` reads screens well but it's a real model — it wants a decent GPU to feel
snappy. If your machine is lighter, there are smaller options in
[LOCAL_SETUP.md](LOCAL_SETUP.md).

**2. Install and start the app.**

```
cd Seno
python -m venv .venv
. .venv/Scripts/activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Then open http://localhost:5000 in Chrome, press Enter to pick a screen or window to
share, and start talking.

If you check http://localhost:5000/api/health — you should see `"backend": "local"` and `"model": "qwen3-vl:8b"`.

## Talking to it

You mostly just ask questions in plain language. A few things it listens for specifically:

| You say / press | What happens |
| --- | --- |
| any question | It looks at the current screen and answers |
| "watch my screen" / "stop watching" | Turns monitoring on or off |
| "stop" | Cuts off whatever it's saying right now |
| "repeat" | Says the last answer again |
| Enter | Share the screen, or switch to a different one |
| Esc / R / M | Stop / repeat / toggle monitoring |

## About PDFs

The qwen model can look at images and PDFs.
Eg: open the PDF in your browser and share the screen. SightMate then reads it like any other page, and you scroll through it a page at a time.

## How it's put together

A Flask backend and a JavaScript front end.

The front end (in `frontend/`) does the parts that have to happen in the browser: capturing
the shared screen, taking a screenshot when you ask something, listening to the mic, and
speaking answers back with the Web Speech API.

The backend (in `backend/`) is the wiring. It takes the screenshot and question, hands them
to the model, and sends the answer back. The interesting bit is that the model sits behind
a set of swappable "provider" seams (vision, reasoning, change-detection, documents). Which
one gets used is decided in a single place — `_build_providers()` in `backend/app.py` —
based on one line in your `.env`. That's why you can run it against local Ollama or a hosted
OpenAI-compatible model without touching anything else.

Conversations are remembered in a small SQLite file so follow-up questions have context.
Only the short text summary is stored — the raw screenshots are never written to disk.

```
Seno/
├── backend/
│   ├── app.py            # wires everything together, picks the model backend
│   ├── config.py         # reads settings from .env
│   ├── routes/           # the web page + the /api endpoints
│   ├── services/         # the model providers (+ stubs used for tests) and session memory
│   ├── schemas/          # the shape of a "screen understanding"
│   ├── db/               # SQLite storage
│   └── prompts/          # the instructions given to the model
├── frontend/             # index.html + the capture / voice / app JS + styles
├── tests/
├── requirements.txt
└── run.py
```

## Using a different model

Everything talks the OpenAI chat format, so you're not locked to Ollama. Point the three
`OPENAI_*` lines in `.env` at LM Studio, vLLM, or a hosted provider (OpenAI, Gemini,
OpenRouter) and it'll use that instead. The models and URLs are laid out in
[LOCAL_SETUP.md](LOCAL_SETUP.md).

## Tests

```
pip install -r requirements.txt
pytest
```

The tests run against stub providers, so they don't need Ollama or any network — they just
check that the analyze → ask → converse → monitor flow behaves.

## License

MIT License - See [LICENSE](LICENSE) for details.

