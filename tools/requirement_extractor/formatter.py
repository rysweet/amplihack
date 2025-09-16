"""
Formatter module for generating output documents
"""
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from .models import Requirement, ModuleRequirements, OutputFormat, GapAnalysis


class RequirementsFormatter:
    """Formats extracted requirements into various output formats"""

    def __init__(self, include_evidence: bool = True, min_confidence: float = 0.5):
        self.include_evidence = include_evidence
        self.min_confidence = min_confidence

    def format_requirements(
        self,
        module_requirements: List[ModuleRequirements],
        output_format: OutputFormat,
        gap_analysis: Optional[GapAnalysis] = None
    ) -> str:
        """Format requirements based on specified output format"""
        # Filter requirements by confidence
        all_requirements = []
        for module_reqs in module_requirements:
            filtered = [r for r in module_reqs.requirements if r.confidence >= self.min_confidence]
            all_requirements.extend(filtered)

        if output_format == OutputFormat.MARKDOWN:
            return self._format_markdown(module_requirements, all_requirements, gap_analysis)
        elif output_format == OutputFormat.JSON:
            return self._format_json(module_requirements, all_requirements, gap_analysis)
        elif output_format == OutputFormat.YAML:
            return self._format_yaml(module_requirements, all_requirements, gap_analysis)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    def _format_markdown(
        self,
        module_requirements: List[ModuleRequirements],
        all_requirements: List[Requirement],
        gap_analysis: Optional[GapAnalysis] = None
    ) -> str:
        """Format requirements as markdown"""
        lines = []

        # Header
        lines.append("# Extracted Requirements")
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Requirements: {len(all_requirements)}")
        lines.append(f"Total Modules: {len(module_requirements)}")
        lines.append("")

        # Summary statistics
        lines.append("## Summary")
        lines.append("")

        # Count by category
        categories = {}
        priorities = {"high": 0, "medium": 0, "low": 0}
        for req in all_requirements:
            categories[req.category] = categories.get(req.category, 0) + 1
            priorities[req.priority] = priorities.get(req.priority, 0) + 1

        lines.append("### By Category")
        for category, count in sorted(categories.items()):
            lines.append(f"- {category}: {count}")
        lines.append("")

        lines.append("### By Priority")
        for priority in ["high", "medium", "low"]:
            lines.append(f"- {priority.capitalize()}: {priorities[priority]}")
        lines.append("")

        # Gap analysis if available
        if gap_analysis:
            lines.append("## Gap Analysis")
            lines.append("")
            lines.append(f"- Requirements in documentation: {len(gap_analysis.documented_requirements)}")
            lines.append(f"- Requirements extracted from code: {len(gap_analysis.extracted_requirements)}")
            lines.append(f"- Missing in documentation: {len(gap_analysis.missing_in_docs)}")
            lines.append(f"- Missing in code: {len(gap_analysis.missing_in_code)}")
            lines.append(f"- Inconsistencies found: {len(gap_analysis.inconsistencies)}")
            lines.append("")

            if gap_analysis.missing_in_docs:
                lines.append("### New Requirements Found in Code")
                lines.append("")
                for req in gap_analysis.missing_in_docs[:10]:  # Show first 10
                    lines.append(f"- **{req.title}** ({req.priority})")
                    lines.append(f"  - {req.description[:200]}")
                lines.append("")

        # Requirements by module
        lines.append("## Requirements by Module")
        lines.append("")

        for module_reqs in module_requirements:
            if module_reqs.extraction_status != "completed":
                continue

            lines.append(f"### {module_reqs.module_name}")
            lines.append("")

            if module_reqs.requirements:
                for req in module_reqs.requirements:
                    if req.confidence < self.min_confidence:
                        continue

                    lines.append(f"#### {req.id}: {req.title}")
                    lines.append("")
                    lines.append(f"**Priority:** {req.priority} | **Category:** {req.category} | **Confidence:** {req.confidence:.2f}")
                    lines.append("")
                    lines.append(req.description)
                    lines.append("")

                    if self.include_evidence and req.evidence:
                        lines.append("**Evidence:**")
                        for evidence in req.evidence[:3]:  # Limit to 3 pieces
                            lines.append(f"- {evidence}")
                        lines.append("")
            else:
                lines.append("*No requirements extracted*")
                lines.append("")

        # Failed modules
        failed = [m for m in module_requirements if m.extraction_status == "failed"]
        if failed:
            lines.append("## Failed Extractions")
            lines.append("")
            for module_reqs in failed:
                lines.append(f"- {module_reqs.module_name}: {module_reqs.error_message}")
            lines.append("")

        return "\n".join(lines)

    def _format_json(
        self,
        module_requirements: List[ModuleRequirements],
        all_requirements: List[Requirement],
        gap_analysis: Optional[GapAnalysis] = None
    ) -> str:
        """Format requirements as JSON"""
        data = {
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_requirements": len(all_requirements),
                "total_modules": len(module_requirements),
                "min_confidence": self.min_confidence
            },
            "requirements": [],
            "modules": {},
            "gap_analysis": None
        }

        # Add all requirements
        for req in all_requirements:
            data["requirements"].append({
                "id": req.id,
                "title": req.title,
                "description": req.description,
                "category": req.category,
                "priority": req.priority,
                "source_modules": req.source_modules,
                "evidence": req.evidence if self.include_evidence else [],
                "confidence": req.confidence
            })

        # Add module information
        for module_reqs in module_requirements:
            data["modules"][module_reqs.module_name] = {
                "status": module_reqs.extraction_status,
                "requirement_ids": [r.id for r in module_reqs.requirements],
                "error": module_reqs.error_message
            }

        # Add gap analysis if available
        if gap_analysis:
            data["gap_analysis"] = {
                "missing_in_docs": [r.id for r in gap_analysis.missing_in_docs],
                "missing_in_code": [r.id for r in gap_analysis.missing_in_code],
                "inconsistencies": len(gap_analysis.inconsistencies)
            }

        return json.dumps(data, indent=2, ensure_ascii=False)

    def _format_yaml(
        self,
        module_requirements: List[ModuleRequirements],
        all_requirements: List[Requirement],
        gap_analysis: Optional[GapAnalysis] = None
    ) -> str:
        """Format requirements as YAML"""
        data = {
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_requirements": len(all_requirements),
                "total_modules": len(module_requirements),
                "min_confidence": self.min_confidence
            },
            "requirements": []
        }

        for req in all_requirements:
            req_data = {
                "id": req.id,
                "title": req.title,
                "description": req.description,
                "category": req.category,
                "priority": req.priority,
                "source_modules": req.source_modules,
                "confidence": req.confidence
            }
            if self.include_evidence:
                req_data["evidence"] = req.evidence
            data["requirements"].append(req_data)

        return yaml.dump(data, default_flow_style=False, sort_keys=False)