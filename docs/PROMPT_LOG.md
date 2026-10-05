# AI Development Workflow & Prompt Log

This document records the prompt history, architectural decisions and engineering iterations behind the Real-Time Notification System. For the narrative view (who decided what, and how AI output was verified), see [`AI_WORKFLOW.md`](../AI_WORKFLOW.md).

## Tooling & Process Overview

* **AI tooling:** Claude Code (Claude Opus 5.5) in the Claude desktop app. It was used for planning, implementation, test generation, browser-based UI testing and git.
* **Workflow:** phase-gated, specification-driven development. Each phase ended with verification and a human review before the next began:
  Domain & Ports → In-Memory Adapters → Router & Strategies → Application & Dashboard → Test Suite & CI → Documentation → Extensions → Verification & Hardening.
* **Core goal:** a decoupled, zero-infrastructure, event-driven notification service. It installs with `pip install -e ".[dev]"`, runs with `uvicorn main:app` (live dashboard) or `python demo.py` (headless), and is covered by 68 tests that CI runs on Python 3.10 and 3.13.
* **Prompt format:** prompts are condensed to their intent. The full opening brief is reproduced in `AI_WORKFLOW.md`.

---

## Engineering Execution & Prompt History

### Phase 0: Requirements Analysis & Architecture Brief

**Prompt:**
> "Act as a Principal Python Engineer. Implement a real-time notification system for a gaming platform using Domain-Driven Design, Ports & Adapters and an event-driven pipeline, step by step, stopping for review after each phase.
> Constraints: Python 3.10+, FastAPI, Pydantic v2, pytest. In-memory infrastructure only: no Redis, no Postgres. Producers (`GameEngine`, `SocialSystem`) must not know about notifications and may only emit events to an `IEventBus`. Strategy pattern for formatting; Adapter pattern for delivery channels."

**AI contributions:**
* Read the challenge PDF *before* planning and compared it with the brief. It found two missing required events (**Challenge Completed** and **New Follower**) and an ambiguous trigger: `friendRequestAccepted(1, 3)` means player 1 accepted, so player **3** is notified.
* Produced a read-only Phase 1 plan for approval before writing any code.

**Follow-up prompt (plan audit):**
> "Before Phase 2, audit the plan against the PDF. Does the service need to be containerized? Flag anything over- or under-engineered; every decision will be defended in a technical interview."

**AI review outcome (approved):**
* Add thin `GameEngine` / `SocialSystem` producers, because the PDF's example usage literally calls them.
* Add a headless `demo.py` so reviewers can verify the system without a browser.
* Notify only for rare or better items, since the spec says "rare or valuable".
* Add CI. Docker is optional (later dropped; see Phase 4).

---

### Phase 1: Domain Model & Ports

**Prompt:**
> "Implement the domain layer and the ports: the notification model and categories, the domain events, the player preferences, and abstract `IEventBus`, `IPreferenceRepository` and `INotificationChannel` interfaces."

**AI contributions & key decisions:**
* **Events carry facts only.** There is no category, recipient or text on an event. The formatting strategy decides all three, so producers stay fully decoupled from notification concerns.
* Immutable (frozen) Pydantic models throughout. `NotificationPreferences.with_category()` returns a new copy instead of mutating.
* **Opt-out preferences:** every category is enabled unless the player turns it off.
* **Async ports** everywhere, so a database or broker adapter can replace the in-memory ones without changing the interfaces.

---

### Phase 2: In-Memory Infrastructure Adapters

**Prompt:**
> "Approved. Commit and push Phase 1, then implement the in-memory adapters: the event bus, the preference repository and the WebSocket channel."

**AI contributions & key decisions:**
* `InMemoryEventBus`: subscriptions match with `isinstance` (subscribing to `BaseEvent` catches everything). Handlers run concurrently with `asyncio.gather(return_exceptions=True)`, so **a failing subscriber is logged and isolated** and never breaks the others.
* `WebSocketChannel`: keeps a set of sockets per player (multi-tab support) and removes dead sockets when a send fails. The HTTP endpoint owns the handshake; the channel only delivers.
* Message envelope `{"type": ..., "data": ...}`, so one socket can carry notifications, acknowledgements and errors.
* `.gitattributes` keeps line endings LF across Windows and Linux.

---

### Phase 3: Notification Router, Strategies & Producers

