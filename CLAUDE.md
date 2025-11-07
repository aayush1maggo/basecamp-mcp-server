# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server built with FastMCP 2.0 that provides tools to interact with the Basecamp API. The server runs using stdio transport and is designed to be integrated with MCP clients.

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Running the Server
```bash
python server.py
```

The server uses stdio transport for MCP client integration.

## Authentication Architecture

The server uses **OAuth 2.0 with automatic token refresh**:

1. **Token Storage**: Access tokens are stored in `token.json` (not `.env`)
2. **Token Format**: `token.json` structure:
   ```json
   {
     "basecamp": {
       "access_token": "...",
       "refresh_token": "...",
       "expires_at": "ISO8601 timestamp",
       "account_id": "..."
     }
   }
   ```
3. **Automatic Refresh**: The `get_valid_token()` function (server.py:75-115) automatically refreshes expired tokens using the OAuth refresh token flow
4. **Fallback Configuration**: Account ID can be read from either `.env` or `token.json`

### Token Lifecycle
- Every API call goes through `get_basecamp_headers()` (server.py:133-147)
- `get_valid_token()` checks token expiration before each use
- If expired, automatically calls `refresh_access_token()` (server.py:48-72)
- New tokens are saved back to `token.json` with updated timestamps

## API Architecture

### Pagination Pattern
All list-based tools use `fetch_all_pages()` (server.py:150-200) which:
- Follows Basecamp's `Link` header for pagination
- Parses `Link: <url>; rel="next"` headers
- Aggregates all pages automatically
- Stops when `Link` header is absent (last page)
- Returns complete result sets, not just first 15 items

This ensures tools like `list_projects()` and `get_todolists()` return ALL items, not just the first page.

### Tool Implementation Pattern
All MCP tools follow this structure:
1. Build URL with optional query parameters
2. Use `fetch_all_pages()` for list endpoints or direct `requests.get()` for single items
3. Get headers via `get_basecamp_headers()` (which handles token refresh)
4. Return JSON strings with formatted responses
5. Handle errors with descriptive JSON error messages

### Resource Hierarchy
Basecamp resources follow this hierarchy:
- **Projects** (also called "buckets")
  - **Dock**: Container for project tools (message boards, to-dos, docs, chat)
    - **Todoset**: Container for all to-do lists in a project
      - **Todolist**: Individual to-do lists
        - **Todo**: Individual to-do items (not yet implemented)

To navigate from project to todos:
1. `get_project(project_id)` → get dock array
2. Find to-do tool in dock → extract `todoset_id` from `todolists_url`
3. `get_todoset(bucket_id, todoset_id)` → get todoset details
4. `get_todolists(bucket_id, todoset_id)` → get all lists
5. `get_todolist(bucket_id, todolist_id)` → get specific list details

## Configuration

### Required Files
- `.env`: OAuth credentials and account configuration (use `.env.example` as template)
- `token.json`: OAuth access/refresh tokens (generated after initial OAuth flow)

### Environment Variables
- `BASECAMP_CLIENT_ID`: OAuth app client ID
- `BASECAMP_CLIENT_SECRET`: OAuth app client secret
- `BASECAMP_REDIRECT_URI`: OAuth callback URL
- `BASECAMP_ACCOUNT_ID`: Basecamp account ID (found in URL: 3.basecamp.com/ACCOUNT_ID)
- `USER_AGENT`: Required by Basecamp API (format: "App Name (email)")

## Current Tool Coverage

Implemented tools:
- `list_projects`: List all projects with pagination
- `get_project`: Get single project with dock details
- `get_todoset`: Get to-do set container
- `get_todolists`: List all to-do lists in a set
- `get_todolist`: Get single to-do list details

Not yet implemented (reference API docs):
- Individual to-dos (GET/POST/PUT/DELETE)
- To-do groups
- Message boards and messages
- Documents and files
- Chat/Campfire
- Schedule entries
- Webhooks
