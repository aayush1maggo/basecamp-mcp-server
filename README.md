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

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Basecamp credentials:
```bash
cp .env.example .env
```

3. Get your Basecamp credentials:
   - **Access Token**: Visit https://launchpad.37signals.com/integrations
   - **Account ID**: Find it in your Basecamp URL (https://3.basecamp.com/YOUR_ACCOUNT_ID)

4. Update `.env` with your credentials:
```
BASECAMP_ACCOUNT_ID=1234567890
BASECAMP_ACCESS_TOKEN=your_token_here
```

## Running the Server

```bash
python server.py
```

The server runs using stdio transport, suitable for MCP client integration.

## Pagination

The server automatically handles Basecamp's pagination by:
- Following the `Link` header for next pages (as per Basecamp API guidelines)
- Aggregating results from all pages
- Stopping when the `Link` header is empty (last page reached)

This ensures you get ALL projects, not just the first 15 returned by the API.

## API Documentation

Based on [Basecamp 4 API Documentation](https://github.com/basecamp/bc3-api)
