"""Load test for the read-hot public surface (Locust).

Not run in CI — this is the tool for producing the number that actually matters
in a senior conversation: p95 latency at a target RPS. The read path is what
takes traffic (list / search / detail), so that's what we hammer.

Run against a locally running stack:

    pip install -r backend/loadtest/requirements.txt
    locust -f backend/loadtest/locustfile.py --host http://localhost:8000

then open http://localhost:8089, set users + spawn rate, and read p50/p95/p99
off the Statistics tab. Headless, CI-style example (records a CSV):

    locust -f backend/loadtest/locustfile.py --host http://localhost:8000 \
        --headless -u 50 -r 10 -t 1m --csv=loadtest/out

WHAT TO LOOK FOR (the senior read, not just "it was fast"):
- p95 on /stories/ (offset) vs the keyset cursor path as you push deeper pages —
  offset should degrade with depth, keyset should stay flat. That contrast is
  the whole point of the keyset work (TECH_TARGETS #3).
- search p95 under load — proves the GIN index is doing the work, not a scan.
"""
from locust import HttpUser, between, task

API = "/api/v1"


class ReaderUser(HttpUser):
    # Model a browsing reader: a short think-time between actions.
    wait_time = between(0.5, 2.0)

    def on_start(self):
        # Grab a first page so detail/keyset tasks have real ids to hit.
        self._story_ids = []
        self._next_cursor = None
        resp = self.client.get(f"{API}/stories/?limit=10", name="/stories/ [first page]")
        if resp.ok:
            data = resp.json()
            self._story_ids = [s["id"] for s in data.get("items", [])]

    @task(5)
    def list_offset(self):
        self.client.get(f"{API}/stories/?limit=10&offset=0", name="/stories/ [offset]")

    @task(4)
    def list_keyset(self):
        # Keyset first page also returns next_cursor; follow it to exercise the
        # O(1)-per-page seek path that offset pagination can't match at depth.
        resp = self.client.get(f"{API}/stories/?limit=10&cursor=", name="/stories/ [keyset]")
        if resp.ok:
            cursor = resp.json().get("next_cursor")
            if cursor:
                self.client.get(
                    f"{API}/stories/?limit=10&cursor={cursor}",
                    name="/stories/ [keyset page 2]",
                )

    @task(3)
    def search(self):
        self.client.get(f"{API}/stories/search?q=story&limit=10", name="/stories/search")

    @task(2)
    def detail(self):
        if self._story_ids:
            sid = self._story_ids[0]
            self.client.get(f"{API}/stories/{sid}", name="/stories/{id}")
