"""
Prompt Coordination Interface for Auto-Mode

Manages prompt templates, context injection, and coordination between
separated prompts and Claude Agent SDK calls for auto-mode functionality.
"""

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import BaseLoader, Environment, TemplateNotFound

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """Types of prompts in auto-mode system"""

    OBJECTIVE_CLARIFICATION = "objective_clarification"
    PROGRESS_ASSESSMENT = "progress_assessment"
    NEXT_ACTION = "next_action"
    ERROR_RESOLUTION = "error_resolution"
    QUALITY_REVIEW = "quality_review"
    WORKFLOW_COORDINATION = "workflow_coordination"


@dataclass
class PromptTemplate:
    """A reusable prompt template"""

    id: str
    name: str
    type: PromptType
    template_content: str
    required_variables: List[str]
    optional_variables: List[str]
    description: str
    metadata: Dict[str, Any]


@dataclass
class PromptContext:
    """Context data for prompt rendering"""

    session_id: str
    user_objective: str
    working_directory: str
    current_step: int
    total_steps: int
    previous_outputs: List[str]
    analysis_results: List[Dict[str, Any]]
    workflow_state: Dict[str, Any]
    custom_variables: Dict[str, Any]


@dataclass
class RenderedPrompt:
    """A rendered prompt ready for execution"""

    id: str
    template_id: str
    type: PromptType
    content: str
    context_snapshot: Dict[str, Any]
    validation_status: str  # "valid", "warning", "error"
    validation_messages: List[str]
    timestamp: datetime


class PromptValidationError(Exception):
    """Raised when prompt validation fails"""

    pass


class TemplateRenderError(Exception):
    """Raised when template rendering fails"""

    pass


class PromptTemplateLoader(BaseLoader):
    """Custom Jinja2 loader for prompt templates"""

    def __init__(self, templates: Dict[str, PromptTemplate]):
        self.templates = templates

    def get_source(self, environment, template):
        if template in self.templates:
            source = self.templates[template].template_content
            return source, None, lambda: True
        raise TemplateNotFound(template)


