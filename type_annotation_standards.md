# Python Type Annotation Standards

- All public functions and class methods must include explicit type annotations for parameters and return values.
- Use Python 3.8+ typing features and `typing-extensions` if necessary.
- Avoid `Any` except where strictly necessary; justify all usages in code comments.
- Prefer precise types (generics, unions, optionals, TypedDict, Literal, etc.) where applicable.
- Enforce `typeCheckingMode: strict` in pyrightconfig.json.
- Ensure all changes pass pyright and test suite in CI/CD.

Refer to https://docs.python.org/3/library/typing.html for more info.
