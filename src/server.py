from __future__ import annotations

import json
import queue
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


_current_computation = None


class Reactive:
    def __init__(self, value=None, formula=None):
        self._formula = formula
        self._value = value
        self._dependencies: set[Reactive] = set()
        self._dependents: set[Reactive] = set()
        self._listeners: set[Callable[[object], None]] = set()
        if self._formula is not None:
            self.recompute()

    @property
    def value(self):
        global _current_computation
        if _current_computation is not None:
            self._dependents.add(_current_computation)
            _current_computation._dependencies.add(self)
        return self._value

    @value.setter
    def value(self, new_val):
        if self._formula is not None:
            raise Exception("Cannot assign to a computed Reactive value.")
        if new_val != self._value:
            self._value = new_val
            self._notify()
            for dep in self._dependents.copy():
                dep.recompute()

    def recompute(self):
        if self._formula is None:
            return
        for dep in self._dependencies:
            dep._dependents.discard(self)
        self._dependencies.clear()
        global _current_computation
        old = _current_computation
        _current_computation = self
        new_val = self._formula()
        _current_computation = old
        if new_val != self._value:
            self._value = new_val
            self._notify()
            for dep in self._dependents.copy():
                dep.recompute()

    def watch(self, listener: Callable[[object], None]) -> Callable[[], None]:
        self._listeners.add(listener)

        def unwatch() -> None:
            self._listeners.discard(listener)

        return unwatch

    def _notify(self):
        for listener in list(self._listeners):
            listener(self._value)


def html_template(template, **reactives):
    return Reactive(formula=lambda: template.format(**{k: v.value for k, v in reactives.items()}))


def html_list(reactive_str, separator=","):
    return Reactive(
        formula=lambda: "".join(f"<li>{item.strip()}</li>" for item in reactive_str.value.split(separator) if item.strip())
    )


title = Reactive("My Page")
body_text = Reactive("Welcome to my reactive HTML!")
items_str = Reactive("Apple, Banana, Cherry")

items_html = html_list(items_str)
page = html_template(
    """
<h1>{title}</h1>
<p>{body_text}</p>
<ul>{items_html}</ul>
""",
    title=title,
    body_text=body_text,
    items_html=items_html,
)

subscriber_lock = threading.Lock()
subscribers: set[queue.Queue[str]] = set()


def serialize_state() -> dict[str, str]:
    return {
        "title": title.value,
        "body_text": body_text.value,
        "items_str": items_str.value,
        "page_html": page.value,
    }


def sse_message(data: dict[str, str], event: str | None = None) -> str:
    payload = json.dumps(data)
    if event:
        return f"event: {event}\ndata: {payload}\n\n"
    return f"data: {payload}\n\n"


def broadcast_state() -> None:
    msg = sse_message(serialize_state(), event="state")
    with subscriber_lock:
        dead = []
        for sub in subscribers:
            try:
                sub.put_nowait(msg)
            except Exception:
                dead.append(sub)
        for sub in dead:
            subscribers.discard(sub)


page.watch(lambda _: broadcast_state())


INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Reactive Python Toy (SSE)</title>
    <style>
      body {
        margin: 0;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        background: linear-gradient(120deg, #f6efe3, #e9f4ff);
        color: #16202a;
      }
      main {
        max-width: 880px;
        margin: 2rem auto;
        padding: 1rem;
        display: grid;
        gap: 1rem;
      }
      .panel {
        border: 1px solid #b8c8d8;
        border-radius: 12px;
        padding: 1rem;
        background: #ffffffcc;
      }
      label {
        display: block;
        font-weight: 600;
        margin-bottom: 0.4rem;
      }
      input {
        width: 100%;
        padding: 0.6rem;
        margin-bottom: 0.8rem;
        border-radius: 8px;
        border: 1px solid #95aac0;
      }
      button {
        padding: 0.65rem 0.9rem;
        border: 0;
        border-radius: 8px;
        background: #1e5ca3;
        color: white;
        cursor: pointer;
      }
      #status {
        font-size: 0.9rem;
        color: #325b80;
      }
    </style>
  </head>
  <body>
    <main>
      <section class="panel">
        <h2>Reactive state editor</h2>
        <form id="editor">
          <label for="title">Title</label>
          <input id="title" name="title" />
          <label for="body_text">Body Text</label>
          <input id="body_text" name="body_text" />
          <label for="items_str">Items (comma separated)</label>
          <input id="items_str" name="items_str" />
          <button type="submit">Push update</button>
        </form>
        <div id="status">Connecting...</div>
      </section>
      <section class="panel">
        <h2>Rendered template (server generated)</h2>
        <div id="rendered"></div>
      </section>
    </main>
    <script>
      const statusEl = document.getElementById("status");
      const renderedEl = document.getElementById("rendered");
      const form = document.getElementById("editor");
      const titleEl = document.getElementById("title");
      const bodyEl = document.getElementById("body_text");
      const itemsEl = document.getElementById("items_str");

      function applyState(state) {
        titleEl.value = state.title;
        bodyEl.value = state.body_text;
        itemsEl.value = state.items_str;
        renderedEl.innerHTML = state.page_html;
      }

      async function submitState() {
        const payload = {
          title: titleEl.value,
          body_text: bodyEl.value,
          items_str: itemsEl.value
        };
        await fetch("/update", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
      }

      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        await submitState();
      });

      const es = new EventSource("/events");
      es.addEventListener("state", (event) => {
        applyState(JSON.parse(event.data));
        statusEl.textContent = "Live updates connected";
      });
      es.onerror = () => {
        statusEl.textContent = "Disconnected from stream, retrying...";
      };
    </script>
  </body>
</html>
"""


class ReactiveHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/":
            body = INDEX_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/state":
            body = json.dumps(serialize_state()).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/events":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            sub = queue.Queue()
            with subscriber_lock:
                subscribers.add(sub)

            try:
                self.wfile.write(sse_message(serialize_state(), event="state").encode("utf-8"))
                self.wfile.flush()
                while True:
                    try:
                        msg = sub.get(timeout=15.0)
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        continue
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with subscriber_lock:
                    subscribers.discard(sub)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.path != "/update":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON payload.")
            return

        for key, target in (("title", title), ("body_text", body_text), ("items_str", items_str)):
            val = payload.get(key)
            if isinstance(val, str):
                target.value = val

        body = b'{"ok": true}'
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), ReactiveHandler)
    print(f"Listening on http://{host}:{port}")
    print("Open / in a browser and use the form to update reactive state.")
    server.serve_forever()


if __name__ == "__main__":
    run()
