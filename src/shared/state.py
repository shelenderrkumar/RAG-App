"""State management utilities for company information bot."""

import hashlib
import uuid
from typing import Any, Literal, Optional, Union
from langchain_core.documents import Document


def _generate_uuid(page_content: str) -> str:
    """Generate UUID for document content."""
    md5_hash = hashlib.md5(page_content.encode()).hexdigest()
    return str(uuid.UUID(md5_hash))


def reduce_docs(
    existing: Optional[list[Document]], 
    new: Union[list[Document], list[dict[str, Any]], list[str], str, Literal["delete"]]
) -> list[Document]:
    """Merge document lists and maintain uniqueness by content."""
    if new == "delete":
        return []

    existing_list = list(existing) if existing else []
    if isinstance(new, str):
        return existing_list + [
            Document(page_content=new, metadata={"uuid": _generate_uuid(new)})
        ]

    new_list = []
    if isinstance(new, list):
        existing_ids = set(doc.metadata.get("uuid") for doc in existing_list)
        for item in new:
            if isinstance(item, str):
                item_id = _generate_uuid(item)
                new_list.append(Document(page_content=item, metadata={"uuid": item_id}))
            elif isinstance(item, dict):
                metadata = item.get("metadata", {})
                item_id = metadata.get("uuid") or _generate_uuid(item.get("page_content", ""))
                if item_id not in existing_ids:
                    new_list.append(Document(**{**item, "metadata": {**metadata, "uuid": item_id}}))
            elif isinstance(item, Document):
                item_id = item.metadata.get("uuid", "") or _generate_uuid(item.page_content)
                if item_id not in existing_ids:
                    new_item = item.copy(deep=True)
                    new_item.metadata["uuid"] = item_id
                    new_list.append(new_item)
                existing_ids.add(item_id)

    return existing_list + new_list