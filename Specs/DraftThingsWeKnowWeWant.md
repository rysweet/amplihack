# Brainstorming listing out things we know we want to carry forward from prior work

Goal: a system for agentic autonomous coding that has a built-in self-improvement loop

- Building on claude code and its sub agents, commands, tools, and hooks - overall we think that this has an orchestration architecture that is further ahead than the other available platforms
- Multiple purpose-built sub agents each with a speciality - allows agents to compartmentalize skills and context
- Separation of concerns between agents, commands, tools, and hooks - allows for more modularity and easier extension - keeps natural language prompts more focused and code more maintainable
- Self-improvement loop - the system should be able to analyze its own performance and make improvements based upon that analysis
- The project should be able to work in a local dev environment on other projects and maintain its self-improvement loop - I should be able to use the tool to work on projects on my system but that usage should accrue to improving the tool itself
- The system shall have a way to anchor all of its operations in some overall guidelines and development philosophy - this will help keep the system aligned with user needs and values (eg ruthless pragmatism, simplicity, maintainability, etc) (global context for all agents)
- Each agent may have its own rules or guidelines that it follows in addition to the global guidelines - this allows for specialization and focus within each agent's domain (local context for each agent)
- The system should systematically analyze tasks and break them down into manageable sub-tasks - this will help the system tackle complex problems more effectively and this task decomposition should include analyzing which tasks can be parallelized and which need to be sequential
- Continual emphasis on ruthless simplicty
- Use the claude-code sdk to initiate sub orchestration
- When we find that a task has multiple stages, repetition, and lots of tool calling - turn it into a new tool or comand that can be called by other agents
