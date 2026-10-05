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

## Prompt 4: "Add README as well, commit and push"

**AI contribution:** Wrote a README that describes only what exists so far: features, an architecture diagram, layer responsibilities, key decisions, a tradeoffs table, and a roadmap. Unbuilt features are marked as upcoming phases. It will be updated as each phase lands and finalized in Phase 6. `readme` was restored in `pyproject.toml`, and a wheel build confirmed the packaging metadata is valid.

## Prompt 5: Phase 3, router and strategies

**AI contribution:** Implemented the formatting strategies, the `NotificationRouter` and the `GameEngine` / `SocialSystem` producers.

**Design decisions:**
- **Strategies are plain functions** in a registry (`DEFAULT_FORMATTERS`: event type → function). Each one decides the recipient, the category and the text. Returning `None` means "no notification" (used for COMMON items). Adding an event means one new function and one registry entry.
- **The router depends only on ports.** `subscribe_to(bus)` registers the router for every type that has a strategy. The pipeline is format → preferences check → send. The formatter registry can be injected (useful for tests and extension).
- **Producers use the PDF's trigger names, written in Python style** (`player_leveled_up(1, 15)` and so on). They import only the events and `IEventBus`; this was verified by grep.
- **New domain invariant:** a player can't target themselves in two-player events. The AI's first version used underscore attributes, which Pydantic treats as private instance attributes. It caught this itself and switched to an explicit `ClassVar[tuple[str, str]]` on a shared base class.
- **Kept deliberately simple:** a strategy returns at most one notification, and the router sends to a single channel. Fan-out to several recipients, or a composite channel for push plus in-app, are documented extension points rather than built features.

**Verification:** a scripted run of the four PDF triggers, plus the extra events, the common-item filter and a SOCIAL opt-out, all through the real bus and router with a recording channel. All eight expected notifications were delivered, and the two suppressed cases were dropped.

## Prompt 6: Phase 4, application entrypoint and dashboard

**Human correction mid-phase:** "We said we don't need Docker." The brief only asks for build scripts, so the Dockerfile was **dropped** from scope. This reverses the earlier "small Dockerfile" item; running is `pip install` plus `uvicorn`.

