# AI Workflow

How I used AI to go from the challenge brief to a working, tested system, and where human judgment steered the result.

> **Short version:** I designed the architecture and set hard constraints up front. I then used Claude Code as a pair-programmer in **six gated phases**, reviewing each phase before the next began. The AI drafted code, checked my brief against the PDF, verified its own output, and caught several of its own mistakes. I made every scope call, including two reversals (dropping Docker and removing an unused parser). I also caught a process error the AI made (committing with the wrong git identity).

---

## 1. Tools

| Tool | Used for |
|---|---|
| **Claude Code** (Claude Opus 5.5, in the Claude desktop app) | Reading the brief, planning, writing code, running scripts and tests, driving a browser to test the dashboard, git |
| **Plan mode** | Phase 1 started read-only: the AI read the PDF and wrote a plan, and could not write code until I approved it |
| **Built-in browser pane** | The AI clicked through the live dashboard to verify the real-time flows |
| **GitHub Actions** | CI: the tests and the demo on Python 3.10 and 3.13 |
| [`docs/PROMPT_LOG.md`](docs/PROMPT_LOG.md) | A log kept during development (not reconstructed afterwards) of every prompt, decision and correction |

## 2. The workflow

```
 Requirements (PDF)
        │
        ▼
 Human: architecture + constraints ──► AI: read PDF, find gaps, propose plan
                                                   │
        ┌──────────────────────────────────────────┘
        ▼
 ┌─► Human review / approve ──► AI implements one phase ──► AI verifies (scripts, tests, browser)
 │                                                                   │
 └──────────── commit + log the prompt and decisions ◄───────────────┘
```

**The rules I set before any code was written:**
1. **One phase at a time:** "Do not generate the entire project at once. Wait for my confirmation after each phase." This kept every diff small enough to actually review.
2. **Fixed architecture:** DDD, Hexagonal (Ports & Adapters), event-driven. Strategy for formatting, Adapter for channels. A fixed directory layout.
3. **Hard boundaries:** in-memory only (no Redis or Postgres). Producers (`GameEngine`, `SocialSystem`) must never know about notifications; they may only emit events to an `IEventBus`.
4. **No over- or under-engineering:** every addition had to be justified against the brief.

| Phase | Delivered |
|---|---|
| 1 | Domain models (events, `Notification`, preferences) and the ports (abstract interfaces) |
| 2 | In-memory adapters: event bus, preference repository, WebSocket channel |
| 3 | Formatting strategies, `NotificationRouter`, `GameEngine` / `SocialSystem` producers |
| 4 | FastAPI app, two-player live dashboard, headless `demo.py` |
| 5 | pytest suite (71 tests today) and GitHub Actions CI |
| 6 | README and this document |

## 3. Who did what

| I (human) decided | The AI did |
|---|---|
| The architecture style and the design patterns | Drafted the domain models, ports, adapters, router and dashboard within those constraints |
| The layer boundaries and the "producers know nothing" rule | Checked the boundary (e.g. grepped producers to confirm they never import notification code) |
| Scope: what's in, what's out | Compared my brief with the PDF and **flagged gaps** for me to approve or reject |
| Approved or reversed every proposal | Proposed small, defensible additions with a reason for each |
| When to commit and push | Wrote the commits, the README and the prompt log; ran the pushes I approved |
| — | Generated test coverage, then **checked the tests by planting bugs** |

## 4. Prompts I used

