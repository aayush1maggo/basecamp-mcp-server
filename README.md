# Basecamp MCP Server

An MCP server built with FastMCP 2.0 that provides tools to interact with the Basecamp API.

## Features

- **Project Discovery**: List every visible Basecamp project with automatic pagination (no 15-item cap)
- **Project Detail View**: Fetch a single project including its dock metadata and tool endpoints
- **To-do Overview**: Browse to-do sets and lists with the same pagination support used for projects
- **Task Drill-down**: Inspect individual to-do lists and tasks with rich metadata, assignments, and scheduling
- **Task Creation**: Create new to-dos with optional assignees, subscribers, due dates, and notification control

## Tools

### `list_projects`
Lists all projects visible to the authenticated user using full pagination so you never miss items.

**Parameters**
- `status` (optional): Filter projects by status; accepts `archived` or `trashed`. Defaults to active.

**Returns** JSON payload with `total_projects`, the applied filter, and the full project list.

### `get_project`
Fetches a single project, including dock information that reveals which Basecamp tools are enabled.

**Parameters**
- `project_id` (required): Numeric ID of the project.

**Returns** JSON blob mirroring the Basecamp API response with metadata, dock entries, and URLs.

### `get_todoset`
Retrieves a to-do set for a given project (bucket). Use this to discover the to-do lists available within the set.

**Parameters**
- `bucket_id` (required): Project or bucket ID (same as `project_id`).
- `todoset_id` (required): ID of the to-do set, obtainable from `get_project`.

**Returns** JSON object with to-do set metadata, statistics, and URLs for downstream queries.

### `get_todolists`
Lists all to-do lists within a to-do set with pagination handled automatically.

**Parameters**
- `bucket_id` (required): Project/bucket ID.
- `todoset_id` (required): To-do set ID.
- `status` (optional): Filter lists by `archived` or `trashed`. Defaults to active.

**Returns** JSON payload with counts, filters, and the full list collection.

### `get_todolist`
Fetches a single to-do list with complete metadata and navigation links.

**Parameters**
- `bucket_id` (required): Project/bucket ID.
- `todolist_id` (required): ID of the list.

**Returns** JSON object describing the list, completion info, parent references, and URLs.

### `get_todos`
Retrieves every to-do within a list, supporting status and completion filters.

**Parameters**
- `bucket_id` (required): Project/bucket ID.
- `todolist_id` (required): ID of the parent list.
- `status` (optional): Filter by `archived` or `trashed`.
- `completed` (optional): `true` for completed tasks, `false` for pending.

**Returns** JSON payload with totals, filters, and all matching to-dos.

### `get_todo`
Gets a single to-do with full detail, including assignments, visibility, scheduling, and action URLs.

**Parameters**
- `bucket_id` (required): Project/bucket ID.
- `todo_id` (required): ID of the to-do.

**Returns** JSON object reflecting the Basecamp to-do schema.

### `create_todo`
Creates a new to-do inside a list, supporting optional metadata aligned with Basecamp’s API.

**Parameters**
- `bucket_id` (required): Project/bucket ID.
- `todolist_id` (required): Destination list ID.
- `content` (required): Task title/summary.
- `description` (optional): Rich HTML description.
- `assignee_ids` (optional): List of person IDs to assign.
- `completion_subscriber_ids` (optional): People to notify on completion.
- `notify` (optional): Boolean to trigger assignment notifications.
- `due_on` (optional): Due date in `YYYY-MM-DD`.
- `starts_on` (optional): Start date in `YYYY-MM-DD`.

**Returns** JSON payload including the created to-do data and status marker.

## Setup

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Basecamp credentials:
```bash
cp .env.example .env
```

3. Get your Basecamp credentials:
   - **OAuth App**: Create at https://launchpad.37signals.com/integrations
   - **Account ID**: Find it in your Basecamp URL (https://3.basecamp.com/YOUR_ACCOUNT_ID)

4. Configure authentication using **one of two methods**:

   **Method A: token.json file** (recommended for local)
   - Obtain OAuth tokens through the OAuth flow
   - Create `token.json` with the following structure:
   ```json
   {
     "basecamp": {
       "access_token": "your_access_token",
       "refresh_token": "your_refresh_token",
       "expires_at": "2025-12-31T23:59:59Z",
       "account_id": "your_account_id"
     }
   }
   ```

   **Method B: Environment variables** (recommended for cloud deployment)
   - Set these in your `.env` file:
   ```
   BASECAMP_ACCESS_TOKEN=your_access_token_here
   BASECAMP_REFRESH_TOKEN=your_refresh_token_here
   BASECAMP_TOKEN_EXPIRES_AT=2025-12-31T23:59:59Z
   BASECAMP_ACCOUNT_ID=your_account_id_here
   BASECAMP_CLIENT_ID=your_client_id
   BASECAMP_CLIENT_SECRET=your_client_secret
   BASECAMP_REDIRECT_URI=your_redirect_uri
   USER_AGENT="Your App Name (your@email.com)"
   ```

### FastMCP Cloud Deployment

For FastMCP Cloud, use environment variables only:

**Required Environment Variables:**
```
BASECAMP_ACCESS_TOKEN=your_access_token
BASECAMP_REFRESH_TOKEN=your_refresh_token
BASECAMP_TOKEN_EXPIRES_AT=2025-12-31T23:59:59Z
BASECAMP_ACCOUNT_ID=your_account_id
BASECAMP_CLIENT_ID=your_oauth_client_id
BASECAMP_CLIENT_SECRET=your_oauth_client_secret
BASECAMP_REDIRECT_URI=your_redirect_uri
USER_AGENT="Your App Name (your@email.com)"
```

The server will automatically refresh tokens when they expire (as long as OAuth credentials are provided).

## Running the Server

```bash
python server.py
```

The server runs using **HTTP transport** on `http://0.0.0.0:8000`, suitable for FastMCP Cloud deployment.

**Note:** If you need stdio transport for local MCP client integration (e.g., Claude Desktop), change line 604 in `server.py`:
```python
# For FastMCP Cloud (current):
mcp.run(transport="http", host="0.0.0.0", port=8000)

# For local MCP client:
mcp.run(transport="stdio")
```

## Pagination

The server automatically handles Basecamp's pagination by:
- Following the `Link` header for next pages (as per Basecamp API guidelines)
- Aggregating results from all pages
- Stopping when the `Link` header is empty (last page reached)

This ensures you get ALL projects, not just the first 15 returned by the API.

## API Documentation

Based on [Basecamp 4 API Documentation](https://github.com/basecamp/bc3-api)