**AI contribution:**
- **`src/bootstrap.py`:** a composition root, `build_system(channel)`, shared by the server and the demo. The delivery channel is injected.
- **`main.py`:** `create_app()` factory, so tests get a fresh state per app. Provides `/` (dashboard), `/health` and `/ws/{player_id}`. Actions are dispatched with `match` to the `GameEngine` / `SocialSystem` producers. **The actor always comes from the connection, never from the payload.** Invalid JSON, unknown actions, missing fields and domain validation errors (e.g. attacking yourself, level 0) return `{"type": "error"}` and the socket stays open.
- **`ConsoleChannel` + `demo.py`:** a headless run of the PDF triggers. It is a second adapter for the same router, a concrete example of the Adapter pattern.
- **`Notification.actor_id` (optional):** added so the client can act on a notification (the **Accept** button on friend requests needs the sender's ID).
- **`static/index.html`:** Tailwind and vanilla JavaScript. Two panels built from a `<template>`, preference toggles, game and social actions, a live feed, inline Accept, and a Disconnect button that demonstrates the offline-drop tradeoff. All server text is inserted with `textContent` (no XSS through item names).

**Verification:**
- `python demo.py` output matched the PDF examples.
- A `TestClient` script covered the full protocol and 8 malformed-input cases.
- A manual browser run covered the attack (defender only), friend request → Accept → requester notified, Social off (follow suppressed, attack delivered), Disconnect (controls disabled, status shows drops) and multi-tab fan-out (the logs showed two sockets per player).

## Prompt 7: "Remove parse_event and start Phase 5"

**Human decision:** remove `parse_event()`. After Phase 4, the endpoint calls the producers directly, so the discriminated-union parser had become dead code.

**AI contribution: test suite (57 tests) and CI**
- **`conftest.py`:** real in-memory bus and repository, a `RecordingChannel` test double, producer fixtures, and an `opt_out` helper.
- **`test_router.py` (the brief's three required tests, plus more):** PDF triggers formatted and delivered; SOCIAL opt-out drops friend requests but allows level-ups; PvP goes strictly to the defender. Also covered: the GAME opt-out, opt-out being per player, preferences checked for the *recipient* (not the actor), re-enabling a category, and an **extensibility test**, where a brand-new `GuildInviteEvent` is delivered by adding only a strategy.
- `test_formatters.py`, `test_domain.py`, `test_infrastructure.py` (including the dead-socket test promised in Phase 2) and `test_app.py` (real WebSocket sessions through `create_app()`).
- **Mutation check:** five realistic bugs were planted one at a time (PvP to the attacker, preferences ignored, preferences checked for the wrong player, bus failures not isolated, actor read from the payload). Each was caught by a failing test, then reverted.
- **CI:** GitHub Actions runs `pytest` and `python demo.py` on Python 3.10 (the minimum supported) and 3.13.

**Issues the AI caught in its own work:**
- The first `test_app.py` helper entered the WebSocket context manager twice. It was replaced with a `@contextmanager`.
- A test that inspected the bus's private `_handlers` was dropped, because it tested implementation details instead of behaviour.

**Environment notes:**
- Starlette 1.x warns that `httpx` is deprecated for its TestClient. That single warning is filtered in `pyproject.toml` so the dependency range stays wide.
- A clean virtual environment install (`pip install -e ".[dev]"` → `pytest` → `demo.py`) was verified to mirror what a reviewer does.

## Prompt 8: "You push it and start Phase 6"

**AI contribution:** Pushed Phase 5 and confirmed through the GitHub API that the first CI run passed on **Python 3.10 and 3.13** (install, pytest, demo). This was the first real check of 3.10 compatibility, since only 3.13 was available locally.

**Documentation:**
- **`AI_WORKFLOW.md`:** tools, the gated workflow, who did what, every prompt in order, where AI review improved the plan, where human oversight changed the outcome (Docker reversal, dead-code removal, the git-identity incident), the AI's self-caught mistakes, the verification approach, and lessons learned. It was built from this log rather than from memory. The AI corrected its own first draft of the prompt table to match the real sequence of prompts.
- **README, final pass:** a requirements-coverage table (PDF requirement → file), an "Extending the system" table for the interview's what-if questions (new event, new channel, offline inbox, horizontal scaling, reliability, batching), missing authentication added as an explicit tradeoff, and the in-progress roadmap replaced with a "How it was built" summary.

## Prompt 9: "All done? … have we done that?" (quoting the PDF's example triggers)

**Human check:** I asked whether the PDF's four example triggers were covered.

**AI answer:** Yes, in `tests/test_router.py` and `demo.py`. However, both passed an explicit `ItemRarity.LEGENDARY` to `item_acquired`, to match the PDF's sample message "legendary Sword of Azeroth". The PDF's literal call `itemAcquired(2, "SwordOfAzeroth")` has no rarity argument and wasn't tested exactly as written. Added `test_pdf_example_triggers_work_exactly_as_written`: all four calls argument for argument. Without a rarity, the item defaults to RARE and is still notified. The suite now has 58 tests.

## Prompt 10: optional extras ("is these important?")

**Human input:** Shared three optional ideas: event deduplication, an offline notification inbox, and `PvPDefeatedEvent` notifying both players.

**AI assessment:**
- **Deduplication: skip.** The in-process bus delivers exactly once and nothing retries, so duplicates can't occur. The guard would be dead code with an ever-growing ID set. It stays as an interview answer (the README's Reliability row).
- **Inbox:** the only extra that fixes a real weakness (offline drops). It's worth building if there's time.
- **PvP defeat:** the PDF says "attacked **or defeated**". Build it, but notify **only the loser**, mirroring attack → defender. Notifying both players would change every formatter's return type for a nice-to-have.

**Human decision:** build #3 as suggested and #2 as well ("after coming online, social events should be visible").

**#3 delivered:** `PvPDefeatedEvent(winner_id, loser_id)`, one formatter, a `GameEngine.player_defeated` method, a `"defeat"` action, a dashboard button, and the demo line. No router change was needed. The existing `test_every_domain_event_has_a_strategy` immediately required the new formatter, and new tests cover routing to the loser only, self-targeting rejected and the WebSocket round trip (61 tests).
