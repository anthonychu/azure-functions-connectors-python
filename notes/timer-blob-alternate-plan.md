# Alternate Plan: Timer + Blob Storage (No Durable Functions)

## User Experience

Same decorator UX — the user doesn't know or care what's underneath:

```python
import azure.functions as func
from azure_connector_triggers import generic_connection_trigger, register_connector_triggers

app = func.FunctionApp()

@generic_connection_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",
    trigger_path="/Mail/OnNewEmail",
    trigger_queries={"folderPath": "Inbox"},
)
async def on_new_email(item: dict):
    print(f"New email: {item['subject']}")

@generic_connection_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    trigger_path="/datasets/default/tables/Lead/onnewitems",
)
def on_new_lead(item: dict):
    print(f"New lead: {item['Name']}")

# Required — wires up timer function + blob state.
# Raises error if decorators exist but this is never called.
register_connector_triggers(app)
```

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  Timer Trigger (runOnStartup=True, every 1 min)      │
│                                                      │
│  For each registered trigger:                        │
│    1. Read state from blob (cursor + backoff)        │
│    2. Check if enough time has passed (backoff)      │
│    3. Poll connector via dynamicInvoke               │
│    4. If items → enqueue each to Storage Queue       │
│    5. Save updated state to blob                     │
└──────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
  ┌──────────────────┐     ┌──────────────────┐
  │ Blob Storage     │     │ Storage Queue    │
  │                  │     │                  │
  │ cursor + backoff │     │ {instance_id,    │
  │ per trigger      │     │  item}           │
  └──────────────────┘     └──────────────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │ Queue Trigger     │
                           │ (scales out)      │
                           │                   │
                           │ Looks up handler  │
                           │ by instance_id,   │
                           │ calls it with item│
                           └──────────────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │ Azure API        │
                           │ Connection       │
                           │ (office365, etc) │
                           └──────────────────┘
```

The timer is the **poller** — it polls connectors and enqueues items. It never
calls user handlers directly. The queue function is the **processor** — it scales
out independently based on queue depth.

## How It Works

### Single Timer Function

`register_connector_triggers(app)` creates **one** timer function that powers
ALL registered triggers. On each tick, it iterates over all triggers and polls
any that are due (based on their individual backoff state).

No matter how many `@generic_connection_trigger` decorators you have — 1 or 50 —
there is always just one timer function.

```python
QUEUE_NAME = "connector-trigger-items"

def register_connector_triggers(app, poll_interval="0 */1 * * * *"):
    """
    Args:
        app: The FunctionApp instance
        poll_interval: CRON schedule for the polling timer. Default: every 1 minute.
                       This is the tick rate — individual triggers manage their own
                       backoff independently within this.
    """
    _register_env_vars()
    _validate_registrations()

    # Timer: polls connectors and enqueues items (singleton — no overlap)
    @app.function_name("ConnectorTriggerPoller")
    @app.timer_trigger(
        schedule=poll_interval,
        arg_name="timer",
        run_on_startup=True
        # UseMonitor defaults to True — ensures only one instance runs at a time
        # and skips if previous execution is still running
    )
    async def poller(timer: func.TimerRequest):
        sem = asyncio.Semaphore(5)  # max 5 concurrent polls
        async def poll_with_limit(trigger):
            async with sem:
                await _poll_trigger(trigger)
        await asyncio.gather(*[poll_with_limit(t) for t in _registered_triggers])

    # Queue: processes items — scales out independently
    @app.function_name("ConnectorTriggerProcessor")
    @app.queue_trigger(
        arg_name="msg",
        queue_name=QUEUE_NAME,
        connection="AzureWebJobsStorage"
    )
    async def processor(msg: func.QueueMessage):
        payload = json.loads(msg.get_body().decode())
        instance_id = payload["instance_id"]
        item = payload["item"]

        handler = _handler_registry.get(instance_id)
        if handler is None:
            logging.warning(f"No handler for {instance_id}, dropping item")
            return

        if asyncio.iscoroutinefunction(handler):
            await handler(item)
        else:
            handler(item)