class PromptCoordinator:
    """
    Coordinates prompt templates and context injection for auto-mode.

    Manages template loading, context injection, prompt validation,
    and coordination with Claude Agent SDK calls.
    """

    def __init__(self, templates_dir: Optional[str] = None):
        self.templates: Dict[str, PromptTemplate] = {}
        self.rendered_prompts: Dict[str, RenderedPrompt] = {}
        self.context_history: List[PromptContext] = []

        # Set up Jinja2 environment
        self.jinja_loader = PromptTemplateLoader(self.templates)
        self.jinja_env = Environment(loader=self.jinja_loader)

        # Load default templates
        self._load_default_templates()

        # Load custom templates if directory provided
        if templates_dir:
            self._load_templates_from_directory(templates_dir)

    def _load_default_templates(self) -> None:
        """Load built-in default templates"""

        default_templates = [
            PromptTemplate(
                id="objective_clarification",
                name="Objective Clarification",
                type=PromptType.OBJECTIVE_CLARIFICATION,
                template_content="""
I need to clarify the objective for auto-mode operation.

User's Original Objective: {{ user_objective }}

Current Working Directory: {{ working_directory }}
Session ID: {{ session_id }}

{% if previous_outputs %}
Previous outputs to consider:
{% for output in previous_outputs[-3:] %}
Output {{ loop.index }}:
{{ output[:500] }}...
{% endfor %}
{% endif %}

Please help me understand:
1. What specifically needs to be accomplished?
2. What are the success criteria?
3. What constraints or requirements should I be aware of?
4. Are there any preferences for approach or methodology?

Provide a clear, actionable breakdown of what we need to achieve.
""".strip(),
                required_variables=["user_objective", "working_directory", "session_id"],
                optional_variables=["previous_outputs"],
                description="Clarifies user objectives for auto-mode",
                metadata={"priority": "high", "category": "initialization"},
            ),
            PromptTemplate(
                id="progress_assessment",
                name="Progress Assessment",
                type=PromptType.PROGRESS_ASSESSMENT,
                template_content="""
Let me assess our progress toward the objective.

Objective: {{ user_objective }}
Current Step: {{ current_step }} of {{ total_steps }}
Working Directory: {{ working_directory }}

{% if analysis_results %}
Recent Analysis Results:
{% for result in analysis_results[-2:] %}
- {{ result.get('findings', ['No findings'])[0] }}
- Confidence: {{ result.get('confidence', 0) }}
{% endfor %}
{% endif %}

{% if previous_outputs %}
Recent Work Completed:
{{ previous_outputs[-1][:800] }}
{% endif %}

Please evaluate:
1. What progress have we made toward the objective?
2. What has been accomplished successfully?
3. What challenges or blockers have emerged?
4. How confident are you in the current approach?
5. What adjustments might improve our trajectory?

Provide specific recommendations for next steps.
""".strip(),
                required_variables=[
                    "user_objective",
                    "current_step",
                    "total_steps",
                    "working_directory",
                ],
                optional_variables=["analysis_results", "previous_outputs"],
                description="Evaluates progress against objectives",
                metadata={"priority": "high", "category": "assessment"},
            ),
            PromptTemplate(
                id="next_action",
                name="Next Action Generation",
                type=PromptType.NEXT_ACTION,
                template_content="""
Based on our current progress, let's determine the next action.

Objective: {{ user_objective }}
Current State: Step {{ current_step }} of {{ total_steps }}

{% if workflow_state %}
Workflow Status:
{% for key, value in workflow_state.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

{% if analysis_results and analysis_results[-1] %}
Latest Analysis Recommendations:
{% for rec in analysis_results[-1].get('recommendations', []) %}
- {{ rec }}
{% endfor %}
{% endif %}

Context from recent work:
{{ previous_outputs[-1][:600] if previous_outputs else "No previous outputs available" }}

Please provide:
1. The specific next action to take
2. Why this action is the logical next step
3. Expected outcomes from this action
4. Any risks or considerations
5. Success criteria for this action

Make your recommendation concrete and actionable.
""".strip(),
                required_variables=["user_objective", "current_step", "total_steps"],
                optional_variables=["workflow_state", "analysis_results", "previous_outputs"],
                description="Generates next actionable steps",
                metadata={"priority": "high", "category": "action"},
            ),
            PromptTemplate(
                id="error_resolution",
                name="Error Resolution",
                type=PromptType.ERROR_RESOLUTION,
                template_content="""
An error or issue needs resolution.

Objective: {{ user_objective }}
Working Directory: {{ working_directory }}

{% if error_details %}
Error Details:
{{ error_details }}
{% endif %}

Recent Context:
{{ previous_outputs[-1][:500] if previous_outputs else "No recent context available" }}

{% if analysis_results and analysis_results[-1] %}
Analysis Insights:
{% for finding in analysis_results[-1].get('findings', []) %}
- {{ finding }}
{% endfor %}
{% endif %}

Please help resolve this by:
1. Diagnosing the root cause of the issue
2. Providing a specific solution approach
3. Identifying steps to implement the fix
4. Suggesting prevention strategies
5. Assessing impact on our overall objective

Focus on practical, implementable solutions.
""".strip(),
                required_variables=["user_objective", "working_directory"],
                optional_variables=["error_details", "previous_outputs", "analysis_results"],
                description="Resolves errors and issues",
                metadata={"priority": "urgent", "category": "troubleshooting"},
            ),
            PromptTemplate(
                id="quality_review",
                name="Quality Review",
                type=PromptType.QUALITY_REVIEW,
                template_content="""
Let's review the quality of our work so far.

Objective: {{ user_objective }}
Progress: {{ current_step }} of {{ total_steps }}

Work to Review:
{{ previous_outputs[-1] if previous_outputs else "No work output to review" }}

{% if analysis_results and analysis_results[-1] %}
Quality Metrics:
- Quality Score: {{ analysis_results[-1].get('quality_score', 'N/A') }}
- Confidence: {{ analysis_results[-1].get('confidence', 'N/A') }}
{% endif %}

Please provide a comprehensive quality review:
1. Code quality and best practices adherence
2. Completeness against requirements
3. Potential issues or vulnerabilities
4. Maintainability and documentation
5. Alignment with stated objectives

Suggest specific improvements and their priority levels.
""".strip(),
                required_variables=["user_objective", "current_step", "total_steps"],
                optional_variables=["previous_outputs", "analysis_results"],
                description="Reviews work quality and suggests improvements",
                metadata={"priority": "medium", "category": "quality"},
            ),
        ]

        # Register default templates
        for template in default_templates:
            self.register_template(template)

    def _load_templates_from_directory(self, templates_dir: str) -> None:
        """Load custom templates from directory"""
        templates_path = Path(templates_dir)
        if not templates_path.exists():
            logger.warning(f"Templates directory not found: {templates_dir}")
            return

        for template_file in templates_path.glob("*.json"):
            try:
                with open(template_file, "r") as f:
                    template_data = json.load(f)

                template = PromptTemplate(
                    id=template_data["id"],
                    name=template_data["name"],
                    type=PromptType(template_data["type"]),
                    template_content=template_data["template_content"],
                    required_variables=template_data["required_variables"],
                    optional_variables=template_data.get("optional_variables", []),
                    description=template_data.get("description", ""),
                    metadata=template_data.get("metadata", {}),
                )

                self.register_template(template)
                logger.info(f"Loaded custom template: {template.name}")

            except Exception as e:
                logger.error(f"Failed to load template from {template_file}: {e}")

    def register_template(self, template: PromptTemplate) -> None:
        """Register a new prompt template"""
        self.templates[template.id] = template
        # Update Jinja2 loader
        self.jinja_loader = PromptTemplateLoader(self.templates)
        self.jinja_env = Environment(loader=self.jinja_loader)
        logger.debug(f"Registered template: {template.id}")

    def render_prompt(
        self,
        template_id: str,
        context: PromptContext,
        custom_variables: Optional[Dict[str, Any]] = None,
    ) -> RenderedPrompt:
        """
        Render a prompt from template with context injection.

        Args:
            template_id: ID of template to render
            context: Context data for rendering
            custom_variables: Additional variables to inject

        Returns:
            Rendered prompt ready for execution

        Raises:
            TemplateRenderError: If rendering fails
            PromptValidationError: If validation fails
        """
        if template_id not in self.templates:
            raise TemplateRenderError(f"Template not found: {template_id}")

        template = self.templates[template_id]

        try:
            # Prepare rendering variables
            render_vars = asdict(context)
            if custom_variables:
                render_vars.update(custom_variables)

            # Add any custom variables from context
            render_vars.update(context.custom_variables)

            # Get Jinja2 template
            jinja_template = self.jinja_env.get_template(template_id)

            # Render content
            rendered_content = jinja_template.render(**render_vars)

            # Create rendered prompt
            rendered_prompt = RenderedPrompt(
                id=str(uuid.uuid4()),
                template_id=template_id,
                type=template.type,
                content=rendered_content,
                context_snapshot=render_vars.copy(),
                validation_status="pending",
                validation_messages=[],
                timestamp=datetime.now(),
            )

            # Validate rendered prompt
            self._validate_rendered_prompt(rendered_prompt, template)

            # Store rendered prompt
            self.rendered_prompts[rendered_prompt.id] = rendered_prompt

            logger.info(f"Rendered prompt {rendered_prompt.id} from template {template_id}")
            return rendered_prompt

        except Exception as e:
            raise TemplateRenderError(f"Failed to render template {template_id}: {e}")

    def _validate_rendered_prompt(
        self, rendered_prompt: RenderedPrompt, template: PromptTemplate
    ) -> None:
        """Validate a rendered prompt"""
        validation_messages = []

        # Check for placeholder variables that weren't filled
        placeholder_pattern = r"\{\{\s*([^}]+)\s*\}\}"
        unfilled_vars = re.findall(placeholder_pattern, rendered_prompt.content)

        if unfilled_vars:
            validation_messages.append(f"Unfilled template variables: {unfilled_vars}")
            rendered_prompt.validation_status = "error"

        # Check content length
        if len(rendered_prompt.content) < 50:
            validation_messages.append("Prompt content appears too short")
            rendered_prompt.validation_status = "warning"

        if len(rendered_prompt.content) > 10000:
            validation_messages.append("Prompt content is very long, may hit token limits")
            rendered_prompt.validation_status = "warning"

        # Check for required context elements
        for required_var in template.required_variables:
            if required_var not in rendered_prompt.context_snapshot:
                validation_messages.append(f"Missing required variable: {required_var}")
                rendered_prompt.validation_status = "error"

        # Set validation status if no errors found
        if rendered_prompt.validation_status == "pending":
            rendered_prompt.validation_status = "valid"

        rendered_prompt.validation_messages = validation_messages

        if rendered_prompt.validation_status == "error":
            raise PromptValidationError(f"Prompt validation failed: {validation_messages}")

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)

    def list_templates(self, prompt_type: Optional[PromptType] = None) -> List[PromptTemplate]:
        """List available templates, optionally filtered by type"""
        templates = list(self.templates.values())

        if prompt_type:
            templates = [t for t in templates if t.type == prompt_type]

        return sorted(templates, key=lambda t: (t.type.value, t.name))

    def get_rendered_prompt(self, prompt_id: str) -> Optional[RenderedPrompt]:
        """Get rendered prompt by ID"""
        return self.rendered_prompts.get(prompt_id)

    def create_context(
        self,
        session_id: str,
        user_objective: str,
        working_directory: str,
        current_step: int = 1,
        total_steps: int = 10,
        **kwargs,
    ) -> PromptContext:
        """Create a new prompt context"""
        context = PromptContext(
            session_id=session_id,
            user_objective=user_objective,
            working_directory=working_directory,
            current_step=current_step,
            total_steps=total_steps,
            previous_outputs=kwargs.get("previous_outputs", []),
            analysis_results=kwargs.get("analysis_results", []),
            workflow_state=kwargs.get("workflow_state", {}),
            custom_variables=kwargs.get("custom_variables", {}),
        )

        self.context_history.append(context)
        return context

    def update_context(self, context: PromptContext, **updates) -> PromptContext:
        """Update an existing context with new data"""
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
            else:
                context.custom_variables[key] = value

        return context

    def get_prompt_suggestions(
        self, context: PromptContext, recent_analysis: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Get suggested prompt templates based on context"""
        suggestions = []

        # Suggest based on current step
        if context.current_step == 1:
            suggestions.append("objective_clarification")

        # Suggest based on analysis results
        if recent_analysis:
            confidence = recent_analysis.get("confidence", 0)
            if confidence < 0.6:
                suggestions.append("objective_clarification")

            if "error" in str(recent_analysis).lower():
                suggestions.append("error_resolution")

        # Default progression
        suggestions.extend(["progress_assessment", "next_action"])

        # Quality check periodically
        if context.current_step % 3 == 0:
            suggestions.append("quality_review")

        return list(dict.fromkeys(suggestions))  # Remove duplicates while preserving order

    def export_template(self, template_id: str, file_path: str) -> None:
        """Export template to JSON file"""
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")

        template = self.templates[template_id]
        template_data = {
            "id": template.id,
            "name": template.name,
            "type": template.type.value,
            "template_content": template.template_content,
            "required_variables": template.required_variables,
            "optional_variables": template.optional_variables,
            "description": template.description,
            "metadata": template.metadata,
        }

        with open(file_path, "w") as f:
            json.dump(template_data, f, indent=2)

        logger.info(f"Exported template {template_id} to {file_path}")

    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get statistics about prompt coordination"""
        return {
            "total_templates": len(self.templates),
            "rendered_prompts": len(self.rendered_prompts),
            "context_history_length": len(self.context_history),
            "template_types": {
                ptype.value: len([t for t in self.templates.values() if t.type == ptype])
                for ptype in PromptType
            },
        }
