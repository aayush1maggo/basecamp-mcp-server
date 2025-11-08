import os
import json
from typing import Optional
from datetime import datetime
import requests
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("basecamp-mcp-tools")

# Path to token file
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")


def load_token() -> dict:
    """
    Load the access token from environment variables or token.json file.

    Priority:
    1. Environment variables (BASECAMP_ACCESS_TOKEN, etc.)
    2. token.json file

    Returns:
        Dictionary containing token information
    """
    # Try to load from environment variables first
    access_token = os.getenv("BASECAMP_ACCESS_TOKEN")
    if access_token:
        return {
            "access_token": access_token,
            "refresh_token": os.getenv("BASECAMP_REFRESH_TOKEN", ""),
            "expires_at": os.getenv("BASECAMP_TOKEN_EXPIRES_AT", ""),
            "account_id": os.getenv("BASECAMP_ACCOUNT_ID", ""),
            "source": "environment"
        }

    # Fallback to token.json file
    try:
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
            data = token_data.get("basecamp", {})
            data["source"] = "file"
            return data
    except FileNotFoundError:
        raise ValueError(
            f"No token found. Either:\n"
            f"1. Set BASECAMP_ACCESS_TOKEN environment variable, or\n"
            f"2. Provide token.json file at {TOKEN_FILE}"
        )
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in token file at {TOKEN_FILE}")


def save_token(token_data: dict) -> None:
    """
    Save updated token data to token.json file.

    Note: This only saves to file. If using environment variables,
    token refresh will work but the new token won't be persisted.

    Args:
        token_data: Dictionary containing token information
    """
    # Only save to file if we have a source field indicating file-based storage
    # or if no source is specified (backward compatibility)
    source = token_data.get("source", "file")

    if source == "environment":
        # Skip saving when using environment variables
        # The token refresh will work for the current session
        return

    # Remove source field before saving
    save_data = {k: v for k, v in token_data.items() if k != "source"}
    data = {"basecamp": save_data}

    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        # Don't fail if we can't save to file when using env vars
        if source == "file":
            raise


