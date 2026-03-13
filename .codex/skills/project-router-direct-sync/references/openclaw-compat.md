# OpenClaw Compatibility Notes

This skill is derived from the public `voicenotes-official` OpenClaw skill and the VoiceNotes help article about connecting VoiceNotes to OpenClaw.

## Auth

- Environment variable: `VOICENOTES_API_KEY`
- Header:

```http
Authorization: <VOICENOTES_API_KEY>
```

## Base URL

```text
https://api.voicenotes.com/api/integrations/open-claw
```

## Endpoints

### Search notes semantically

```http
GET /search/semantic?query=<query>
```

Returns a relevance-ordered array with `note`, `note_split`, or `import_split`.

### List recordings with filters

```http
POST /recordings
Content-Type: application/json
```

Request body fields:

- `tags`: optional string array
- `date_range`: optional two-item array `[start_iso, end_iso]`

Response shape:

```json
{
  "data": [],
  "links": {
    "next": null
  },
  "meta": {
    "current_page": 1
  }
}
```

### Get a full transcript

```http
GET /recordings/{recording_uuid}
```

### Create a text note

```http
POST /recordings/new
Content-Type: application/json
```

Payload:

```json
{
  "recording_type": 3,
  "transcript": "note content here",
  "device_info": "codex"
}
```

## Important Caveats

- `import_split` results come from imported files and may not be retrievable through `GET /recordings/{uuid}`.
- `transcript` content may contain HTML such as `<br>` or `<b>`.
- This compatibility layer is useful for Codex, but the API surface is documented publicly through the OpenClaw integration rather than as a separate first-class Codex integration.