```

**Why this scales:** The timer function is always a singleton (one poller).
The queue function scales out automatically based on queue depth — Azure Functions
spins up more instances when items pile up. Each item is processed independently.

### Blob State (Per Trigger)

Each trigger gets its own blob at a well-known path:

```
Container: connector-trigger-state
Blob path: triggers/{instance_id}.json
```

Contents:
```json
{
  "cursor": "eyJMYXN0UmVjZWl2ZWRNYWlsVGltZSI6...",
  "last_poll_utc": "2026-03-10T14:00:00Z",
  "backoff_seconds": 8,
  "consecutive_empty": 3,
  "structural_hash": "abc123",
  "runtime_hash": "def456"
}
```

### Poll Logic (Per Trigger)

```python
async def _poll_trigger(trigger: TriggerRegistration):
    state = await _read_state(trigger.instance_id)

    # Config change detection
    if state and state.structural_hash != trigger.structural_hash:
        state = None  # reset — different data source
    elif state and state.runtime_hash != trigger.runtime_hash:
        state.runtime_hash = trigger.runtime_hash  # update, keep cursor

    # Backoff check — skip if not enough time has passed
    if state and state.last_poll_utc:
        elapsed = (utcnow() - state.last_poll_utc).total_seconds()
        if elapsed < state.backoff_seconds:
            return  # not due yet

    # Poll
    try:
        result = await poll_dynamic_invoke(
            connection_id=trigger.config.connection_id,
            trigger_path=trigger.config.trigger_path,
            trigger_queries=trigger.config.trigger_queries,
            cursor=state.cursor if state else None,
        )
    except ThrottledError as e:
        # Honor Retry-After
        state = state or TriggerState()
        state.backoff_seconds = max(state.backoff_seconds, e.retry_after)
        state.last_poll_utc = utcnow()
        await _save_state(trigger.instance_id, state)
        return

    # Update state
    new_state = TriggerState(
        cursor=result.cursor,
        last_poll_utc=utcnow(),
        structural_hash=trigger.structural_hash,
        runtime_hash=trigger.runtime_hash,
    )

    if result.status == 200 and result.items:
        # Enqueue each item for processing
        queue_client = get_queue_client("connector-trigger-items")
        for item in result.items:
            message = json.dumps({
                "instance_id": trigger.instance_id,
                "item": item,
            })
            await queue_client.send_message(message)

        new_state.backoff_seconds = trigger.config.min_interval
        new_state.consecutive_empty = 0
    else:
        # Exponential backoff
        prev_backoff = state.backoff_seconds if state else trigger.config.min_interval
        new_state.backoff_seconds = min(prev_backoff * 2, trigger.config.max_interval)
        new_state.consecutive_empty = (state.consecutive_empty if state else 0) + 1
        # Honor Retry-After from connector
        if result.retry_after:
            new_state.backoff_seconds = max(new_state.backoff_seconds, result.retry_after)

    await _save_state(trigger.instance_id, new_state)
```

### Blob Operations

```python
CONTAINER = "connector-trigger-state"

async def _read_state(instance_id: str) -> TriggerState | None:
    blob_client = get_blob_client(f"triggers/{instance_id}.json")
    try:
        data = await blob_client.download_blob()
        return TriggerState(**json.loads(await data.readall()))
    except ResourceNotFoundError:
        return None

async def _save_state(instance_id: str, state: TriggerState):
    blob_client = get_blob_client(f"triggers/{instance_id}.json")
    await blob_client.upload_blob(
        json.dumps(state.to_dict()),
        overwrite=True
    )
