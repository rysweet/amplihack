"""Database service for data persistence."""

from typing import Any


class DatabaseService:
    """Service for database operations.

    Provides a simple in-memory database for testing.
    In production, this would connect to a real database.
    """

    def __init__(self):
        """Initialize database service."""
        self.data: dict[str, list[dict[str, Any]]] = {}

    def query(self, table: str, criteria: dict[str, Any]) -> dict[str, Any] | None:
        """Query for a single record.

        Args:
            table: Table name
            criteria: Query criteria

        Returns:
            First matching record or None
        """
        if table not in self.data:
            return None

        for record in self.data[table]:
            if all(record.get(k) == v for k, v in criteria.items()):
                return record

        return None

    def query_all(self, table: str, limit: int = 100) -> list[dict[str, Any]]:
        """Query all records from a table.

        Args:
            table: Table name
            limit: Maximum records to return

        Returns:
            List of records
        """
        if table not in self.data:
            return []

        return self.data[table][:limit]

    def insert(self, table: str, record: dict[str, Any]) -> bool:
        """Insert a record.

        Args:
            table: Table name
            record: Record data

        Returns:
            True if successful
        """
        if table not in self.data:
            self.data[table] = []

        self.data[table].append(record)
        return True

    def update(self, table: str, criteria: dict[str, Any], updates: dict[str, Any]) -> bool:
        """Update records matching criteria.

        Args:
            table: Table name
            criteria: Query criteria
            updates: Fields to update

        Returns:
            True if any records updated
        """
        if table not in self.data:
            return False

        updated = False
        for record in self.data[table]:
            if all(record.get(k) == v for k, v in criteria.items()):
                record.update(updates)
                updated = True

        return updated

    def delete(self, table: str, criteria: dict[str, Any]) -> bool:
        """Delete records matching criteria.

        Args:
            table: Table name
            criteria: Query criteria

        Returns:
            True if any records deleted
        """
        if table not in self.data:
            return False

        original_count = len(self.data[table])
        self.data[table] = [
            record
            for record in self.data[table]
            if not all(record.get(k) == v for k, v in criteria.items())
        ]

        return len(self.data[table]) < original_count
