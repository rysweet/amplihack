---
title: Glossary
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Glossary
</nav>

# Atlas Glossary

| Term                       | Definition                                                                   |
| -------------------------- | ---------------------------------------------------------------------------- |
| **Layer**                  | A distinct analytical view of the codebase (8 total)                         |
| **Structural layer**       | Layers analyzing static code structure (1, 2, 3, 4, 7)                       |
| **Behavioral layer**       | Layers analyzing runtime behavior and data flow (5, 6, 8)                    |
| **Manifest**               | Canonical file list built from `git ls-files` (Layer 0 foundation)           |
| **Coverage**               | Percentage of manifest files analyzed by a layer                             |
| **Afferent coupling (Ca)** | Number of packages that depend on this package                               |
| **Efferent coupling (Ce)** | Number of packages this package depends on                                   |
| **Instability**            | Ce / (Ca + Ce). 0 = maximally stable, 1 = maximally unstable                 |
| **Dead code**              | Definitions not exported, not imported, not called internally (conservative) |
| **Entry point**            | CLI command, HTTP route, or hook that starts a user journey                  |
| **Journey**                | Trace from entry point through call graph to outcome (depth-limited)         |
| **Outcome**                | Terminal action: file I/O, database op, subprocess, network call, or return  |
| **Cross-layer check**      | Validation that data is consistent across multiple layers                    |
| **Transformation point**   | Function that both reads and writes data (data flow bridge)                  |