The full opening brief is in the [Appendix](#appendix-the-opening-prompt). Later prompts were short, because the phase plan carried the context; they are shown condensed to their intent. The phase-by-phase detail is in [`docs/PROMPT_LOG.md`](docs/PROMPT_LOG.md).

| # | Prompt (condensed) | What happened |
|---|---|---|
| 1 | The architecture brief and phased plan (Appendix) | The AI read the PDF first, compared it with my brief, and wrote a Phase 1 plan in read-only plan mode |
| 2 | Audit the plan against the PDF: is containerization needed, and is anything over- or under-engineered? | The AI reviewed the whole plan and proposed 5 additions (see §5) |
| 3 | Approved: push Phase 1, implement the in-memory adapters | Git initialized, Phase 1 pushed, adapters built |
| 4 | Add a README for the current state, push, continue with Phase 3 | README added; Phase 2 pushed; strategies, router and producers built and held for review |
| 5 | Commits must use my personal email, not the machine's work identity | Repo-local identity set and history rewritten (see §6) |
| 6 | Summarize progress and remaining work | A status report, including GitHub being out of sync after the rewrite |
| 7 | Proceed with Phase 4; Docker is out of scope | App, dashboard and demo built; Dockerfile dropped |
| 8 | Push was rejected after the history rewrite: how to resolve? | The AI explained why, warned **not** to `git pull` (that would re-merge the old commits), and gave a `--force-with-lease` command pinned to the old commit |
| 9 | Remove the unused `parse_event`, then build the test suite and CI | Dead code removed; tests and CI added |
| 10 | Push Phase 5 and write the final documentation | README and this document |
| 11 | Confirm the PDF's example triggers are covered exactly as written | Earlier tests passed an explicit item rarity; a test now runs the four PDF calls **argument for argument** |
| 12 | Assess three optional extensions: deduplication, an offline inbox, PvP defeat notifying both players | The AI recommended skipping deduplication (duplicates can't occur in this design), a **simpler** PvP defeat (notify the loser only, no router change), and the inbox if time allowed |
| 13 | Build the PvP defeat event and the offline inbox; returning players should see what they missed | Both built. Scope widened from social events to **every** missed notification the player hasn't opted out of |
| 14 | Live-test offline delivery for both players, then audit against the PDF and best practices | Two clean live-test rounds passed; `ruff` + `mypy` added as checks, ruff in CI |
| 15 | The architecture diagram is hard to read: fix it | The ASCII diagram was also inaccurate; replaced with a verified Mermaid diagram |
| 16 | Restructure the prompt log into a phase-by-phase format with an interview defense table | `docs/PROMPT_LOG.md` rewritten in that format |
| 17 | Design a sidebar showing every player's information | A two-artboard design; the AI noted which data the server already had and which it didn't track |
| 18 | Implement the sidebar design | An opt-in `watch_roster` presence feed (online, tabs, waiting, preferences) plus session stats in the dashboard; no faked data |

## 5. Where AI review improved my plan

Before writing code, I asked the AI to check my brief against the PDF. It found real gaps:

- **Missing events.** My brief listed five events. The PDF also requires **Challenge Completed** and **New Follower**, so both were added.
- **Missing producers.** My plan had no `GameEngine` or `SocialSystem`, even though the PDF's example usage is literally `gameEngine.playerLeveledUp(1, 15)`. These were added as thin classes that only publish events.
- **No headless demo.** Reviewers "clone the repo and run it". `demo.py` now runs the PDF's four triggers in about a second, with no browser needed.
- **"Rare or valuable" items.** The spec only notifies for valuable items, so the item strategy returns `None` for COMMON items.
- **Ambiguous direction.** `friendRequestAccepted(1, 3)` means player 1 accepted player 3's request, so player 3 is notified. The fields are named `accepter_id` / `requester_id` to make that explicit.

## 6. Where human oversight changed the outcome

- **Docker: approved, then reversed.** The AI suggested a small optional Dockerfile and I first agreed. Mid-Phase 4, I pushed back and took it out of scope. The brief only asks for build scripts, so it was dropped. That's one less thing to maintain and defend.
- **Removing dead code.** After Phase 4, the WebSocket endpoint called the producers directly, which left a typed-JSON parser (`parse_event`) from Phase 1 unused. The AI asked whether to keep it with tests or remove it. I chose to remove it rather than defend unused code.
- **Git identity.** The AI committed using the machine's global git identity, which was my work email, and pushed it to my public repo. I caught it. The fix was a repo-local `user.email`, a history rewrite that kept the original dates, and a force-push. The AI's safety guard **blocked it from force-pushing on its own**, so I ran the push myself. Lesson: check the commit identity before the first commit in any repo; the AI now does this by default.
- **The offline inbox was my call.** The design originally dropped notifications for offline players, as a documented tradeoff. After the core was done, I decided players should see what they missed. The AI built it behind a new port (`INotificationInbox`), so the router change is three lines: "if the channel couldn't deliver it, keep it". It also planted bugs to prove the new tests guard it.
- **Pushing was gated.** Phases were committed locally and pushed only after I said so.

## 7. Where the AI caught its own mistakes

I asked the AI to verify everything it wrote, and the verification found real bugs before they were committed:

| What went wrong | How it was caught | Fix |
|---|---|---|
| The validator for "a player can't target themselves" used `_underscore` attributes, which Pydantic treats as **private instance attributes**, so they might not exist during validation | Code review before testing | An explicit `ClassVar[tuple[str, str]]` on a shared base class |
| The WebSocket test helper entered the connection's context manager **twice** | Reviewing its own test code | Rewritten as a `@contextmanager` |
| A test inspected the bus's private `_handlers` | Self-review: it tested implementation, not behaviour | Removed; the behaviour is covered end to end |
| The prompt log claimed "dead-socket cleanup" was verified when that path hadn't actually been exercised | Re-reading its own claim against what it had run | The log was corrected and a dedicated test was added in Phase 5 |
| The first version of the inbox's WebSocket test **hung** (instead of failing) when a planted bug stopped the replay, because it waited for a message that never came | The planted-bug check timed out | The test now triggers a reply first, so a missing replay fails fast; the check runs with a timeout |
| Dashboard clicks landed on the wrong buttons in a tiny browser pane | Inspecting the DOM state after clicking | Switched to element references; the feature itself was fine |

## 8. How AI output was verified

Code that only *looked* right was never accepted. Each phase ended with evidence:

- **Phases 1–3:** scripted smoke runs through the real bus, router and preferences (e.g. the PDF triggers produced exactly the four expected messages).
- **Phase 4:** a `TestClient` script exercising the full WebSocket protocol, including 8 malformed inputs. A live browser session covering an attack (defender only), friend request → Accept → requester notified, Social opt-out, Disconnect, and two tabs per player.
- **Phase 5:** the test suite (57 tests then, 71 now) plus a **mutation check**. Five realistic bugs were planted one at a time, and the suite caught every one:
  - PvP sent to the attacker
  - preferences ignored
  - preferences checked for the wrong player
  - bus failures not isolated
  - the acting player read from the client's payload
- **Static checks:** `ruff` (lint, now also in CI) and `mypy` (types) both pass. Their only findings were Python 3.10 typing modernizations, with no bugs.
- **Final live test (two rounds, fresh server):** each player went offline in turn while the other sent events. All missed notifications arrived on reconnect, opted-out ones were correctly not kept, nothing was replayed twice, and there were no console or server errors.
- **Install check:** a fresh virtual environment, then `pip install -e ".[dev]"`, `pytest` and `python demo.py`, exactly what a reviewer runs. CI repeats this on Python 3.10 and 3.13.

## 9. What worked, and what I'd do differently

**What worked**
- **Architecture first, AI second.** Because the patterns and boundaries were fixed up front, the AI's output was easy to judge: either it respected the boundaries or it didn't.
- **Phase gates.** Small, reviewable steps kept me in control and made reversals (Docker, `parse_event`) cheap.
- **Asking the AI to challenge the plan, not just execute it.** The most valuable output of the session was the gap analysis against the PDF.
- **Requiring evidence.** "Show me it runs" caught bugs that reading the code alone would have missed.
- **Logging prompts as I went.** This document is based on a log written during development, not on memory.

**What I'd do differently**
- Set the repo-local git identity before the first commit.
- Decide on optional extras (like Docker) explicitly in the first planning round, rather than approving them as part of a batch.

---

## Appendix: the opening prompt

*The constraints are verbatim. The per-phase task lists are condensed.*

> You are an expert Principal Python Engineer and system designer. I am completing a coding challenge for a backend engineering role. The challenge requires building a Real-Time Notification System for a gaming platform. I have already designed the architecture using Domain-Driven Design (DDD), Ports & Adapters (Hexagonal Architecture), and an Event-Driven pipeline.
>
> Your task is to help me implement this codebase step-by-step. Do not generate the entire project at once. Wait for my confirmation after each phase.
>
> **Strict Architectural Constraints:**
> - Tech Stack: Python 3.10+, FastAPI (for WebSockets), Pydantic v2 (for models), Pytest (for testing).
> - No External Infrastructure: Use strictly in-memory data structures for the Event Bus, Preference Repository, and WebSocket Connection Manager. No Redis, no Postgres.
> - Decoupling: Game triggers (GameEngine, SocialSystem) MUST NOT know about notifications. They only emit BaseEvent objects to an IEventBus.
> - Design Patterns: Use the Strategy Pattern for formatting events into notifications, and the Adapter Pattern for notification delivery channels.
>
> **Target Directory Structure:** `main.py`, `pyproject.toml`, `src/{domain,ports,services,infrastructure}`, `static/index.html`, `tests/`.
>
> **Phase 1: Domain Layer & Interfaces.** `NotificationCategory` enum (GAME, SOCIAL) and the `Notification` model; `BaseEvent` and specific events (`LevelUpEvent`, `ItemAcquiredEvent`, `FriendRequestSentEvent`, `FriendRequestAcceptedEvent`, `PvPAttackedEvent`); a preferences model; `IEventBus` (publish/subscribe), `IPreferenceRepository` (get/set) and `INotificationChannel` (send) using `abc`.
>
> **Phase 2: Infrastructure & Adapters.** An async in-memory event bus; an in-memory dictionary of preferences; a WebSocket channel that holds active connections and pushes JSON notifications to specific users.
>
> **Phase 3: Core Business Logic.** Strategy functions mapping each event to a `Notification`; a `NotificationRouter` that subscribes to the bus, formats, checks whether the user opted out, and passes enabled notifications to the channel.
>
> **Phase 4: Application Entrypoint & Interactive UI.** `main.py` wiring the bus, repo, router and channel; a `/ws/{player_id}` endpoint that listens for raw JSON actions (simulating the GameEngine); a TailwindCSS + vanilla JS split-screen dashboard for Player 1 and Player 2 with event buttons, preference toggles and a live feed.
>
> **Phase 5: Automated Testing.** Fixtures for the bus, the repo and a recording mock channel. Tests that events are formatted and delivered, that opting out of SOCIAL drops friend requests but allows level-ups, and that `PvPAttackedEvent` goes strictly to the defender.
>
> **Phase 6: Documentation for the Interview.** README (setup, architecture, dashboard usage) and AI_WORKFLOW.md (how AI drafted boilerplate, enforced Clean Architecture and generated test coverage, while human oversight dictated the design patterns and boundary constraints).
>
> Stop and ask for my review when each phase is complete.
