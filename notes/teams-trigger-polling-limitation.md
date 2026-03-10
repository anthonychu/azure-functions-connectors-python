# Teams Trigger Polling Limitation

## Summary

The Microsoft Teams connector's batch polling triggers (e.g., `OnNewChannelMessage`,
`OnNewChannelMessageMentioningMe`) have a **connector-side bug** that prevents them from
working via `dynamicInvoke`. The trigger correctly detects new items, but then **crashes**
while computing the next cursor state, returning a 502 BadGateway error.

## Details

### Tested Trigger

- **Path:** `/trigger/beta/teams/{teamId}/channels/{channelId}/messages`
- **Connection:** Authenticated Teams API connection in Azure (westus)
- **operationId:** `OnNewChannelMessage`

### Behavior

1. **Fresh poll (no cursor):** Returns 202 Accepted with a `Location` header containing a
   `triggerState` skiptoken. No items in body. ✅
2. **Poll with cursor (no new items):** Returns 202 Accepted with updated `Location` header. ✅
3. **Poll with cursor (new items exist):** Returns **502 BadGateway** with error:
   `"Unable to compute iso trigger state."` The error body includes the actual message items
   that were found, confirming the trigger DID detect them. ❌

### Error Detail

```json
{
  "error": {
    "code": 502,
    "message": "Unable to compute iso trigger state.\nItems:\n[\n  {\n    \"replyToId\": null,\n    \"etag\": \"1773186410636\",\n    \"messageType\": \"message\",\n    \"createdDateTime\": \"2026-03-10T23:46:50.636Z\",\n    ..."
  }
}
```

The connector is finding items but failing to build the next ISO-formatted `triggerState`
cursor from the message data. This is similar to the calendar trigger's `triggerstate`
cursor issue, but in that case the fix was on our side (key casing). Here the failure is
inside the connector's internal cursor computation.

### Cursor Format

The `Location` header contains:
```
triggerState=$skiptoken~-9XhG0rwHHVc1gT8KCEuMnc1Cct4...
```

Cursor comparison across connectors:
- Office 365 email: `LastPollInformation` (ISO timestamp)
- Office 365 calendar: `triggerstate` (lowercase, ISO timestamp)
- Teams: `triggerState` (camelCase S, opaque skiptoken blob)

The cursor is correctly stored and passed back by our SDK. Both `triggerState` (original
casing) and `triggerstate` (lowercase) work for passing the cursor. The issue is the
connector's internal processing after items are found.

### Other Teams Batch Triggers

| Trigger | Status |
|---------|--------|
| `OnNewChannelMessage` | 502 when items found (cursor bug) |
| `OnNewChannelMessageMentioningMe` | Untested with actual items (likely same bug) |
| `OnGroupMembershipAdd` | Returns 404 NotFound |
| `OnGroupMembershipRemoval` | Returns 404 NotFound |

### What Works

Teams connector **actions** (non-trigger endpoints) work fine via `dynamicInvoke`:
- `GET /beta/teams` — list teams ✅
- `GET /beta/teams/{teamId}/channels` — list channels ✅
- `POST /beta/teams/{teamId}/channels/{channelId}/messages` — post message ✅
- All other action endpoints — ✅

### Workarounds

Since the connector's polling trigger is broken server-side, alternatives are:

1. **Timer + Teams client** — Use a timer function with `TeamsClient.get_messages_from_channel()`
   and track state manually (last seen message timestamp/ID). This is the simplest and uses the
   same connection. **Recommended.**
2. **Direct Graph API polling** — Use `GET /beta/teams/{teamId}/channels/{channelId}/messages/delta`
   via Microsoft Graph directly. Requires its own auth (not the connector).
3. **Webhook subscriptions** — Create webhook subscriptions via the connector's webhook trigger
   endpoints (e.g., `WebhookNewMessageTrigger`). Requires a public endpoint and subscription
   lifecycle management. Complex.

### Recommendation

- Teams support in the SDK focuses on the **client** (21 action methods) which all work correctly
- Teams trigger definitions remain in the SDK for when the connector bug is fixed
- Document the timer + client workaround as the recommended approach for Teams triggers
- The trigger code IS correct — the bug is in the Teams connector's `dynamicInvoke` response pipeline
