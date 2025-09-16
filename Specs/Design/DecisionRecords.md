# These are decision records regarding the deisgn of the project I want to follow for the whole project

## Python Project Management and Structure

- This project will be in python
- Use uv for package and virtual environment management
- Use ruff for formatting/linting
- Use pyright for type checking
- Use pytest for testing
- When running python ecosystem commands such as pip, pytest, etc, use `uv run <command>` to ensure the correct environment is used
- Use pre-commit hooks to ensure code quality before commits (pyright, ruff, pytest clean)

## Test-Driven Development

- Write tests before writing the actual code
- Start with a failing test for a new feature or bug fix
- Write the minimum code necessary to make the test pass
- Refactor the code while ensuring all tests still pass
- Aim for high test coverage, but prioritize meaningful tests over quantity
- Use descriptive names for test functions to clearly indicate their purpose
- Ensure all tests pass before merging code into main branch
- Do not use Mocks or Stubs in tests - tests should be as close to real usage as possible
- Always test production code - never test implementation details
- Use fixtures for setup and teardown of test environments when necessary
- Fixtures should be idempotent and reusable across multiple tests

## Separation of concerns

- Within the Claude Code setup (the .claude directory) there should be a clear separation of concerns such that tools, commands, hooks, and subagents are cleanly separated into .claude/hooks, .claude/tools, .claude/commands, and .claude/agents respectively
- DO NOT put CODE inside of agents/*.md files - keep these as only natural language instructions. 

## Documentation

- Use docstrings to document functions, classes, and modules
- Write clear and concise comments to explain complex logic
- Maintain a README file with an overview of the project, installation instructions, and usage examples - keep the README up to date with each new major feature - do not hesitate to link to more detailed documentation that must go in the docs/ directory
- Use markdown files in the docs/ directory for detailed documentation, including design decisions, architecture diagrams, and usage guides
- Keep documentation up to date with code changes

## Constraints on designs and codegen

- Do not ever use a design that calls for passwords or secrets to be stored in code
- Do not ever use STUBs, or placeholders for code that is not implemented - if a feature is not implemented, it should be clear from the design or documentation, but there should never be a placeholder in the code no TODOs, FAKE APIs, or unimplemented functions
- If a functions is not fully implemented, it needs to be removed. do not ever write code to make tests pass that is not the actual implementation