```

## Concurrency Control

### Multiple Triggers in One Timer Fire

The timer processes triggers **sequentially** within a single invocation.
This is simple and avoids concurrent writes to blob storage. If processing is
slow, triggers later in the list may be delayed — but each trigger's backoff
is independent, so they self-correct on the next timer fire.

For advanced use: process triggers concurrently with per-blob ETags for
optimistic concurrency:

```python
# Optimistic concurrency — only save if blob hasn't changed
await blob_client.upload_blob(data, overwrite=True, etag=state.etag,
                               match_condition=MatchConditions.IfNotModified)
```

### Multiple App Instances (Scale-Out)

Timer triggers are **singleton by default** — Azure Functions takes a blob lease
so only one instance runs the timer at a time across all scaled-out instances.
If a tick fires while the previous execution is still running, it's skipped.
This means:

- No overlapping timer executions
- No duplicate polling
- No need for additional distributed locking on the timer itself

Blob leases on individual trigger state blobs (Option A below) provide an
additional safety net for the rare case where the singleton lock fails.

When multiple instances fire the timer simultaneously, they'll both try to poll
the same triggers. Two options:

**Option A: Blob lease (one poller wins)**
```python
async def _poll_trigger(trigger):
    blob_client = get_blob_client(f"triggers/{trigger.instance_id}.json")
    try:
        lease = await blob_client.acquire_lease(lease_duration=60)
    except ResourceExistsError:
        return  # another instance is polling this trigger
    try:
        # ... poll and process ...
    finally:
        await lease.release()
```

**Option B: Let both poll (idempotent)**

Since the cursor is timestamp-based, two instances polling with the same cursor
get the same items. If both process the same items, the handler runs twice.
This is fine if handlers are idempotent. The second instance to save state wins
(last-writer-wins) — both cursors will be identical anyway.

**Recommendation:** Start with Option A (blob lease). Simple, prevents duplicate
processing, and the cursor-in-blob pattern naturally supports it.

## Config Change Detection

Same structural/runtime hash split as the Durable plan:

| Structural hash | Runtime hash | Action | Cursor |
|----------------|-------------|--------|--------|
| Same | Same | No-op | Preserved in blob |
| Same | Changed | Update runtime_hash in state | Preserved |
| Changed | Any | Delete old state blob | Reset (fresh start) |

No "reconciliation" step needed — each timer fire checks the hash inline.

### Orphan Cleanup

If a trigger is removed from code, its state blob stays in storage (harmless).
For cleanliness, `register_connector_triggers` can optionally clean up blobs
that don't match any registered trigger:

```python
async def _cleanup_orphan_blobs():
    desired_ids = {t.instance_id for t in _registered_triggers}
    async for blob in container_client.list_blobs(name_starts_with="triggers/"):
        blob_id = blob.name.replace("triggers/", "").replace(".json", "")
        if blob_id not in desired_ids:
            await container_client.delete_blob(blob.name)
