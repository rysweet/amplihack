# Workflow to Skills Migration Guide

**Version**: 1.0
**Date**: 2025-11-20
**Status**: Phase 5 (Architecture Documentation)

## Architecture Change

**Before**: Workflows | Commands | Agents | Skills (4 mechanisms)
**After**: Skills | Commands | Agents (3 mechanisms)

Workflows are now implemented as skills per Claude Code best practices.

## Deprecated Files

| File                      | Replacement                  |
| ------------------------- | ---------------------------- |
| DEFAULT_WORKFLOW.md       | default-workflow skill       |
| INVESTIGATION_WORKFLOW.md | investigation-workflow skill |
| CASCADE_WORKFLOW.md       | cascade-workflow skill       |
| CONSENSUS_WORKFLOW.md     | consensus-workflow skill     |
| DEBATE_WORKFLOW.md        | debate-workflow skill        |
| N_VERSION_WORKFLOW.md     | n-version-workflow skill     |

## Timeline

- **Now**: Deprecation warnings (Phase 5)
- **v2.0**: Markdown workflows removed

## Related

- CLAUDE.md: 3-mechanism architecture
- Specs/ATOMIC_DELIVERY_PLAN.md: Migration plan
