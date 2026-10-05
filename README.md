# Gaming Notification Service

[![CI](https://github.com/ghulamfatima123/gaming-notification-service-app/actions/workflows/ci.yml/badge.svg)](https://github.com/ghulamfatima123/gaming-notification-service-app/actions/workflows/ci.yml)

A real-time, event-driven notification system for a multiplayer gaming platform. Game and social subsystems emit domain events. A notification pipeline turns them into player-facing notifications, checks each player's preferences, and pushes them live over WebSockets.

Built with **Python 3.10+, FastAPI, and Pydantic v2**. Infrastructure is entirely in memory, so it needs no external services (no Redis, no database).

**Quick start:** `pip install -e ".[dev]"`, then `python demo.py` (headless) or `uvicorn main:app` (live dashboard at http://localhost:8000). Details in [Getting started](#getting-started).

**How AI was used:** see [`AI_WORKFLOW.md`](AI_WORKFLOW.md) and the per-phase log in [`docs/PROMPT_LOG.md`](docs/PROMPT_LOG.md).

---

## Features

**In-game events**
| Event | Example notification |
|---|---|
| Level up | "Congratulations! You've reached level 15!" |
| Item acquired (rare or better) | "You've acquired the legendary Sword of Azeroth!" |
| Challenge completed | Quest or achievement completion |
| PvP attacked | Sent to the **defender** only |
| PvP defeated | Sent to the **loser** only |

**Social events**
| Event | Who is notified |
|---|---|
| Friend request sent | The recipient |
| Friend request accepted | The original requester |
| New follower | The player being followed |

**Player preferences.** Each player can turn **Game** and **Social** notifications on or off independently. Everything is enabled by default (opt-out).

**Real-time delivery.** In-app notifications go over WebSockets. A player can be connected from several tabs at once.

### Requirements coverage

| Challenge requirement | Where it lives |
|---|---|
| In-game events (level up, item, challenge, PvP attacked or defeated) | `src/domain/events.py`, `src/services/formatters.py` |
| Social events (friend request, accepted, new follower) | Same, plus `src/producers/social_system.py` |
| In-app, real-time channel | `src/infrastructure/channels/websocket_channel.py` and the dashboard |
| Clear notification content | `formatters.py`. The PDF's example messages are asserted word for word in tests. |
| Per-category user preferences | `src/domain/preferences.py`, `src/infrastructure/memory_prefs_repo.py` |
| `Notification` class | `src/domain/notification.py`. The brief mentions a provided class, but none was attached, so it is defined here. |
| Notification handling (interfaces, services) | `src/ports/`, `src/services/router.py` |
| Event handling: receive, then dispatch | `src/infrastructure/memory_event_bus.py` → `NotificationRouter` |
| Example usage | `demo.py` (the PDF's triggers) and `static/index.html` |

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
| Producers | `src/producers/` | `GameEngine` and `SocialSystem`, stand-ins for platform subsystems. They depend only on `IEventBus`. |

### Key design decisions
- **Producers are fully decoupled.** Events carry only facts, with no category and no recipient. The formatting strategy for each event decides the category and who gets notified (for example, PvP goes to the defender). Adding a new event type never changes the producers.
- **Strategy pattern for formatting.** There is one strategy per event type. Adding a new notification means adding one event class and one strategy.
- **Adapter pattern for delivery.** The router only sees `INotificationChannel`. Push or email would be new adapters, with no changes to the core.
- **Async ports throughout.** Swapping the in-memory adapters for a database or message broker doesn't change the interfaces.
- **Domain invariants live in the domain.** A player can't befriend, follow or attack themselves. Two-player events reject this when they are created.
- **Strategies can decline.** A formatter returning `None` means "don't notify". This is how common items are filtered out (the spec only asks for rare or valuable items).
- **Stable event names.** Each event has a fixed `event_type` (e.g. `"level_up"`), which every notification carries so clients can tell them apart.

### Tradeoffs (deliberate, for the scope of this exercise)
| Choice | Why | Production path |
|---|---|---|
| In-process event bus | No infrastructure needed; deterministic tests | Kafka / SNS+SQS / Redis Streams adapter |
| `publish` awaits handlers | Simple and predictable; failures are isolated per handler | Fire-and-forget with a durable queue and retries |
| Offline players' notifications are dropped (and logged) | Keeps the channel stateless | A persistent inbox, replayed when the player connects |
| The dashboard drives producers over the player's own WebSocket | One connection per player; the actor can't be spoofed | Producers live in their own services and publish to a shared broker |
| In-memory preferences | Satisfies the "simple map" requirement | A database-backed `IPreferenceRepository` |
| No authentication: the player ID comes from the URL | Out of scope for the exercise; keeps the demo frictionless | Authenticate the WebSocket handshake (e.g. a JWT) and derive the player from the token |

### Extending the system

| Scenario | What changes | What doesn't |
|---|---|---|
| **New event type** (e.g. guild invite) | One event class, one formatter, one producer method. Proven by `test_new_event_type_needs_only_a_new_strategy`. | Router, bus, channels |
| **Push or email channel** | A new `INotificationChannel` adapter. For several at once, a composite channel that fans out to each. | Router, formatters, producers |
| **Per-channel or per-event preferences** | `NotificationPreferences` keys become (category, channel) or event type | Producers, formatters |
| **One event notifies many players** (e.g. a guild raid) | A formatter returns a list instead of a single notification; the router loops | Producers, channels |
| **Offline delivery** | A notification inbox port: persist, then replay to the player on connect and mark as read | Formatters, producers |
| **Horizontal scaling** | A broker adapter for `IEventBus`. Sockets are per instance, so delivery needs pub/sub routing by player (e.g. Redis). Preferences move to a database with a cache. | Domain, formatters, router logic |
| **Reliability** | Outbox pattern on the producer side; retries with deduplication by `event_id` / notification `id` | Domain model |
| **Batching or rate limiting** ("3 players attacked you") | A decorator around the channel that aggregates within a time window | Router, formatters |

---

## Project structure

```
├── main.py                   # FastAPI app: WebSocket endpoint + dashboard
├── demo.py                   # headless walkthrough of the PDF triggers
├── pyproject.toml
├── src/
│   ├── bootstrap.py          # composition root (wires adapters to the core)
│   ├── domain/               # events.py, notification.py, preferences.py
│   ├── ports/                # event_bus.py, preference_repository.py, notification_channel.py
│   ├── services/             # router.py, formatters.py (strategies)
│   ├── infrastructure/       # memory_event_bus.py, memory_prefs_repo.py, channels/ (websocket, console)
│   └── producers/            # game_engine.py, social_system.py
├── static/index.html         # live two-player dashboard
├── tests/                    # pytest suite (58 tests)
├── .github/workflows/ci.yml  # pytest + demo on Python 3.10 and 3.13
├── AI_WORKFLOW.md            # how AI was used, and where human judgment steered
└── docs/PROMPT_LOG.md        # AI prompts and decisions, phase by phase
```

---

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 1. Headless demo (no browser needed)

```bash
python demo.py
```

This runs the challenge's example triggers (`playerLeveledUp(1, 15)`, `itemAcquired(2, "SwordOfAzeroth")`, `friendRequestSent(3, 1)`, `friendRequestAccepted(1, 3)`) and the other events through the real pipeline, then shows the preference opt-out. Each delivered notification is printed by a `ConsoleChannel`, a second delivery adapter that plugs into the same router.

### 2. Live dashboard

```bash
uvicorn main:app --reload
```

Open <http://localhost:8000>. Player 1 and Player 2 appear side by side, each with its own WebSocket connection.

| Try this | What you'll see |
|---|---|
| **Level up**, **Find an item**, **Complete a challenge** | The notification appears in that player's own feed. Common items produce none. |
| **Attack** / **Defeat Player N** | Only the defender (or loser) is notified. |
| **Friend request** → **Accept** in the other feed | The original sender gets "accepted your friend request". |
| Turn off **Social events**, then have the other player follow you | Nothing arrives. Game events still come through. |
| **Disconnect** a player, then trigger events at them | The notifications are dropped (see Tradeoffs). |
| Open the page in a second tab | Both tabs receive the player's notifications. |

The dashboard uses the Tailwind CDN, so it needs an internet connection for styling.

### 3. Tests

```bash
pytest
```

| File | Covers |
|---|---|
| `test_router.py` | The PDF triggers end to end; PvP goes only to the defender; SOCIAL opt-out drops friend requests but keeps level-ups (and the reverse); opt-out is per player and checked against the recipient; a new event type needs only a new strategy |
| `test_formatters.py` | Every domain event has a strategy; message text; rarity filtering; item-name formatting |
| `test_domain.py` | Self-targeting rejected; positive levels; immutability; preference defaults |
| `test_infrastructure.py` | Bus fan-out, catch-all subscriptions, failure isolation; repository defaults; WebSocket multi-tab delivery, offline drop, dead-socket cleanup |
| `test_app.py` | Real WebSocket sessions: attack, friend request → accept, preference toggle, 8 malformed inputs, the actor can't be spoofed |

The tests drive the real in-memory adapters, with a `RecordingChannel` test double in place of WebSockets. To check that the suite catches real defects, deliberately planted bugs were each confirmed to fail it: PvP sent to the attacker, preferences ignored, preferences checked for the wrong player, bus failures not isolated, and the actor read from the payload. CI runs the suite and the demo on Python 3.10 and 3.13.

### WebSocket protocol

`ws://localhost:8000/ws/{player_id}`. The acting player is always taken from the connection, never from the payload.

**Client → server**
```json
{"action": "level_up", "level": 16}
{"action": "acquire_item", "item_name": "SwordOfAzeroth", "rarity": "legendary"}
{"action": "complete_challenge", "challenge_name": "Dragon Slayer"}
{"action": "attack" | "defeat" | "send_friend_request" | "accept_friend_request" | "follow", "target_id": 2}
{"action": "set_preference", "category": "game" | "social", "enabled": false}
```

**Server → client:** `{"type": "notification", "data": {...}}`, `{"type": "preferences", "data": {...}}` (sent on connect and after each change), `{"type": "ack", "action": "..."}` and `{"type": "error", "message": "..."}`. Invalid input returns an error message and the connection stays open.

---

## How it was built

The project was built in six reviewed phases: domain and ports → in-memory adapters → router and strategies → app and dashboard → tests and CI → docs. There is one commit per phase. Claude Code was used as a pair-programmer. The architecture, constraints and every scope decision were mine, and each phase was reviewed before moving on. The full process is described in [`AI_WORKFLOW.md`](AI_WORKFLOW.md).
