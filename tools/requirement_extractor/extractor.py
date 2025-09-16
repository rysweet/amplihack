"""
Extractor module for extracting requirements using AI
"""
import asyncio
import json
import uuid
from typing import List, Optional
from datetime import datetime
from .models import CodeModule, Requirement, ModuleRequirements

# Try to import Claude SDK, but make it optional
try:
    from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    print("Warning: Claude Code SDK not available. Install with: pip install claude-code-sdk")


class RequirementsExtractor:
    """Extracts functional requirements from code modules using AI"""

    def __init__(self, timeout_seconds: int = 120):
        self.timeout_seconds = timeout_seconds

    async def extract_requirements(self, module: CodeModule) -> ModuleRequirements:
        """Extract requirements from a code module"""
        module_reqs = ModuleRequirements(
            module_name=module.name,
            requirements=[],
            extraction_status="processing"
        )

        try:
            # Prepare code context
            code_context = self._prepare_code_context(module)

            # Extract using AI
            requirements = await self._extract_with_ai(code_context, module.name)

            module_reqs.requirements = requirements
            module_reqs.extraction_status = "completed"

        except asyncio.TimeoutError:
            module_reqs.extraction_status = "failed"
            module_reqs.error_message = f"Extraction timed out after {self.timeout_seconds} seconds"
        except Exception as e:
            module_reqs.extraction_status = "failed"
            module_reqs.error_message = str(e)

        return module_reqs

    def _prepare_code_context(self, module: CodeModule) -> str:
        """Prepare code context for AI extraction"""
        context_parts = [
            f"Module: {module.name}",
            f"Description: {module.description}",
            f"Primary Language: {module.primary_language}",
            "",
            "Files in module:"
        ]

        # Include file list and snippets
        for file in module.files[:10]:  # Limit to first 10 files for context
            context_parts.append(f"  - {file.relative_path} ({file.lines} lines)")

        # Read a sample of actual code
        context_parts.append("\nCode samples:")
        for file in module.files[:3]:  # Read first 3 files
            try:
                with open(file.path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[:50]  # First 50 lines
                    context_parts.append(f"\n--- {file.relative_path} ---")
                    context_parts.append("".join(lines))
            except Exception:
                continue

        return "\n".join(context_parts)

    async def _extract_with_ai(self, code_context: str, module_name: str) -> List[Requirement]:
        """Extract requirements using AI"""
        if not CLAUDE_SDK_AVAILABLE:
            # Fallback: Generate basic requirements without AI
            return self._generate_basic_requirements(module_name)

        try:
            async with asyncio.timeout(self.timeout_seconds):
                return await self._claude_sdk_extraction(code_context, module_name)
        except asyncio.TimeoutError:
            print(f"Claude SDK timeout for module {module_name}")
            return self._generate_basic_requirements(module_name)
        except Exception as e:
            print(f"Claude SDK error for module {module_name}: {e}")
            return self._generate_basic_requirements(module_name)

    async def _claude_sdk_extraction(self, code_context: str, module_name: str) -> List[Requirement]:
        """Extract requirements using Claude SDK"""
        prompt = f"""Analyze the following code module and extract functional requirements.

{code_context}

Extract functional requirements in the following JSON format ONLY (no markdown):
{{
    "requirements": [
        {{
            "title": "Brief requirement title",
            "description": "Detailed description of what the code does",
            "category": "Category like API, Data, UI, etc",
            "priority": "high/medium/low based on importance",
            "evidence": ["Code patterns or functions that implement this"]
        }}
    ]
}}

Focus on:
1. What functionality the code provides
2. Business logic and rules
3. Data processing and transformations
4. API endpoints and interfaces
5. User interactions

Return ONLY valid JSON, no markdown formatting."""

        response = ""
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt="You are a requirements analyst extracting functional requirements from code.",
                max_turns=1,
            )
        ) as client:
            await client.query(prompt)

            async for message in client.receive_response():
                if hasattr(message, "content"):
                    content = getattr(message, "content", [])
                    if isinstance(content, list):
                        for block in content:
                            if hasattr(block, "text"):
                                response += getattr(block, "text", "")

        # Parse response
        requirements = []
        if response:
            try:
                # Strip markdown if present
                cleaned = response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                data = json.loads(cleaned)
                for idx, req_data in enumerate(data.get("requirements", [])):
                    req = Requirement(
                        id=f"{module_name}_{idx+1}",
                        title=req_data.get("title", "Untitled"),
                        description=req_data.get("description", ""),
                        category=req_data.get("category", "General"),
                        priority=req_data.get("priority", "medium"),
                        source_modules=[module_name],
                        evidence=req_data.get("evidence", []),
                        confidence=0.8
                    )
                    requirements.append(req)
            except json.JSONDecodeError as e:
                print(f"Failed to parse AI response for {module_name}: {e}")

        return requirements

    def _generate_basic_requirements(self, module_name: str) -> List[Requirement]:
        """Generate basic requirements without AI (fallback)"""
        return [
            Requirement(
                id=f"{module_name}_1",
                title=f"{module_name} Module Functionality",
                description=f"Provides functionality for {module_name}",
                category="General",
                priority="medium",
                source_modules=[module_name],
                evidence=[],
                confidence=0.3
            )
        ]