```

Run this on startup (when `run_on_startup=True` fires), not on every timer tick.

## Backoff Behavior

Same as Durable plan, but managed via blob state:

```
timer fires (60s) → trigger A: backoff=60s, elapsed=60s → POLL → 202 → backoff=120s
timer fires (60s) → trigger A: backoff=120s, elapsed=60s → SKIP (not due yet)
timer fires (60s) → trigger A: backoff=120s, elapsed=120s → POLL → 202 → backoff=240s
...
timer fires (60s) → trigger A: backoff=300s, elapsed=300s → POLL → 200 (items!) → backoff=60s
timer fires (60s) → trigger A: backoff=60s, elapsed=60s → POLL → 202 → backoff=120s
```

The timer fires at a fixed interval (default: 60s). Each trigger independently
tracks when it was last polled and its current backoff. If the backoff hasn't
elapsed since the last poll, the trigger is skipped that tick.

**Minimum effective latency:** timer interval (default 60s). To get lower latency,
pass a faster CRON to `register_connector_triggers(app, poll_interval="*/10 * * * * *")`.

## Package Structure

```
azure_connector_triggers/
├── __init__.py              # exports decorator, register_connector_triggers
├── decorator.py             # @generic_connection_trigger + handler registry
├── registration.py          # register_connector_triggers(app) — wires up timer + queue
├── poller.py                # Timer function: poll logic, enqueue items
├── processor.py             # Queue function: look up handler, call with item
├── dynamic_invoke.py        # ARM dynamicInvoke client
├── state.py                 # Blob state read/write/lease
├── env.py                   # Env var resolution (%VAR% and $VAR syntax)
├── cleanup.py               # Orphan blob cleanup
└── models.py                # TriggerConfig, TriggerState, TriggerRegistration
```

## Comparison: Timer+Blob vs Durable

| Aspect | Timer + Blob | Durable Functions |
|--------|-------------|-------------------|
| **Dependencies** | Blob storage (already required by Functions) | Durable Task framework + storage |
| **Complexity** | Simple — one timer, blob read/write | Higher — orchestrator, activities, reconciliation |
| **Min latency** | Timer interval (10-30s) | ~2s (Durable timer resolution) |
| **Fan-out** | Queue-triggered function scales out automatically | Parallel activities across instances |
| **State** | Blob JSON (cursor + backoff) | Durable orchestration input |
| **Versioning** | No replay issues — just code runs | Non-deterministic replay risk |
| **Scale-out processing** | Blob lease = one poller | Durable distributes activities |
| **Orphan cleanup** | Delete old blobs | Terminate + purge orchestrations |
| **Recovery** | Automatic — timer fires, reads blob | Reconciliation logic needed |
| **Debugging** | Read blob to see state | Query Durable status API |

### When to Choose Timer+Blob
- Simpler deployment (no Durable dependency)
- Acceptable latency (10-30s)
- Low-to-medium throughput
- Handlers are fast (run within timer invocation timeout)

### When to Choose Durable
- Need <5s latency
- High throughput with parallel item processing
- Handlers are slow or need independent retry
- Already using Durable Functions

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Multiple instances fire timer simultaneously | Blob lease: one wins, others skip |
| Timer fires while previous still running | Skipped — singleton lock (UseMonitor=True by default) |
| Many triggers (50+) registered | Polled concurrently with semaphore (max 5 parallel), not sequential |
| Handler throws | Queue message becomes visible again, retried (built-in). Poison queue after 5 failures. |
| Handler is slow (>timer interval) | No impact — handlers run in queue function, not timer. |
| Blob storage unavailable | Timer invocation fails, retries next tick. State unchanged. |
| Config changed (structural) | Old state blob ignored/deleted, fresh cursor |
| Config changed (runtime only) | State preserved, hash updated |
| Package upgraded | Runtime hash changes, cursor preserved |
| Trigger removed from code | Orphan blob cleaned up on startup |
| Handler is slow (>timer interval) | No impact — handlers run in queue function, not timer |
| Cold start on Consumption | `runOnStartup=True` fires immediately |

## Known Limitations

1. **Minimum latency = timer interval** — Default 1 minute. Configurable via
   `register_connector_triggers(app, poll_interval="*/10 * * * * *")`.
   For near-real-time, use the Durable plan or add webhook accelerator.

2. **Queue-based processing** — Items are enqueued then processed by a separate
   queue-triggered function. This means items scale out automatically, but adds
   slight latency (queue poll interval, typically <1s). If the handler fails,
   the message returns to the queue and is retried (built-in queue retry).

3. **Handler timeout** — Handlers run in the queue function, not the timer.
   Long-running handlers don't block polling. Queue function timeout applies
   (default 5 min on Consumption, 10 min on Premium).

4. **Cursor reset on structural config change** — Same as Durable plan.

5. **Handlers must be idempotent** — Queue messages can be delivered more than
   once (at-least-once delivery). Plus duplicate delivery possible on
   crash/restart boundaries.
