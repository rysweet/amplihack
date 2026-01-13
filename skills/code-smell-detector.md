# Code Smell Detector

Domain knowledge for identifying and resolving code quality issues that indicate deeper problems.

## When to Use

- Code review or quality assessment
- Refactoring planning
- Technical debt identification
- Keywords: "code smell", "refactor", "quality", "clean up"

## Common Code Smells

### Bloaters (Too Large)

| Smell | Symptoms | Fix |
|-------|----------|-----|
| **Long Method** | >20 lines, multiple responsibilities | Extract methods by responsibility |
| **Large Class** | >200 lines, multiple concerns | Split by responsibility |
| **Long Parameter List** | >3 parameters | Parameter object or builder |
| **Data Clumps** | Same fields appear together | Extract to class |

### Object-Orientation Abusers

| Smell | Symptoms | Fix |
|-------|----------|-----|
| **Switch Statements** | Repeated type checking | Polymorphism |
| **Refused Bequest** | Subclass ignores parent methods | Composition over inheritance |
| **Alternative Classes** | Same interface, different names | Merge or extract interface |

### Change Preventers

| Smell | Symptoms | Fix |
|-------|----------|-----|
| **Divergent Change** | One class, many change reasons | Split by concern |
| **Shotgun Surgery** | One change, many files | Consolidate responsibility |
| **Parallel Inheritance** | Must create subclass in two hierarchies | Merge hierarchies |

### Dispensables (Remove)

| Smell | Symptoms | Fix |
|-------|----------|-----|
| **Comments** | Explaining bad code | Make code self-documenting |
| **Duplicate Code** | Same logic in multiple places | Extract and share |
| **Dead Code** | Unreachable or unused | Delete it |
| **Speculative Generality** | Future-proofing without need | YAGNI - delete it |

### Couplers (Too Connected)

| Smell | Symptoms | Fix |
|-------|----------|-----|
| **Feature Envy** | Method uses another class more | Move method |
| **Inappropriate Intimacy** | Classes know too much about each other | Move/extract, hide delegate |
| **Message Chains** | a.b().c().d() | Hide delegate |
| **Middle Man** | Class only delegates | Remove or inline |

## Detection Checklist

```markdown
## Code Smell Scan: [file/module]

### Bloaters
- [ ] Methods under 20 lines
- [ ] Classes under 200 lines
- [ ] Parameters ≤ 3
- [ ] No repeated field groups

### OO Abusers
- [ ] No type switches
- [ ] Inheritance used appropriately
- [ ] Interfaces consistent

### Change Preventers
- [ ] Single reason to change
- [ ] Changes localized
- [ ] No parallel hierarchies

### Dispensables
- [ ] No explanatory comments needed
- [ ] No duplication
- [ ] No dead code
- [ ] No speculative features

### Couplers
- [ ] Methods use own class data
- [ ] Minimal class dependencies
- [ ] No long chains
- [ ] No pure delegates
```

## Priority Ordering

1. **High Impact**: Duplicate code, dead code, long methods
2. **Medium Impact**: Feature envy, large classes, data clumps
3. **Low Impact**: Comments, message chains, speculative generality

## Philosophy Alignment

These smells directly violate amplihack philosophy:
- **Ruthless Simplicity**: Bloaters and dispensables add unnecessary complexity
- **Brick Philosophy**: Couplers break module isolation
- **Zero-BS**: Dead code and speculative generality are waste