def refresh_access_token(refresh_token: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """
    Refresh the access token using the refresh token.

    Args:
        refresh_token: The refresh token
        client_id: OAuth client ID
        client_secret: OAuth client secret
        redirect_uri: OAuth redirect URI

    Returns:
        New token data
    """
    url = "https://launchpad.37signals.com/authorization/token"
    data = {
        "type": "refresh",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }

    response = requests.post(url, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def get_valid_token() -> str:
    """
    Get a valid access token, refreshing if necessary.

    Returns:
        Valid access token string
    """
    token_data = load_token()
    access_token = token_data.get("access_token")

    # Check if token is expired
    expires_at_str = token_data.get("expires_at")
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        if datetime.now(expires_at.tzinfo) >= expires_at:
            # Token is expired, refresh it
            client_id = os.getenv("BASECAMP_CLIENT_ID", "")
            client_secret = os.getenv("BASECAMP_CLIENT_SECRET", "")
            redirect_uri = os.getenv("BASECAMP_REDIRECT_URI", "")
            refresh_token = token_data.get("refresh_token")

            if not all([client_id, client_secret, redirect_uri, refresh_token]):
                raise ValueError("Missing OAuth credentials for token refresh")

            # Refresh the token
            new_token_data = refresh_access_token(refresh_token, client_id, client_secret, redirect_uri)

            # Update token data (preserves 'source' field)
            token_data.update({
                "access_token": new_token_data.get("access_token"),
                "refresh_token": new_token_data.get("refresh_token", refresh_token),
                "expires_at": new_token_data.get("expires_at"),
                "updated_at": datetime.now().isoformat()
            })
            save_token(token_data)  # Will only save to file if source != "environment"
            access_token = new_token_data.get("access_token")

    if not access_token:
        raise ValueError("No access token found in token.json")

    return access_token


# API Configuration
BASECAMP_ACCOUNT_ID = os.getenv("BASECAMP_ACCOUNT_ID", "")
USER_AGENT = os.getenv("USER_AGENT", "Basecamp MCP Server")

# Try to load account ID from token file if not in env
if not BASECAMP_ACCOUNT_ID:
    token_data = load_token()
    BASECAMP_ACCOUNT_ID = token_data.get("account_id", "")

if not BASECAMP_ACCOUNT_ID:
    raise ValueError("BASECAMP_ACCOUNT_ID not found in environment or token.json")

BASECAMP_API_BASE_URL = f"https://3.basecampapi.com/{BASECAMP_ACCOUNT_ID}"


def get_basecamp_headers() -> dict:
    """
    Get the required headers for Basecamp API requests.
    Automatically refreshes the token if expired.

    Returns:
        Dictionary containing authorization and user agent headers
    """
    access_token = get_valid_token()

    return {
        'Authorization': f'Bearer {access_token}',
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json'
    }


def fetch_all_pages(url: str) -> list:
    """
    Fetch all pages of a paginated Basecamp API endpoint.

    Uses the Link header to follow pagination as per Basecamp API guidelines.
    Stops when the Link header is empty.

    Args:
        url: The initial API endpoint URL

    Returns:
        List of all items from all pages combined
    """
    all_items = []
    current_url = url
    headers = get_basecamp_headers()

    while current_url:
        try:
            response = requests.get(current_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Add items from current page
            page_items = response.json()
            if isinstance(page_items, list):
                all_items.extend(page_items)
            else:
                # If single item returned, add it
                all_items.append(page_items)

            # Check for next page in Link header
            link_header = response.headers.get('Link', '')
            if link_header:
                # Parse Link header for next page URL
                # Format: <https://3.basecampapi.com/.../projects.json?page=2>; rel="next"
                parts = link_header.split(';')
                if len(parts) >= 2 and 'rel="next"' in parts[1]:
                    # Extract URL from <...>
                    next_url = parts[0].strip()[1:-1]  # Remove < and >
                    current_url = next_url
                else:
                    # No next page
                    current_url = None
            else:
                # No Link header means this is the last page
                current_url = None

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching data from Basecamp: {str(e)}")

    return all_items


@mcp.tool()
def list_projects(status: Optional[str] = None) -> str:
    """
    List all active projects visible to the current user.

    This tool fetches ALL projects using pagination, not just the first 15.
    Projects are ordered by most recently created first.

    Args:
        status: Optional filter by project status ("archived" or "trashed").
                If not provided, returns active projects.

    Returns:
        JSON string containing all projects with their details
    """
    try:
        # Build URL with optional status parameter
        url = f"{BASECAMP_API_BASE_URL}/projects.json"
        if status:
            url += f"?status={status}"

        # Fetch all pages
        projects = fetch_all_pages(url)

        # Format response
        response = {
            "total_projects": len(projects),
            "status_filter": status or "active",
            "projects": projects
        }

        return json.dumps(response, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_project(project_id: int) -> str:
    """
    Get detailed information for a specific project.

    Returns comprehensive project details including the project's dock
    (available tools like message boards, to-dos, docs, chat, etc.).

    Args:
        project_id: The ID of the project to retrieve

    Returns:
        JSON string containing detailed project information including:
        - Project metadata (id, status, name, description, purpose)
        - Dock array with enabled/disabled tools and their endpoints
        - URLs for API and web access
    """
    try:
        url = f"{BASECAMP_API_BASE_URL}/projects/{project_id}.json"
        headers = get_basecamp_headers()

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        project_data = response.json()

        return json.dumps(project_data, indent=2)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return json.dumps({
                "error": f"Project with ID {project_id} not found"
            }, indent=2)
        else:
            return json.dumps({
                "error": f"HTTP error: {str(e)}"
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_todoset(bucket_id: int, todoset_id: int) -> str:
    """
    Get a to-do set from a project.

    To-do sets are containers for organizing multiple to-do lists within a project.
    All to-do lists under a project are children of a to-do set resource.

    To find the todoset_id for a project:
    1. Use get_project() to retrieve the project details
    2. Look in the 'dock' array for the to-do list tool
    3. The todoset_id is part of the todolists_url

    Args:
        bucket_id: The project/bucket ID (same as project_id)
        todoset_id: The ID of the to-do set to retrieve

    Returns:
        JSON string containing to-do set information including:
        - Basic fields (id, status, title, name)
        - Visibility settings (visible_to_clients)
        - Statistics (completion ratio, count of to-do lists)
        - URLs (todolists_url to get all to-do lists)
        - Creator information
    """
    try:
        url = f"{BASECAMP_API_BASE_URL}/buckets/{bucket_id}/todosets/{todoset_id}.json"
        headers = get_basecamp_headers()

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        todoset_data = response.json()

        return json.dumps(todoset_data, indent=2)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return json.dumps({
                "error": f"To-do set with ID {todoset_id} not found in bucket {bucket_id}"
            }, indent=2)
        else:
            return json.dumps({
                "error": f"HTTP error: {str(e)}"
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_todolists(bucket_id: int, todoset_id: int, status: Optional[str] = None) -> str:
    """
    Get all to-do lists from a to-do set.

    This tool fetches ALL to-do lists using pagination, not just the first page.
    To-do lists are the actual lists that contain to-dos within a to-do set.

    Args:
        bucket_id: The project/bucket ID (same as project_id)
        todoset_id: The ID of the to-do set containing the lists
        status: Optional filter by status ("archived" or "trashed").
                If not provided, returns active to-do lists.

    Returns:
        JSON string containing all to-do lists with their details including:
        - List metadata (id, status, title, name)
        - Completion information (completed status, completion ratio)
        - Position within the todoset
        - Parent and bucket references
        - Creator information
        - URLs for accessing todos and groups
    """
    try:
        # Build URL with optional status parameter
        url = f"{BASECAMP_API_BASE_URL}/buckets/{bucket_id}/todosets/{todoset_id}/todolists.json"
        if status:
            url += f"?status={status}"

        # Fetch all pages
        todolists = fetch_all_pages(url)

        # Format response
        response = {
            "total_todolists": len(todolists),
            "bucket_id": bucket_id,
            "todoset_id": todoset_id,
            "status_filter": status or "active",
            "todolists": todolists
        }

        return json.dumps(response, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_todolist(bucket_id: int, todolist_id: int) -> str:
    """
    Get a single to-do list with complete details.

    Returns comprehensive information about a specific to-do list including
    all metadata, completion status, and URLs to access the todos within it.

    Args:
        bucket_id: The project/bucket ID (same as project_id)
        todolist_id: The ID of the to-do list to retrieve

    Returns:
        JSON string containing detailed to-do list information including:
        - List metadata (id, status, title, name, description)
        - Completion information (completed status, completion ratio)
        - Position and visibility settings
        - Parent todoset reference
        - Bucket/project information
        - Creator details
        - URLs for accessing todos and groups within this list
    """
    try:
        url = f"{BASECAMP_API_BASE_URL}/buckets/{bucket_id}/todolists/{todolist_id}.json"
        headers = get_basecamp_headers()

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        todolist_data = response.json()

        return json.dumps(todolist_data, indent=2)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return json.dumps({
                "error": f"To-do list with ID {todolist_id} not found in bucket {bucket_id}"
            }, indent=2)
        else:
            return json.dumps({
                "error": f"HTTP error: {str(e)}"
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_todos(bucket_id: int, todolist_id: int, status: Optional[str] = None, completed: Optional[bool] = None) -> str:
    """
    Get all to-dos from a to-do list.

    This tool fetches ALL to-dos using pagination. By default, returns active,
    pending (uncompleted) to-dos unless filters are specified.

    Args:
        bucket_id: The project/bucket ID (same as project_id)
        todolist_id: The ID of the to-do list containing the to-dos
        status: Optional filter by status ("archived" or "trashed").
                If not provided, returns active to-dos.
        completed: Optional boolean to filter by completion status.
                   Set to True to retrieve only completed to-dos.

    Returns:
        JSON string containing all to-dos with their details including:
        - To-do metadata (id, status, title, content)
        - Assignment information (assignees, completion_subscribers)
        - Completion status and data
        - Due dates and start dates
        - Parent todolist reference
        - Creator information
        - URLs for accessing and modifying the to-do
    """
    try:
        # Build URL with optional query parameters
        url = f"{BASECAMP_API_BASE_URL}/buckets/{bucket_id}/todolists/{todolist_id}/todos.json"
        params = []
        if status:
            params.append(f"status={status}")
        if completed is not None:
            params.append(f"completed={'true' if completed else 'false'}")

        if params:
            url += "?" + "&".join(params)

        # Fetch all pages
        todos = fetch_all_pages(url)

        # Format response
        response = {
            "total_todos": len(todos),
            "bucket_id": bucket_id,
            "todolist_id": todolist_id,
            "status_filter": status or "active",
            "completed_filter": completed if completed is not None else "all pending",
            "todos": todos
        }

        return json.dumps(response, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_todo(bucket_id: int, todo_id: int) -> str:
    """
    Get a single to-do with complete details.

    Returns comprehensive information about a specific to-do including
    all metadata, assignment details, completion status, and available actions.

    Args:
        bucket_id: The project/bucket ID (same as project_id)
        todo_id: The ID of the to-do to retrieve

    Returns:
        JSON string containing detailed to-do information including:
        - Basic metadata (id, status, title, description, content)
        - Visibility settings (visible_to_clients)
        - Assignment data (assignees array with person details)
        - Completion information (completed status, completion_subscriber_ids)
        - Scheduling (due_on, starts_on dates)
        - Parent todolist reference
        - Bucket/project information
        - Creator details
        - URLs for completion and modification actions
    """
    try:
        url = f"{BASECAMP_API_BASE_URL}/buckets/{bucket_id}/todos/{todo_id}.json"
        headers = get_basecamp_headers()

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        todo_data = response.json()

        return json.dumps(todo_data, indent=2)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return json.dumps({
                "error": f"To-do with ID {todo_id} not found in bucket {bucket_id}"
            }, indent=2)
        else:
            return json.dumps({
                "error": f"HTTP error: {str(e)}"
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def create_todo(
    bucket_id: int,
    todolist_id: int,
    content: str,
    description: Optional[str] = None,
    assignee_ids: Optional[list] = None,
    completion_subscriber_ids: Optional[list] = None,
    notify: Optional[bool] = None,
    due_on: Optional[str] = None,
    starts_on: Optional[str] = None
) -> str:
    """
    Create a new to-do in a to-do list.

    Args:
        bucket_id: The project/bucket ID (same as project_id)
        todolist_id: The ID of the to-do list to add the to-do to
        content: The to-do task description (required)
        description: Optional rich HTML content for detailed description
        assignee_ids: Optional list of person IDs to assign the to-do to
        completion_subscriber_ids: Optional list of person IDs to notify on completion
        notify: Optional boolean to send notifications to assignees (default: False)
        due_on: Optional due date in YYYY-MM-DD format
        starts_on: Optional start date in YYYY-MM-DD format

    Returns:
        JSON string containing the created to-do object with status 201 Created
    """
    try:
        url = f"{BASECAMP_API_BASE_URL}/buckets/{bucket_id}/todolists/{todolist_id}/todos.json"
        headers = get_basecamp_headers()

        # Build request body
        payload = {
            "content": content
        }

        if description:
            payload["description"] = description
        if assignee_ids:
            payload["assignee_ids"] = assignee_ids
        if completion_subscriber_ids:
            payload["completion_subscriber_ids"] = completion_subscriber_ids
        if notify is not None:
            payload["notify"] = notify
        if due_on:
            payload["due_on"] = due_on
        if starts_on:
            payload["starts_on"] = starts_on

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        todo_data = response.json()

        return json.dumps({
            "status": "created",
            "todo": todo_data
        }, indent=2)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return json.dumps({
                "error": f"To-do list with ID {todolist_id} not found in bucket {bucket_id}"
            }, indent=2)
        else:
            return json.dumps({
                "error": f"HTTP error: {str(e)}",
                "details": e.response.text if hasattr(e, 'response') else None
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def update_todo(
    bucket_id: int,
    todo_id: int,
    content: str,
    description: Optional[str] = None,
    assignee_ids: Optional[list] = None,
    completion_subscriber_ids: Optional[list] = None,
    notify: Optional[bool] = None,
    due_on: Optional[str] = None,
    starts_on: Optional[str] = None
) -> str:
    """
    Update an existing to-do.

    IMPORTANT: You must pass ALL existing parameters in addition to those being updated.
    Omitting a parameter will clear its value. To preserve existing values, first fetch
    the to-do with get_todo(), then pass all current values along with your changes.

    Args:
        bucket_id: The project/bucket ID (same as project_id)
        todo_id: The ID of the to-do to update
        content: The to-do task description (required, cannot be blank)
        description: Optional rich HTML content for detailed description
        assignee_ids: Optional list of person IDs to assign the to-do to
        completion_subscriber_ids: Optional list of person IDs to notify on completion
        notify: Optional boolean to send notifications to assignees
        due_on: Optional due date in YYYY-MM-DD format
        starts_on: Optional start date in YYYY-MM-DD format

    Returns:
        JSON string containing the updated to-do object with status 200 OK
    """
    try:
        url = f"{BASECAMP_API_BASE_URL}/buckets/{bucket_id}/todos/{todo_id}.json"
        headers = get_basecamp_headers()

        # Build request body
        payload = {
            "content": content
        }

        if description is not None:
            payload["description"] = description
        if assignee_ids is not None:
            payload["assignee_ids"] = assignee_ids
        if completion_subscriber_ids is not None:
            payload["completion_subscriber_ids"] = completion_subscriber_ids
        if notify is not None:
            payload["notify"] = notify
        if due_on is not None:
            payload["due_on"] = due_on
        if starts_on is not None:
            payload["starts_on"] = starts_on

        response = requests.put(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        todo_data = response.json()

        return json.dumps({
            "status": "updated",
            "todo": todo_data
        }, indent=2)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return json.dumps({
                "error": f"To-do with ID {todo_id} not found in bucket {bucket_id}"
            }, indent=2)
        else:
            return json.dumps({
                "error": f"HTTP error: {str(e)}",
                "details": e.response.text if hasattr(e, 'response') else None
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def complete_todo(bucket_id: int, todo_id: int) -> str:
    """
    Mark a to-do as completed.

    This sets the to-do's completion status to true and records who completed it
    and when. Subscribers will be notified according to the to-do's settings.

    Args:
        bucket_id: The project/bucket ID (same as project_id)
        todo_id: The ID of the to-do to complete

    Returns:
        JSON string with completion confirmation
    """
    try:
        url = f"{BASECAMP_API_BASE_URL}/buckets/{bucket_id}/todos/{todo_id}/completion.json"
        headers = get_basecamp_headers()

        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()

        return json.dumps({
            "status": "completed",
            "message": f"To-do {todo_id} has been marked as complete"
        }, indent=2)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return json.dumps({
                "error": f"To-do with ID {todo_id} not found in bucket {bucket_id}"
            }, indent=2)
        else:
            return json.dumps({
                "error": f"HTTP error: {str(e)}",
                "details": e.response.text if hasattr(e, 'response') else None
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def uncomplete_todo(bucket_id: int, todo_id: int) -> str:
    """
    Mark a to-do as uncompleted (reopen it).

    This removes the completion status from a to-do, allowing it to be worked on again.

    Args:
        bucket_id: The project/bucket ID (same as project_id)
        todo_id: The ID of the to-do to uncomplete

    Returns:
        JSON string with uncompletion confirmation
    """
    try:
        url = f"{BASECAMP_API_BASE_URL}/buckets/{bucket_id}/todos/{todo_id}/completion.json"
        headers = get_basecamp_headers()

        response = requests.delete(url, headers=headers, timeout=30)
        response.raise_for_status()

        return json.dumps({
            "status": "uncompleted",
            "message": f"To-do {todo_id} has been marked as incomplete"
        }, indent=2)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return json.dumps({
                "error": f"To-do with ID {todo_id} not found in bucket {bucket_id}"
            }, indent=2)
        else:
            return json.dumps({
                "error": f"HTTP error: {str(e)}",
                "details": e.response.text if hasattr(e, 'response') else None
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
