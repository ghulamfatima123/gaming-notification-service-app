# Prompt Log

A running record of the prompts and decisions behind this project, written alongside the work so that `AI_WORKFLOW.md` describes what actually happened.

**Tooling:** Claude Code (Claude Opus 5.5) in the Claude desktop app, working directly in this repository.

---

## Prompt 1: Architecture brief and phased plan

**Human input:** I designed the architecture before writing any code: DDD, Ports & Adapters (Hexagonal), and an event-driven pipeline. Constraints:
- Python 3.10+, FastAPI, Pydantic v2, Pytest.
- In-memory only: no Redis, no Postgres.
- Producers (`GameEngine`, `SocialSystem`) must not know about notifications. They only emit events to an `IEventBus`.
- Strategy pattern for formatting events into notifications. Adapter pattern for delivery channels.
- A fixed target directory layout, built in six phases with a human review after each one.

> "Help me implement this codebase step-by-step. Do not generate the entire project at once. Wait for my confirmation after each phase."

**AI contribution:** Read the challenge PDF first and checked the brief against it. Then produced a Phase 1 plan for review.

**Gaps the AI flagged, approved by me:**
- The PDF requires **Challenge Completed** and **New Follower** events, which my brief left out. Added both.
- `friendRequestAccepted(1, 3)` means player 1 accepted player 3's request, so player 3 is notified. Field names (`accepter_id`, `requester_id`) make the direction explicit.

**Design decisions recorded:**
- Events carry facts only, with no category or recipient. The formatting strategies decide both, which keeps producers fully decoupled.
- Each event has a fixed `event_type`, so `parse_event()` turns raw JSON into the correct typed event.
- All ports are async, so a database or broker adapter could replace the in-memory ones without changing the interfaces.

## Prompt 2: Review of the plan against the brief (before Phase 2)

**Human input:** Asked whether the project should be containerized and whether the AI had read the challenge. Shared the delivery repo. Stressed that the interview evaluates the process and the defence of design decisions, so the design must be correct and neither over- nor under-engineered.

**AI review, all items approved by me:**
- **Containerization:** not required by the brief ("build scripts you provide"). Add one small Dockerfile for reproducibility. No compose file or extra infrastructure.
- **Missing producers:** add `GameEngine` and `SocialSystem` classes that expose the PDF's exact trigger methods and only publish events.
- **Headless demo:** add `demo.py`, which runs the PDF's four example triggers without needing a browser.
- **"Rare or valuable" items:** the formatter skips COMMON items.
- **Extra tests:** a WebSocket end-to-end test, and a test that a failing subscriber is isolated from the others.
- **CI:** a minimal GitHub Actions workflow that runs pytest.
- **Offline players:** notifications are dropped and logged. This is a documented tradeoff; a persistent inbox is listed as an extension point.
- **Git:** one commit per phase. The challenge PDF is kept out of the public repo.

## Prompt 3: "Push Phase 1 and start Phase 2"

**AI contribution:** Initialized git, pushed Phase 1, then implemented the in-memory adapters.

**Design decisions:**
- **Event bus:** subscriptions match with `isinstance`, so subscribing to `BaseEvent` receives every event. `publish` awaits all handlers concurrently with `asyncio.gather(return_exceptions=True)`, so a failing handler is logged and isolated. Delivery is at-most-once and in-process; a real broker is a drop-in adapter.
- **Preference repository:** a plain dict of immutable values. No lock is needed on a single event loop. Unknown players get the defaults.
- **WebSocket channel:** keeps a *set* of sockets per player, so multiple tabs work. The endpoint owns the handshake and the channel only delivers. Dead sockets are removed when a send fails. Offline players' notifications are dropped and logged, as agreed.
- **Message envelope:** `{"type": "notification", "data": {...}}`, so the dashboard can later receive other message types (acks, errors) on the same socket.
- Added `.gitattributes` so line endings stay LF across Windows and Linux (needed for Docker and CI).

**Verification:** an ad-hoc script checked handler isolation, catch-all subscriptions, preference opt-out, delivery to two tabs over a real FastAPI WebSocket (`TestClient`), unregistering on disconnect, and the offline drop path. The dead-socket path (a send that fails) gets a dedicated test in Phase 5.
