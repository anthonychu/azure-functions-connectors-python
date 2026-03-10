# Teams Trigger Polling Limitation

## Summary

The Microsoft Teams connector's polling triggers (e.g., `new_channel_message`, `channel_mention`)
**do not work correctly via `dynamicInvoke`**. They always return HTTP 202 with no items, and
passing the cursor (`triggerState`) back on subsequent polls causes a 500 Internal Server Error.

## Details

### Tested Trigger

- **Path:** `/trigger/beta/teams/{teamId}/channels/{channelId}/messages`
- **Connection:** Authenticated Teams API connection in Azure

### Behavior

1. **Fresh poll (no cursor):** Returns 202 Accepted with a `Location` header containing a `triggerState` skiptoken. No items in body.
2. **Poll with cursor:** Returns 500 Internal Server Error: `"Index was outside the bounds of the array."` (source: `logic-apis-westus.azure-apim.net`, path: `choose[28]\when[1]`).
3. **After posting a message:** Fresh polls still return 202 with no items.

### Cursor Format

The `Location` header contains:
```
triggerState=$skiptoken~-9XhG0rwHHVc1gT8KCEuMnc1Cct4...
```

This is different from Office 365 triggers:
- Office 365 email: `LastPollInformation` (ISO timestamp)
- Office 365 calendar: `triggerstate` (lowercase, ISO timestamp)
- Teams: `triggerState` (camelCase, skiptoken — opaque blob)

### Root Cause

The Teams connector's polling triggers appear to be designed for **webhook-style** consumption
(Logic Apps / Power Automate), not for raw polling via `dynamicInvoke`. The connector's internal
policy pipeline crashes when the skiptoken cursor is passed back as a query parameter.

### What Works

Teams connector **actions** (non-trigger endpoints) work fine via `dynamicInvoke`:
- `GET /beta/teams` — list teams ✅
- `GET /beta/teams/{teamId}/channels` — list channels ✅
- `POST /beta/teams/{teamId}/channels/{channelId}/messages` — post message ✅
- All other action endpoints — ✅

### Implication

The Teams trigger definitions in our SDK are correct in terms of path and parameter structure,
but they will not return items via the polling mechanism. If Teams triggers are needed, they
would require:

1. **Webhook subscriptions** — Creating a webhook subscription and receiving notifications at a
   public endpoint (complex, requires subscription lifecycle management).
2. **Direct Graph API polling** — Using the Microsoft Graph API directly (e.g.,
   `GET /beta/teams/{teamId}/channels/{channelId}/messages/delta`) instead of the connector.
   This bypasses the connector entirely and requires its own auth.
3. **Timer + Teams client** — Using a timer function with the Teams client to periodically call
   `get_messages_from_channel()` and track state manually. This is the simplest workaround.

### Recommendation

For now, the Teams support in the SDK focuses on the **client** (21 action methods) which all
work correctly. Teams triggers are registered but won't produce items. We should:

- Document this limitation prominently
- Consider option 3 (timer + client polling) as a documented workaround
- Revisit if Microsoft fixes the connector's polling path
