# reactive-python-toy

Archive repo for a Python reactivity experiment.

## What this was trying to do

This project is a small toy implementation of a reactive computation model in Python:

- `Reactive` values track dependencies automatically.
- Computed values recompute when upstream state changes.
- `main2.py` extends the toy into reactive HTML string generation (`html_template`, `html_list`).

The intent was to test reactivity mechanics in plain Python before wiring any real browser/runtime integration.

Important archival note: `src/main.py` and `src/main2.py` demonstrate server-side/in-process reactivity only.

This repo now also includes `src/server.py`, which adds a minimal browser integration using Server-Sent Events (SSE). It is still a toy, but it closes the transport gap by pushing template updates to connected clients.

## When this was written

Based on local filesystem metadata from the original workspace:

- `main.py` created at **2025-02-18 23:44:15 -0600**, last modified at **2025-02-18 23:44:17 -0600**
- `main2.py` created at **2025-02-18 23:53:44 -0600**, last modified at **2025-02-18 23:53:45 -0600**

(US Central time)

## Archive contents

- `src/main.py`: initial reactive core and arithmetic usage demo
- `src/main2.py`: refined core plus reactive HTML template/list demo
- `src/server.py`: reactive core + tiny HTTP server + SSE stream to push updates to the browser

## Run the browser demo

```bash
python3 src/server.py
```

Then open:

- `http://127.0.0.1:8000/`

How it works:

- Browser submits state changes to `POST /update`
- Server mutates base `Reactive` values
- Computed `page` reactive recomputes
- Server broadcasts new rendered HTML/state over `GET /events` (SSE)
- Browser applies updates without refresh
