"""Custom exceptions for Neo4j memory system."""


class Neo4jConnectionError(Exception):
    """Raised when cannot connect to Neo4j database."""


class Neo4jContainerError(Exception):
    """Raised when Docker container operations fail."""


class Neo4jConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""


class Neo4jSchemaError(Exception):
    """Raised when schema initialization or verification fails."""


class Neo4jPrerequisiteError(Exception):
    """Raised when prerequisites (Docker, etc.) are not met."""
