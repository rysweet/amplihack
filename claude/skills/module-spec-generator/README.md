# Claude Code Skills for Amplihack

This directory contains production-ready Claude Code Skills that extend amplihack's capabilities across coding, creative work, knowledge management, and document processing.

## 📚 About Claude Code Skills

Claude Code Skills are modular, reusable capabilities that extend Claude's functionality. They consist of folders containing a `SKILL.md` file with YAML frontmatter and Markdown instructions, along with optional supporting scripts and resources.

**Key Benefits:**

- **Token Efficient**: Skills load on-demand, consuming minimal tokens until needed
- **Philosophy Aligned**: All skills follow amplihack's ruthless simplicity and modular design
- **Portable**: Work across Claude.ai, API, and Claude Code environments
- **Self-Contained**: Each skill is independently usable and testable

## 🎯 Implemented Skills

### Core Skills (12 Total)

#### Phase 1: Quick Wins (4 skills)

| Skill                     | Score | Description                                             | Issue                                                                                | PR                                                                                 |
| ------------------------- | ----- | ------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| **decision-logger**       | 49.5  | Structured decision recording (What\|Why\|Alternatives) | [#1221](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1221) | [#1231](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1231) |
| **email-drafter**         | 47.0  | Professional email generation (formal/casual/technical) | [#1223](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1223) | [#1232](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1232) |
| **module-spec-generator** | 50.0  | Generate brick module specifications                    | [#1219](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1219) | TBD                                                                                |
| **meeting-synthesizer**   | 50.0  | Extract action items and decisions from meetings        | [#1220](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1220) | [#1231](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1231) |

#### Phase 2: Philosophy Enforcement (3 skills)

| Skill                   | Score | Description                                     | Issue                                                                                | PR                                                                                 |
| ----------------------- | ----- | ----------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| **philosophy-guardian** | 45.5  | Reviews code against amplihack philosophy       | [#1224](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1224) | [#1235](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1235) |
| **test-gap-analyzer**   | 44.5  | Identifies untested functions and coverage gaps | [#1225](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1225) | [#1233](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1233) |
| **code-smell-detector** | 42.5  | Detects anti-patterns and over-engineering      | [#1228](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1228) | [#1234](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1234) |

#### Phase 3: Creative (2 skills)

| Skill                         | Score | Description                                          | Issue                                                                                | PR                                                                                 |
| ----------------------------- | ----- | ---------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| **mermaid-diagram-generator** | 48.0  | Converts descriptions to Mermaid diagrams            | [#1222](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1222) | [#1236](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1236) |
| **storytelling-synthesizer**  | 44.0  | Transforms technical work into compelling narratives | [#1226](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1226) | [#1236](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1236) |

#### Phase 4: Advanced (3 skills)

| Skill                     | Score | Description                                          | Issue                                                                                | PR                                                                                 |
| ------------------------- | ----- | ---------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| **learning-path-builder** | 43.5  | Creates personalized technology learning paths       | [#1227](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1227) | [#1237](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1237) |
| **knowledge-extractor**   | 40.5  | Extracts learnings to DISCOVERIES.md and PATTERNS.md | [#1229](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1229) | [#1238](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1238) |
| **pr-review-assistant**   | 40.0  | Philosophy-aware PR reviews                          | [#1230](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1230) | TBD                                                                                |

### Office Document Skills (4 Skills)

Anthropic's office document skills integrated into amplihack for comprehensive document processing capabilities.

| Skill    | Status     | Description                                                  | Documentation            |
| -------- | ---------- | ------------------------------------------------------------ | ------------------------ |
| **pdf**  | Integrated | Comprehensive PDF manipulation - extract, create, merge, OCR | [README](pdf/README.md)  |
| **xlsx** | Integrated | Excel spreadsheet manipulation with formulas and charts      | [README](xlsx/README.md) |
| **docx** | Integrated | Word document processing with tracked changes                | [README](docx/README.md) |
| **pptx** | Integrated | PowerPoint presentation generation                           | [README](pptx/README.md) |

## 📖 Research & Documentation

### Research Reports

- **[Complete Research Report](../runtime/logs/20251108_skills_research/RESEARCH.md)** (357 lines)
  - Comprehensive analysis of Claude Code Skills ecosystem
  - Comparison with MCP (Model Context Protocol)
  - 23+ documented skills from Anthropic and community
  - Key insights from Simon Willison and other experts

- **[Evaluation Matrix & Ideas](../runtime/logs/20251108_skills_research/EVALUATION_MATRIX_AND_IDEAS.md)** (842 lines)
  - 6-criteria evaluation framework aligned with amplihack philosophy
  - 20 brainstormed skill ideas with priority scores
  - Implementation phases and effort estimates
  - Detailed scoring rubrics

### Evaluation Criteria

All skills were evaluated on:

1. **Ruthless Simplicity** (1-5): Single clear purpose, minimal dependencies
2. **Modular Design** (1-5): Self-contained, clear interfaces (bricks & studs)
3. **Zero-BS Implementation** (1-5): Actually works, no stubs
4. **Reusability** (1-5): Useful across multiple contexts
5. **Maintenance Burden** (1-5, lower is better): Stable dependencies
6. **User Value** (1-5): Solves frequent pain points, measurable time savings

**Priority Score Formula:**

```
Priority = (Simplicity * 2) + (Modular * 2) + (Zero-BS * 1.5) +
           (Reusability * 1.5) + ((6 - Maintenance) * 1) + (User Value * 2.5)
Max Score: 50 points
```

## 🔍 Using Skills

Skills are automatically discovered from:

- User settings: `~/.config/claude/skills/`
- Project settings: `~/.amplihack/.claude/skills/`
- Plugin-provided skills
- Built-in skills

### Invoking Skills

```
Claude, use the decision-logger skill to record this architectural decision.

Claude, analyze test coverage using test-gap-analyzer.

Claude, generate a Mermaid diagram for this workflow using mermaid-diagram-generator.

Claude, extract all tables from sales_report.pdf to Excel using the pdf skill.
```

### Managing Skills

```bash
/agents                # List available agents and skills
/reload-skills         # Reload after modifications
```

## 🏗️ Skill Structure

Each skill follows this structure:

```
skill-name/
├── SKILL.md           # Required: YAML frontmatter + instructions
├── README.md          # Optional: User-facing documentation
├── DEPENDENCIES.md    # Optional: Dependency documentation (Office skills)
├── examples/          # Optional: Example usage
└── tests/             # Optional: Validation tests
```

### SKILL.md Format

```yaml
---
name: skill-name
description: |
  Clear description of what this skill does and when Claude should use it.
  Include both the capability AND the usage context.
---

# Skill Instructions

Detailed instructions for Claude on how to use this skill...

## Examples
Concrete examples with input/output...
```

## 📊 Quality Standards

All skills meet these quality standards:

- ✅ **Complete Documentation**: SKILL.md with YAML frontmatter
- ✅ **Clear Examples**: Real-world usage demonstrations
- ✅ **Philosophy Aligned**: Ruthless simplicity, modular design, zero-BS
- ✅ **Tested**: Quality review completed
- ✅ **Production Ready**: No stubs, TODOs, or placeholders

## 🚀 Office Skills Quick Start

### 1. Choose Your Skill

Identify which document type you need to work with:

- PDF files → Use `pdf` skill
- Excel files (.xlsx) → Use `xlsx` skill (coming soon)
- Word documents (.docx) → Use `docx` skill (coming soon)
- PowerPoint slides (.pptx) → Use `pptx` skill (coming soon)

### 2. Install Dependencies

Each skill has different dependencies. See skill-specific DEPENDENCIES.md:

```bash
# For PDF skill
pip install pypdf pdfplumber reportlab pandas

# Optional OCR support
pip install pytesseract pdf2image
brew install tesseract poppler  # macOS
```

### 3. Verify Installation

Use the verification script to check dependencies:

```bash
cd .claude/skills
python common/verification/verify_skill.py pdf
```

### 4. Use in Claude Code

Simply mention the task in conversation:

```
User: Extract all tables from sales_report.pdf to Excel
Claude: [Uses PDF skill to extract and convert tables]

User: Create a professional PDF report with our Q4 data
Claude: [Uses PDF skill to generate formatted report]
```

## Office Skills Architecture

### Directory Structure

```
.claude/skills/
├── README.md                    # This file
├── INTEGRATION_STATUS.md        # Office skills integration tracker
├── common/                      # Shared infrastructure for Office skills
│   ├── README.md
│   ├── dependencies.txt         # Shared dependencies
│   ├── ooxml/                   # OOXML scripts (docx + pptx)
│   └── verification/            # Dependency verification
├── pdf/                         # PDF skill
│   ├── SKILL.md                 # Official skill definition
│   ├── README.md                # Integration notes
│   ├── DEPENDENCIES.md          # Dependency documentation
│   ├── examples/
│   └── tests/
├── decision-logger/             # Core skill example
├── email-drafter/               # Core skill example
└── ... (other skills)
```

### Design Principles

Each skill follows amplihack's brick philosophy:

1. **Self-contained**: All skill code in its directory
2. **Clear contract**: Well-defined inputs and outputs
3. **Regeneratable**: Can be rebuilt from specification
4. **Independent**: No cross-skill dependencies
5. **Graceful degradation**: Optional features skip cleanly

## Philosophy Compliance

Skills integration follows amplihack's core principles:

### Ruthless Simplicity

- Use established libraries, no custom parsers
- Minimal abstractions
- Direct, straightforward implementations

### Modular Design

- Each skill is an independent brick
- Clear public contracts (SKILL.md)
- No implicit dependencies

### Zero-BS Implementation

- No stubs or placeholders
- All code works or degrades gracefully
- No fake implementations

### Explicit Over Implicit

- All dependencies documented
- No automatic installation
- Clear error messages with solutions

### Regeneratable

- Each skill can be rebuilt from SKILL.md
- Documentation is specification
- Tests verify contracts

## 🤝 Contributing

When adding new skills:

1. Create GitHub issue with evaluation scores
2. Implement in separate worktree/branch
3. Follow naming: `feat/issue-{number}-{skill-name}`
4. Create PR with comprehensive description
5. Link to research and evaluation docs
6. Ensure quality review completed

## 📚 Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Project overview and agent system
- [PHILOSOPHY.md](../context/PHILOSOPHY.md) - Ruthless simplicity principles
- [PATTERNS.md](../context/PATTERNS.md) - Reusable solution patterns
- [Agent Catalog](../agents/CATALOG.md) - Specialized agents
- [Office Skills Integration Status](INTEGRATION_STATUS.md) - Progress tracker

## License

The Office skills are provided by Anthropic under their proprietary license. See individual SKILL.md files and Anthropic's LICENSE.txt for complete terms.

The amplihack integration code and core skills follow the amplihack project license.

---

**Last Updated**: November 9, 2025
**Total Skills**: 16 (12 core + 4 office)
**Status**: Production Ready (12 core skills + 4 office skills integrated - COMPLETE!)

🤖 Skills documentation maintained as part of amplihack project
