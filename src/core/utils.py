import re


def sanitize_filename(name: str) -> str:
    """
    Removes invalid characters for file systems and prevents directory traversal.
    """
    if not name:
        return ""
    # Remove control characters
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    # Prevent path traversal: Replace '..' with '_'
    while ".." in name:
        name = name.replace("..", "_")
    # Remove path traversal and invalid chars: / \ : * ? " < > |
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    # Remove leading/trailing dots or spaces
    name = name.strip(". ")
    # Truncate to reasonable length (e.g., 100 chars) to avoid OS limits
    return name[:100]


def sanitize_fts_query(query: str) -> str:
    """
    Escapes special FTS5 characters to prevent OperationalError.
    Characters: " * : ^
    """
    if not query:
        return ""
    # FTS5 special characters need to be handled carefully.
    # Simple strategy: remove them or escape them if we want to allow complex queries.
    # For now, we'll remove them or enclose the whole thing in quotes if it's not complex.
    # But for a simple keyword search, removing them is safer.
    return re.sub(r'[*":^]', " ", query).strip()
