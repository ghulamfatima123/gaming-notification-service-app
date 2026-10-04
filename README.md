# Gaming Notification Service

A real-time, event-driven notification system for a multiplayer gaming platform. Game and social subsystems emit domain events. A notification pipeline turns them into player-facing notifications, checks each player's preferences, and pushes them live over WebSockets.

Built with **Python 3.10+, FastAPI, and Pydantic v2**. Infrastructure is entirely in memory, so it needs no external services (no Redis, no database).

> **Status:** in progress, built in reviewed phases (see [Roadmap](#roadmap)).

---

## Features

**In-game events**
| Event | Example notification |
|---|---|
| Level up | "Congratulations! You've reached level 15!" |
| Item acquired (rare or better) | "You've acquired the legendary Sword of Azeroth!" |
| Challenge completed | Quest or achievement completion |
| PvP attacked | Sent to the **defender** only |

**Social events**
| Event | Who is notified |
|---|---|
| Friend request sent | The recipient |
| Friend request accepted | The original requester |
| New follower | The player being followed |

**Player preferences.** Each player can turn **Game** and **Social** notifications on or off independently. Everything is enabled by default (opt-out).

**Real-time delivery.** In-app notifications go over WebSockets. A player can be connected from several tabs at once.

---

## Architecture

The design is Hexagonal (Ports & Adapters) with an event-driven pipeline. The core depends only on abstract **ports**, and concrete **adapters** plug in at the edges.

```
 GameEngine / SocialSystem          (producers: know nothing about notifications)
            │  publish(BaseEvent)
            ▼
     ┌─────────────┐
     │  IEventBus  │◄──── InMemoryEventBus
     └─────┬───────┘
           │  subscribe
           ▼
  ┌──────────────────────┐   format (Strategy)   ┌───────────────┐
  │  NotificationRouter  │──────────────────────►│  Formatters   │
  └──────┬────────┬──────┘                       └───────────────┘
         │        │ get(player_id)
         │        ▼
         │  ┌───────────────────────┐
         │  │ IPreferenceRepository │◄── InMemoryPreferenceRepository
         │  └───────────────────────┘
         │ send(notification)
         ▼
  ┌──────────────────────┐
  │ INotificationChannel │◄──── WebSocketChannel (Adapter)
  └──────────────────────┘
```

| Layer | Path | Responsibility |
|---|---|---|
| Domain | `src/domain/` | Pure Pydantic models: events, `Notification`, preferences. No I/O. |
| Ports | `src/ports/` | Abstract interfaces: `IEventBus`, `IPreferenceRepository`, `INotificationChannel`. |
| Services | `src/services/` | `NotificationRouter` and the formatting strategies (the business rules). |
| Infrastructure | `src/infrastructure/` | In-memory adapters that implement the ports. |

### Key design decisions
- **Producers are fully decoupled.** Events carry only facts, with no category and no recipient. The formatting strategy for each event decides the category and who gets notified (for example, PvP goes to the defender). Adding a new event type never changes the producers.
- **Strategy pattern for formatting.** There is one strategy per event type. Adding a new notification means adding one event class and one strategy.
- **Adapter pattern for delivery.** The router only sees `INotificationChannel`. Push or email would be new adapters, with no changes to the core.
- **Async ports throughout.** Swapping the in-memory adapters for a database or message broker doesn't change the interfaces.
- **Typed event parsing.** Each event has a fixed `event_type`, so `parse_event()` validates raw JSON into the correct event class.

### Tradeoffs (deliberate, for the scope of this exercise)
| Choice | Why | Production path |
|---|---|---|
| In-process event bus | No infrastructure needed; deterministic tests | Kafka / SNS+SQS / Redis Streams adapter |
| `publish` awaits handlers | Simple and predictable; failures are isolated per handler | Fire-and-forget with a durable queue and retries |
| Offline players' notifications are dropped (and logged) | Keeps the channel stateless | A persistent inbox, replayed when the player connects |
| In-memory preferences | Satisfies the "simple map" requirement | A database-backed `IPreferenceRepository` |

---

## Project structure

```
├── pyproject.toml
├── src/
│   ├── domain/               # events.py, notification.py, preferences.py
│   ├── ports/                # event_bus.py, preference_repository.py, notification_channel.py
│   ├── services/             # router + formatting strategies        (Phase 3)
│   └── infrastructure/       # memory_event_bus.py, memory_prefs_repo.py, channels/
├── static/index.html         # live two-player dashboard              (Phase 4)
├── tests/                    # pytest suite                           (Phase 5)
└── docs/PROMPT_LOG.md        # AI prompts and decisions, phase by phase
```

---

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Instructions for running the server, the dashboard, the demo, Docker and the tests will be added as those phases land.

---

## Roadmap

- [x] **Phase 1:** domain models and ports
- [x] **Phase 2:** in-memory adapters (event bus, preference repository, WebSocket channel)
- [ ] **Phase 3:** formatting strategies, `NotificationRouter`, `GameEngine` / `SocialSystem` producers
- [ ] **Phase 4:** FastAPI app, two-player dashboard, headless `demo.py`, Dockerfile
- [ ] **Phase 5:** pytest suite and GitHub Actions CI
- [ ] **Phase 6:** final docs and `AI_WORKFLOW.md`

## AI usage

This project was built with Claude Code as a pair-programmer under a phase-by-phase review workflow. The architecture and constraints were human-defined. Every prompt and decision is logged in [`docs/PROMPT_LOG.md`](docs/PROMPT_LOG.md).
