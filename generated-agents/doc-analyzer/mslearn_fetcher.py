"""
Microsoft Learn Documentation Fetcher

Fetches and parses documentation from Microsoft Learn.
"""

import re

import requests
from bs4 import BeautifulSoup


class MSLearnFetcher:
    """
    Fetches documentation from Microsoft Learn and extracts markdown content.

    Microsoft Learn pages typically have a main content area with article text.
    This fetcher extracts that content and converts it to a clean markdown format.
    """

    BASE_URL = "https://learn.microsoft.com"
    USER_AGENT = "Mozilla/5.0 (compatible; DocAnalyzer/1.0)"

    def __init__(self, timeout: int = 30):
        """
        Initialize the fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            }
        )

    def fetch_document(self, url: str) -> str | None:
        """
        Fetch a Microsoft Learn document and extract its markdown content.

        Args:
            url: Full URL to the Microsoft Learn document

        Returns:
            Markdown content as string, or None if fetch failed
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract main content
            content = self._extract_content(soup)

            if not content:
                return None

            # Convert to markdown
            markdown = self._html_to_markdown(content)

            return markdown

        except requests.RequestException as e:
            print(f"Error fetching document: {e}")
            return None
        except Exception as e:
            print(f"Error processing document: {e}")
            return None

    def _extract_content(self, soup: BeautifulSoup) -> BeautifulSoup | None:
        """
        Extract the main content area from the page.

        Microsoft Learn uses various selectors for the main content:
        - main element
        - article element
        - div with specific classes
        """
        # Try common content selectors
        content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=re.compile(r"content|article|main", re.I))
        )

        return content

    def _html_to_markdown(self, content: BeautifulSoup) -> str:
        """
        Convert HTML content to markdown.

        This is a simple converter that handles common elements.
        For production use, consider using a library like html2text.
        """
        lines = []

        for element in content.descendants:
            if element.name == "h1":
                lines.append(f"\n# {element.get_text().strip()}\n")
            elif element.name == "h2":
                lines.append(f"\n## {element.get_text().strip()}\n")
            elif element.name == "h3":
                lines.append(f"\n### {element.get_text().strip()}\n")
            elif element.name == "h4":
                lines.append(f"\n#### {element.get_text().strip()}\n")
            elif element.name == "h5":
                lines.append(f"\n##### {element.get_text().strip()}\n")
            elif element.name == "h6":
                lines.append(f"\n###### {element.get_text().strip()}\n")
            elif element.name == "p":
                text = element.get_text().strip()
                if text:
                    lines.append(f"{text}\n")
            elif element.name == "code":
                if element.parent.name == "pre":
                    # Code block
                    lines.append(f"\n```\n{element.get_text()}\n```\n")
                else:
                    # Inline code
                    lines.append(f"`{element.get_text()}`")
            elif element.name == "a":
                text = element.get_text().strip()
                href = element.get("href", "")
                if text and href:
                    lines.append(f"[{text}]({href})")
            elif element.name in ("ul", "ol"):
                # Skip - we'll handle list items directly
                pass
            elif element.name == "li":
                text = element.get_text().strip()
                if text:
                    lines.append(f"- {text}\n")

        # Clean up the output
        markdown = "".join(lines)

        # Remove excessive blank lines
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        return markdown.strip()

    def fetch_multiple(self, urls: list[str]) -> dict[str, str | None]:
        """
        Fetch multiple documents.

        Args:
            urls: List of URLs to fetch

        Returns:
            Dictionary mapping URLs to their markdown content
        """
        results = {}
        for url in urls:
            print(f"Fetching: {url}")
            content = self.fetch_document(url)
            results[url] = content

        return results


# Sample Microsoft Learn URLs for testing
SAMPLE_DOCS = [
    "https://learn.microsoft.com/en-us/azure/architecture/guide/",
    "https://learn.microsoft.com/en-us/dotnet/core/introduction",
    "https://learn.microsoft.com/en-us/python/api/overview/azure/",
]


def get_sample_markdown() -> str:
    """
    Return sample markdown for testing without network access.

    This simulates a typical Microsoft Learn document structure.
    """
    return """# Azure Architecture Guide

## Overview

The Azure Architecture Center provides guidance for designing cloud solutions on Azure. This guide helps you build secure, scalable, and reliable applications.

## Prerequisites

Before you begin, ensure you have:

- An Azure subscription
- Basic understanding of cloud concepts
- Familiarity with Azure services

## Key Concepts

### Cloud Design Patterns

Cloud design patterns are reusable solutions to common problems in cloud architecture. These patterns help you build more resilient and maintainable applications.

### Scalability

Azure provides multiple options for scaling applications:

- **Vertical scaling**: Increase the size of individual resources
- **Horizontal scaling**: Add more instances of resources

## Best Practices

1. Design for failure
2. Use managed services when possible
3. Implement proper monitoring
4. Follow security best practices

## Code Example

Here's a basic example of deploying a resource:

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

credential = DefaultAzureCredential()
client = ResourceManagementClient(credential, subscription_id)
```

## Next Steps

- [Learn about microservices](https://example.com/microservices)
- [Explore reference architectures](https://example.com/architectures)
- [Review security guidelines](https://example.com/security)

## Additional Resources

For more information, see:

- [Azure documentation](https://docs.microsoft.com/azure)
- [Architecture patterns](https://example.com/patterns)
- [Community forums](https://example.com/community)
"""
