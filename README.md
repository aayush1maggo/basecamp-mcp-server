# Basecamp MCP Server

An MCP server built with FastMCP 2.0 that provides tools to interact with the Basecamp API.

## Features

- **List All Projects**: Fetches ALL active projects using automatic pagination (not just the first 15)
- **Get Single Project**: Retrieve detailed information about a specific project including its dock (available tools)

## Tools

### `list_projects`
Lists all active projects visible to the current user with full pagination support.

**Parameters:**
- `status` (optional): Filter by project status ("archived" or "trashed"). Defaults to active projects.

**Returns:** JSON containing all projects with metadata

### `get_project`
Gets detailed information for a specific project.

**Parameters:**
- `project_id` (required): The ID of the project to retrieve

**Returns:** JSON containing comprehensive project details including the dock (message boards, to-dos, docs, chat, etc.)

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
