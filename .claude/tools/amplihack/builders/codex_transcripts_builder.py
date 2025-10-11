#!/usr/bin/env python3
"""
Codex Transcripts Builder - Microsoft Amplifier Style
Builds structured knowledge extraction and codex from multiple session transcripts.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from ..paths import get_project_root
except ImportError:
    # Fallback for testing or standalone usage
    from pathlib import Path

    def get_project_root():
        return Path(__file__).resolve().parents[4]


class CodexTranscriptsBuilder:
    """Builds codex and knowledge extraction from multiple session transcripts."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize codex builder.

        Args:
            output_dir: Optional output directory. Defaults to .claude/runtime/codex/
        """
        self.project_root = get_project_root()
        self.logs_dir = self.project_root / ".claude" / "runtime" / "logs"
        self.output_dir = (
            Path(output_dir)
            if output_dir
            else (self.project_root / ".claude" / "runtime" / "codex")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_comprehensive_codex(self, session_ids: Optional[List[str]] = None) -> str:
        """Build comprehensive codex from all or specified sessions.

        Args:
            session_ids: Optional list of session IDs. If None, processes all sessions.

        Returns:
            Path to the generated codex file
        """
        sessions = self._get_sessions(session_ids)

        codex_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "source": "codex_transcripts_builder",
                "version": "1.0",
                "sessions_processed": len(sessions),
                "total_sessions_available": len(self._get_all_session_ids()),
            },
            "knowledge_patterns": self._extract_knowledge_patterns(sessions),
            "tool_usage_analytics": self._analyze_tool_usage_across_sessions(sessions),
            "conversation_insights": self._extract_conversation_insights(sessions),
            "decision_patterns": self._analyze_decision_patterns(sessions),
            "success_patterns": self._analyze_success_patterns(sessions),
            "error_patterns": self._analyze_error_patterns(sessions),
            "learning_insights": self._extract_learning_insights(sessions),
            "workflow_patterns": self._extract_workflow_patterns(sessions),
            "session_summaries": self._create_session_summaries(sessions),
        }

        codex_file = (
            self.output_dir / f"comprehensive_codex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(codex_file, "w") as f:
            json.dump(codex_data, f, indent=2)

        # Also create a markdown report
        self._create_markdown_codex_report(codex_data)

        return str(codex_file)

    def build_focused_codex(self, focus_area: str, session_ids: Optional[List[str]] = None) -> str:
        """Build focused codex for specific area (tools, errors, patterns, etc.).

        Args:
            focus_area: Area to focus on (tools, errors, patterns, decisions, workflows)
            session_ids: Optional list of session IDs

        Returns:
            Path to the focused codex file
        """
        sessions = self._get_sessions(session_ids)

        if focus_area == "tools":
            codex_data = self._build_tools_focused_codex(sessions)
        elif focus_area == "errors":
            codex_data = self._build_errors_focused_codex(sessions)
        elif focus_area == "patterns":
            codex_data = self._build_patterns_focused_codex(sessions)
        elif focus_area == "decisions":
            codex_data = self._build_decisions_focused_codex(sessions)
        elif focus_area == "workflows":
            codex_data = self._build_workflows_focused_codex(sessions)
        else:
            raise ValueError(f"Unsupported focus area: {focus_area}")

        codex_file = (
            self.output_dir / f"{focus_area}_codex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(codex_file, "w") as f:
            json.dump(codex_data, f, indent=2)

        return str(codex_file)

    def extract_learning_corpus(self, session_ids: Optional[List[str]] = None) -> str:
        """Extract learning corpus for training and knowledge transfer.

        Args:
            session_ids: Optional list of session IDs

        Returns:
            Path to the learning corpus file
        """
        sessions = self._get_sessions(session_ids)

        corpus = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "sessions_count": len(sessions),
                "extraction_method": "codex_transcripts_builder",
            },
            "conversation_patterns": self._extract_conversation_patterns(sessions),
            "problem_solution_pairs": self._extract_problem_solution_pairs(sessions),
            "code_examples": self._extract_code_examples(sessions),
            "best_practices": self._extract_best_practices(sessions),
            "common_mistakes": self._extract_common_mistakes(sessions),
            "tool_usage_examples": self._extract_tool_usage_examples(sessions),
            "workflow_templates": self._extract_workflow_templates(sessions),
        }

        corpus_file = (
            self.output_dir / f"learning_corpus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(corpus_file, "w") as f:
            json.dump(corpus, f, indent=2)

        return str(corpus_file)

    def generate_insights_report(self, session_ids: Optional[List[str]] = None) -> str:
        """Generate insights report from session transcripts.

        Args:
            session_ids: Optional list of session IDs

        Returns:
            Path to the insights report file
        """
        sessions = self._get_sessions(session_ids)

        insights = {
            "executive_summary": self._create_executive_summary(sessions),
            "productivity_metrics": self._calculate_productivity_metrics(sessions),
            "tool_effectiveness": self._analyze_tool_effectiveness(sessions),
            "common_bottlenecks": self._identify_common_bottlenecks(sessions),
            "success_factors": self._identify_success_factors(sessions),
            "improvement_opportunities": self._identify_improvement_opportunities(sessions),
            "trend_analysis": self._perform_trend_analysis(sessions),
            "recommendations": self._generate_recommendations(sessions),
        }

        report_file = (
            self.output_dir / f"insights_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w") as f:
            json.dump(insights, f, indent=2)

        # Create markdown version
        self._create_markdown_insights_report(insights)

        return str(report_file)

    def _get_sessions(self, session_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Get session data for specified or all sessions."""
        if session_ids:
            available_ids = set(self._get_all_session_ids())
            session_ids = [sid for sid in session_ids if sid in available_ids]
        else:
            session_ids = self._get_all_session_ids()

        sessions = []
        for session_id in session_ids:
            session_data = self._load_session_data(session_id)
            if session_data:
                sessions.append(session_data)

        return sessions

    def _get_all_session_ids(self) -> List[str]:
        """Get all available session IDs."""
        if not self.logs_dir.exists():
            return []

        session_ids = []
        for session_dir in self.logs_dir.iterdir():
            if session_dir.is_dir():
                session_ids.append(session_dir.name)

        return sorted(session_ids, reverse=True)

    def _load_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from various files."""
        session_dir = self.logs_dir / session_id
        if not session_dir.exists():
            return None

        session_data = {
            "session_id": session_id,
            "transcript": None,
            "codex_export": None,
            "summary": None,
            "original_request": None,
            "decisions": None,
        }

        # Load conversation transcript
        transcript_file = session_dir / "conversation_transcript.json"
        if transcript_file.exists():
            try:
                with open(transcript_file) as f:
                    session_data["transcript"] = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        # Load codex export
        codex_file = session_dir / "codex_export.json"
        if codex_file.exists():
            try:
                with open(codex_file) as f:
                    session_data["codex_export"] = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        # Load session summary
        summary_file = session_dir / "session_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file) as f:
                    session_data["summary"] = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        # Load original request
        original_request_file = session_dir / "original_request.json"
        if original_request_file.exists():
            try:
                with open(original_request_file) as f:
                    session_data["original_request"] = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        # Load decisions
        decisions_file = session_dir / "DECISIONS.md"
        if decisions_file.exists():
            try:
                session_data["decisions"] = decisions_file.read_text()
            except OSError:
                pass

        return session_data if any(session_data.values()) else None

    def _extract_knowledge_patterns(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract knowledge patterns across sessions."""
        patterns = {
            "recurring_topics": {},
            "tool_combinations": {},
            "solution_approaches": {},
            "knowledge_domains": set(),
        }

        for session in sessions:
            if session.get("codex_export"):
                codex = session["codex_export"]

                # Analyze knowledge artifacts
                artifacts = codex.get("knowledge_artifacts", [])
                for artifact in artifacts:
                    if artifact.get("type") == "code_block":
                        lang = artifact.get("language", "unknown")
                        patterns["knowledge_domains"].add(lang)

                # Analyze tool usage patterns
                tools_analysis = codex.get("tools_usage", {})
                tool_sequence = tools_analysis.get("tool_sequence", [])
                for i in range(len(tool_sequence) - 1):
                    combo = f"{tool_sequence[i]} -> {tool_sequence[i + 1]}"
                    patterns["tool_combinations"][combo] = (
                        patterns["tool_combinations"].get(combo, 0) + 1
                    )

        # Convert set to list for JSON serialization
        patterns["knowledge_domains"] = list(patterns["knowledge_domains"])

        return patterns

    def _analyze_tool_usage_across_sessions(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze tool usage patterns across all sessions."""
        analysis = {
            "total_tool_calls": 0,
            "tool_frequency": {},
            "tool_success_rate": {},
            "tool_combinations": {},
            "session_tool_usage": {},
        }

        for session in sessions:
            session_id = session["session_id"]
            if session.get("codex_export"):
                tools_usage = session["codex_export"].get("tools_usage", {})

                analysis["total_tool_calls"] += tools_usage.get("total_tool_calls", 0)

                # Aggregate tool frequency
                tool_freq = tools_usage.get("tool_frequency", {})
                for tool, freq in tool_freq.items():
                    analysis["tool_frequency"][tool] = (
                        analysis["tool_frequency"].get(tool, 0) + freq
                    )

                analysis["session_tool_usage"][session_id] = tool_freq

        return analysis

    def _extract_conversation_insights(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract insights about conversation patterns."""
        insights = {
            "average_session_length": 0,
            "message_type_distribution": {},
            "conversation_flow_patterns": [],
            "interaction_patterns": {},
        }

        total_messages = 0
        total_sessions = len(sessions)

        for session in sessions:
            if session.get("transcript"):
                messages = session["transcript"].get("messages", [])
                total_messages += len(messages)

                # Analyze message types
                for msg in messages:
                    role = msg.get("role", "unknown")
                    insights["message_type_distribution"][role] = (
                        insights["message_type_distribution"].get(role, 0) + 1
                    )

        if total_sessions > 0:
            insights["average_session_length"] = total_messages / total_sessions

        return insights

    def _analyze_decision_patterns(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze decision-making patterns across sessions."""
        patterns = {
            "decision_types": {},
            "decision_outcomes": {},
            "decision_frequency": 0,
            "common_decision_points": [],
        }

        for session in sessions:
            if session.get("codex_export"):
                decisions = session["codex_export"].get("decisions_made", [])
                patterns["decision_frequency"] += len(decisions)

                for decision in decisions:
                    decision_text = decision.get("decision", "")
                    # Categorize decisions
                    if "implement" in decision_text.lower():
                        patterns["decision_types"]["implementation"] = (
                            patterns["decision_types"].get("implementation", 0) + 1
                        )
                    elif "fix" in decision_text.lower():
                        patterns["decision_types"]["fix"] = (
                            patterns["decision_types"].get("fix", 0) + 1
                        )
                    elif "design" in decision_text.lower():
                        patterns["decision_types"]["design"] = (
                            patterns["decision_types"].get("design", 0) + 1
                        )

        return patterns

    def _analyze_success_patterns(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze success patterns across sessions."""
        patterns = {"success_indicators": {}, "completion_rates": {}, "success_factors": []}

        for session in sessions:
            if session.get("codex_export"):
                outcomes = session["codex_export"].get("outcomes_achieved", [])

                for outcome in outcomes:
                    outcome_type = outcome.get("type", "unknown")
                    patterns["success_indicators"][outcome_type] = (
                        patterns["success_indicators"].get(outcome_type, 0) + 1
                    )

        return patterns

    def _analyze_error_patterns(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze error patterns across sessions."""
        patterns = {
            "error_types": {},
            "error_frequency": 0,
            "resolution_patterns": {},
            "common_errors": [],
        }

        for session in sessions:
            if session.get("codex_export"):
                outcomes = session["codex_export"].get("outcomes_achieved", [])

                for outcome in outcomes:
                    if outcome.get("type") in ["error", "failure"]:
                        patterns["error_frequency"] += 1
                        error_desc = outcome.get("description", "")

                        # Categorize errors
                        if "import" in error_desc.lower():
                            patterns["error_types"]["import"] = (
                                patterns["error_types"].get("import", 0) + 1
                            )
                        elif "syntax" in error_desc.lower():
                            patterns["error_types"]["syntax"] = (
                                patterns["error_types"].get("syntax", 0) + 1
                            )
                        elif "file" in error_desc.lower():
                            patterns["error_types"]["file"] = (
                                patterns["error_types"].get("file", 0) + 1
                            )

        return patterns

    def _extract_learning_insights(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract learning insights from sessions."""
        insights = {
            "knowledge_progression": [],
            "skill_development": {},
            "learning_velocity": 0,
            "knowledge_gaps": [],
        }

        # Analyze progression over time
        sessions_by_date = sorted(sessions, key=lambda s: s["session_id"])

        for i, session in enumerate(sessions_by_date):
            if session.get("summary"):
                tools_used = session["summary"].get("tools_used", [])
                insights["knowledge_progression"].append(
                    {
                        "session_index": i,
                        "session_id": session["session_id"],
                        "tools_count": len(tools_used),
                        "complexity_score": self._calculate_complexity_score(session),
                    }
                )

        return insights

    def _extract_workflow_patterns(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract workflow patterns from sessions."""
        patterns = {
            "common_workflows": {},
            "workflow_efficiency": {},
            "step_patterns": [],
            "optimization_opportunities": [],
        }

        for session in sessions:
            if session.get("codex_export"):
                flow = session["codex_export"].get("conversation_flow", [])

                # Analyze tool sequences
                tool_sequence = []
                for step in flow:
                    tools = step.get("tools_mentioned", [])
                    tool_sequence.extend(tools)

                if len(tool_sequence) > 2:
                    workflow_signature = " -> ".join(tool_sequence[:5])
                    patterns["common_workflows"][workflow_signature] = (
                        patterns["common_workflows"].get(workflow_signature, 0) + 1
                    )

        return patterns

    def _create_session_summaries(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create summaries for each session."""
        summaries = []

        for session in sessions:
            summary = {
                "session_id": session["session_id"],
                "has_transcript": bool(session.get("transcript")),
                "has_codex": bool(session.get("codex_export")),
                "has_summary": bool(session.get("summary")),
                "message_count": 0,
                "tools_used": [],
                "outcomes_count": 0,
            }

            if session.get("transcript"):
                summary["message_count"] = len(session["transcript"].get("messages", []))

            if session.get("summary"):
                summary["tools_used"] = session["summary"].get("tools_used", [])

            if session.get("codex_export"):
                outcomes = session["codex_export"].get("outcomes_achieved", [])
                summary["outcomes_count"] = len(outcomes)

            summaries.append(summary)

        return summaries

    def _calculate_complexity_score(self, session: Dict[str, Any]) -> float:
        """Calculate complexity score for a session."""
        score = 0.0

        if session.get("summary"):
            summary = session["summary"]
            score += len(summary.get("tools_used", [])) * 0.5
            score += summary.get("message_count", 0) * 0.1

        if session.get("codex_export"):
            codex = session["codex_export"]
            score += len(codex.get("knowledge_artifacts", [])) * 0.3
            score += len(codex.get("decisions_made", [])) * 0.2

        return score

    def _build_tools_focused_codex(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build tools-focused codex."""
        return {
            "focus": "tools",
            "analysis": self._analyze_tool_usage_across_sessions(sessions),
            "tool_effectiveness": self._analyze_tool_effectiveness(sessions),
            "tool_combinations": self._extract_tool_combinations(sessions),
            "tool_learning_curve": self._analyze_tool_learning_curve(sessions),
        }

    def _build_errors_focused_codex(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build errors-focused codex."""
        return {
            "focus": "errors",
            "error_patterns": self._analyze_error_patterns(sessions),
            "resolution_strategies": self._extract_resolution_strategies(sessions),
            "error_prevention": self._identify_error_prevention_opportunities(sessions),
        }

    def _build_patterns_focused_codex(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build patterns-focused codex."""
        return {
            "focus": "patterns",
            "conversation_patterns": self._extract_conversation_patterns(sessions),
            "workflow_patterns": self._extract_workflow_patterns(sessions),
            "success_patterns": self._analyze_success_patterns(sessions),
        }

    def _build_decisions_focused_codex(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build decisions-focused codex."""
        return {
            "focus": "decisions",
            "decision_patterns": self._analyze_decision_patterns(sessions),
            "decision_outcomes": self._analyze_decision_outcomes(sessions),
            "decision_quality": self._assess_decision_quality(sessions),
        }

    def _build_workflows_focused_codex(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build workflows-focused codex."""
        return {
            "focus": "workflows",
            "workflow_patterns": self._extract_workflow_patterns(sessions),
            "efficiency_metrics": self._calculate_workflow_efficiency(sessions),
            "optimization_opportunities": self._identify_workflow_optimizations(sessions),
        }

    # Additional helper methods for focused analysis
    def _analyze_tool_effectiveness(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze tool effectiveness across sessions."""
        return {"placeholder": "Tool effectiveness analysis"}

    def _extract_tool_combinations(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract effective tool combinations."""
        return {"placeholder": "Tool combinations analysis"}

    def _analyze_tool_learning_curve(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze tool learning curve."""
        return {"placeholder": "Tool learning curve analysis"}

    def _extract_resolution_strategies(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract error resolution strategies."""
        return {"placeholder": "Resolution strategies"}

    def _identify_error_prevention_opportunities(
        self, sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Identify error prevention opportunities."""
        return {"placeholder": "Error prevention opportunities"}

    def _extract_conversation_patterns(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract conversation patterns."""
        return {"placeholder": "Conversation patterns"}

    def _analyze_decision_outcomes(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze decision outcomes."""
        return {"placeholder": "Decision outcomes"}

    def _assess_decision_quality(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess decision quality."""
        return {"placeholder": "Decision quality assessment"}

    def _calculate_workflow_efficiency(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate workflow efficiency metrics."""
        return {"placeholder": "Workflow efficiency"}

    def _identify_workflow_optimizations(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify workflow optimization opportunities."""
        return {"placeholder": "Workflow optimizations"}

    def _extract_problem_solution_pairs(
        self, sessions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract problem-solution pairs for learning."""
        return [{"placeholder": "Problem-solution pairs"}]

    def _extract_code_examples(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract code examples from sessions."""
        return [{"placeholder": "Code examples"}]

    def _extract_best_practices(self, sessions: List[Dict[str, Any]]) -> List[str]:
        """Extract best practices from sessions."""
        return ["Placeholder best practice"]

    def _extract_common_mistakes(self, sessions: List[Dict[str, Any]]) -> List[str]:
        """Extract common mistakes from sessions."""
        return ["Placeholder common mistake"]

    def _extract_tool_usage_examples(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tool usage examples."""
        return [{"placeholder": "Tool usage examples"}]

    def _extract_workflow_templates(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract workflow templates."""
        return [{"placeholder": "Workflow templates"}]

    def _create_executive_summary(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create executive summary of sessions."""
        return {"total_sessions": len(sessions), "summary": "Placeholder executive summary"}

    def _calculate_productivity_metrics(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate productivity metrics."""
        return {"placeholder": "Productivity metrics"}

    def _identify_common_bottlenecks(self, sessions: List[Dict[str, Any]]) -> List[str]:
        """Identify common bottlenecks."""
        return ["Placeholder bottleneck"]

    def _identify_success_factors(self, sessions: List[Dict[str, Any]]) -> List[str]:
        """Identify success factors."""
        return ["Placeholder success factor"]

    def _identify_improvement_opportunities(self, sessions: List[Dict[str, Any]]) -> List[str]:
        """Identify improvement opportunities."""
        return ["Placeholder improvement opportunity"]

    def _perform_trend_analysis(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform trend analysis on sessions."""
        return {"placeholder": "Trend analysis"}

    def _generate_recommendations(self, sessions: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on analysis."""
        return ["Placeholder recommendation"]

    def _create_markdown_codex_report(self, codex_data: Dict[str, Any]) -> None:
        """Create markdown version of codex report."""
        report_content = f"""# Comprehensive Codex Report

Generated: {codex_data["metadata"]["created_at"]}
Sessions Processed: {codex_data["metadata"]["sessions_processed"]}

## Knowledge Patterns

{json.dumps(codex_data["knowledge_patterns"], indent=2)}

## Tool Usage Analytics

{json.dumps(codex_data["tool_usage_analytics"], indent=2)}

## Insights Summary

This report provides comprehensive analysis of conversation patterns,
tool usage, and knowledge extraction across multiple sessions.
"""

        report_file = (
            self.output_dir
            / f"comprehensive_codex_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        report_file.write_text(report_content)

    def _create_markdown_insights_report(self, insights: Dict[str, Any]) -> None:
        """Create markdown version of insights report."""
        report_content = f"""# Session Insights Report

Generated: {datetime.now().isoformat()}

## Executive Summary

{json.dumps(insights["executive_summary"], indent=2)}

## Key Insights

This report provides actionable insights for improving development
workflows and tool usage based on session analysis.
"""

        report_file = (
            self.output_dir / f"insights_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        report_file.write_text(report_content)
