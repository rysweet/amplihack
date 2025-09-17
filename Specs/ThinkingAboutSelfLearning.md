# Brainstorming about how we want to do self-learning

# When do we invoke the analysis to do improvement?

- After every task?
- After a set of tasks?
- After a certain time period?
- on demand?

# How can the tool customize its behavior to learn from what the specific user wants?

- eg: Ryan says "I want you to always be more concise in your answers"
- but Lynn might say "I prefer really verbose answers"

## types of custom behavior

    - verbosity
    - level of detail
    - style of communication (formal, informal, technical, etc)
    - preferred programming languages or frameworks
    - specific coding standards or guidelines
    - frequency of updates or check-ins
    - types of tasks to prioritize (e.g. bug fixes vs new features)
    - collaboration style (e.g. more independent vs more interactive)
    - workflow preferences (e.g. order of operations, required gates etc)

## where would we store these?

- in the @/.claude/context/USER_PREFERENCES.md

## when using my preferences - want it to let you know - need auditability or decision record...

- eg "I am being more concise because you asked me to be in your preferences"

# How can the tool itself improve/fix its own code?

- eg bugfix
- eg new guidelines or features
- eg refactoring
- eg performance improvements
- eg security improvements
- eg usability improvements
- eg adding new agent types