**Prompt:**
> "Add a README that documents only what exists so far, commit and push, then implement the formatting strategies, the `NotificationRouter`, and the `GameEngine` / `SocialSystem` producers."

**AI contributions & key decisions:**
* **Strategy registry:** one pure function per event type, mapped in `DEFAULT_FORMATTERS`. Each decides the recipient, category and message. Returning `None` means "don't notify" (common items).
* **Router pipeline:** format → check preferences → send. It depends only on ports, and the formatter registry is injectable.
* **Recipient targeting:** preferences are checked against the **recipient**, never the actor. Friend requests notify the target; acceptances notify the original requester; PvP attacks notify the defender only.
* **Domain invariant:** two-player events reject self-targeting (a player can't befriend, follow or attack themselves).
* **Self-correction:** the first version of that validator used underscore attributes, which Pydantic treats as private instance attributes. It was caught in review and replaced with an explicit `ClassVar`.
* Producers import only events and `IEventBus`, verified by grep.

---

### Phase 4: Application Entrypoint & Live Dashboard

**Prompt:**
> "Implement the FastAPI application and the two-player dashboard. Docker is out of scope; the brief only asks for build scripts."

**AI contributions & key decisions:**
* `create_app()` factory, with a composition root in `src/bootstrap.py` shared by the server and `demo.py`. The delivery channel is injected (`WebSocketChannel` for the server, `ConsoleChannel` for the demo), which shows the Adapter pattern in action.
* `/ws/{player_id}` dispatches dashboard actions to the producers. **The acting player comes from the connection, never from the payload**, so clients can't impersonate another player.
* Invalid JSON, unknown actions, missing fields and domain violations return `{"type": "error"}`, and the socket stays open.
* An optional `actor_id` on `Notification` lets clients act on a notification (an inline **Accept** on friend requests).
* Dashboard: Tailwind and vanilla JavaScript. All server text is inserted with `textContent`, so there is no XSS through item names.

**Verification:** the PDF triggers were run headless, the WebSocket protocol was scripted including 8 malformed inputs, and a manual browser run covered attack → defender only, friend request → accept, and the Social opt-out.

---

### Phase 5: Automated Test Suite & CI

**Prompt:**
> "Remove `parse_event`, which is unused now that the endpoint calls the producers. Then build the pytest suite: formatting and delivery, SOCIAL opt-out dropping friend requests but not level-ups, and PvP routed strictly to the defender. Add CI."

**AI contributions & key decisions:**
* Fixtures use the **real** in-memory adapters plus a `RecordingChannel` test double.
* Beyond the three required tests: GAME opt-out, per-player opt-out, recipient-based preference checks, re-enabling a category, and an **extensibility test** where a brand-new `GuildInviteEvent` is delivered by adding only a strategy.
* `test_app.py` drives real WebSocket sessions through `create_app()`.
* **Mutation check:** realistic bugs were planted one at a time (PvP sent to the attacker, preferences ignored, preferences checked for the wrong player, bus failures not isolated, actor read from the payload). The suite caught every one.
* GitHub Actions runs the suite and the demo on Python 3.10 and 3.13.
* **Self-correction:** a test helper entered the WebSocket context manager twice (fixed), and a test that inspected private bus internals was removed in favour of behavioural coverage.

---

### Phase 6: Documentation

**Prompt:**
> "Push Phase 5 and write the final README and `AI_WORKFLOW.md`."

**AI contributions:** a requirements-coverage table (PDF requirement → file), an "Extending the system" section covering likely interview scenarios, missing authentication documented as an explicit tradeoff, and a workflow document built from this log rather than from memory.

---

### Phase 7: Requirement Audit & Extensions

**Prompts:**
> "Confirm the PDF's four example triggers are covered exactly as written."

> "Assess three optional extensions: event deduplication, an offline inbox, and a PvP defeat event that notifies both players."

> "Implement the PvP defeat event and the offline inbox. Players coming back online should see what they missed."

**AI contributions & key decisions:**
* Added a test that runs `playerLeveledUp(1, 15)`, `itemAcquired(2, "SwordOfAzeroth")`, `friendRequestSent(3, 1)` and `friendRequestAccepted(1, 3)` **argument for argument**. Earlier tests had passed an explicit item rarity.
* **Deduplication: declined.** The in-process bus delivers exactly once and nothing retries, so duplicates can't occur. It is documented as a requirement only once a real broker is introduced.
* **`PvPDefeatedEvent`: simplified to notify the loser only**, mirroring attack → defender. One event, one formatter, and no router change. The existing "every event has a strategy" test flagged the new event immediately.
* **Offline inbox:**
  * A new `INotificationInbox` port with a bounded in-memory adapter (latest 50 per player).
  * `INotificationChannel.send()` now reports whether delivery succeeded, and the router keeps undelivered notifications.
  * Opted-out notifications are never stored.
  * On connect, the endpoint replays missed notifications as `{"type": "missed"}`, and the dashboard labels them.
  * Scope was widened from "social events" to **every** missed notification the player hasn't opted out of, since a missed attack matters too.
* **Self-correction:** the first mutation run **hung** instead of failing (a test waited for a message that never came). The test now triggers a reply first so a missing replay fails fast, and mutation runs use a timeout.

---

### Phase 8: Verification & Hardening

**Prompts:**
> "Live-test offline delivery: take each player offline in turn, send events from the other, and confirm everything arrives on reconnect. Then audit the code against the PDF and best practices."

> "The architecture diagram is hard to read. Fix it."

> "Restructure the prompt log into a phase-by-phase format with an interview defense table."

**AI contributions & verification results:**
* **Clean test conditions first:** the server log showed a second, user-opened tab holding a Player 1 socket, which would have made "offline" untestable. The AI paused instead of reporting a misleading pass, then restarted the server for a clean state.
* **Round A:** Player 1 offline. All four notifications from Player 2 were logged as kept and arrived on reconnect, labelled "Missed while offline". Player 2's own level-up did not leak in. Accept on a missed friend request worked.
* **Round B:** Player 2 had Social off, then went offline. Social events were suppressed and only the game events were kept and replayed. The preference survived the reconnect. Reconnecting again replayed nothing. No console or server errors.
* **Static analysis:** `mypy` was clean. `ruff` (E, F, W, B, UP, SIM, I) found only typing modernizations for the 3.10 floor; these were applied and reviewed, and ruff now runs in CI.
* **Diagram:** the ASCII diagram had become inaccurate (it showed the channel writing to the inbox; the router does) and overflowed on GitHub. It was replaced with a Mermaid diagram, verified in light and dark themes under Mermaid's `strict` mode, as GitHub renders it.

---

## Key Architectural Trade-offs & Interview Defense Points

| Decision | Chosen solution | Alternative considered | Justification |
| :--- | :--- | :--- | :--- |
| **Delivery transport** | WebSockets behind `INotificationChannel` (plus a console adapter) | REST polling, Server-Sent Events | True push in real time. The port keeps the core transport-agnostic, so push or email are new adapters. |
| **Event routing** | In-process async event bus | Kafka, RabbitMQ, Redis Streams | No infrastructure and deterministic tests. The `IEventBus` contract fits a broker adapter unchanged. |
| **State persistence** | In-memory dictionaries (preferences, inbox) | SQLite, Postgres, Redis | Satisfies the brief's "simple map" with zero setup. Dependency inversion means a database adapter is a drop-in. |
| **Where preferences are checked** | After formatting, before sending | Before formatting | The formatter decides the recipient and category, so the router can only check once it knows them. Formatters are cheap pure functions. |
| **Offline players** | Bounded in-memory inbox, replayed once on connect | Drop; durable inbox with read receipts | Fixes the offline gap without infrastructure; the cap bounds memory. Production would use durable storage and acknowledgements. |
| **PvP notifications** | Defender (attack) and loser (defeat) only | Notify both players | No router change; one recipient per event keeps formatters simple. Multi-recipient fan-out is a documented extension. |
| **Duplicate events** | Not handled | Track processed `event_id`s | Exactly-once in-process delivery makes duplicates impossible. Deduplication becomes necessary with an at-least-once broker. |
| **Actor identity** | Taken from the WebSocket connection | Taken from the message payload | Prevents a client from acting as another player. |
| **Authentication** | None (player ID in the URL) | JWT on the WebSocket handshake | Out of scope for the exercise. Documented as the first production change. |
| **Containerization** | Not included | Dockerfile | The brief asks for build scripts only; `pip` + `uvicorn` keeps the run path minimal. |
