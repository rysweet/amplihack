# Computer Scientist Analyst - Quick Reference

## TL;DR

Analyze computational problems through theoretical computer science: algorithmic complexity (Big-O), computational tractability (P vs. NP), data structure trade-offs, distributed systems limits (CAP theorem), and information theory. Ensure solutions scale and avoid intractable approaches.

## When to Use

**Perfect For:**

- Algorithm selection and optimization
- Performance prediction and capacity planning
- Problem feasibility assessment
- System scalability analysis
- Data structure selection
- Distributed systems design
- Cryptography and security analysis
- Compression and encoding decisions

**Skip If:**

- Problem scale is trivially small
- Performance is not a concern
- Looking for UI/UX insights
- Focused on business or social aspects

## Core Frameworks

### Big-O Complexity

Understand how algorithms scale:

- **O(1)** - Constant: Array access, hash lookup
- **O(log n)** - Logarithmic: Binary search, balanced trees
- **O(n)** - Linear: Array traversal
- **O(n log n)** - Linearithmic: Good sorting (merge, heap, quick)
- **O(n²)** - Quadratic: Nested loops, bad sorting (bubble, insertion)
- **O(2ⁿ)** - Exponential: Recursive combinations, brute force
- **O(n!)** - Factorial: Permutations, traveling salesman brute force

**Rule of Thumb**: O(n log n) is usually the best you can do for comparison-based problems. O(n²) acceptable only for small n (< 1000).

### P vs. NP

Understanding computational tractability:

- **P** - Solvable efficiently (polynomial time)
- **NP** - Solutions verifiable efficiently
- **NP-complete** - Hardest problems in NP (Boolean satisfiability, traveling salesman, graph coloring, knapsack)
- **NP-hard** - At least as hard as NP-complete

**Implication**: If problem is NP-complete, use approximations or heuristics, not exact algorithms (unless n is small).

### CAP Theorem

Distributed systems can guarantee at most 2 of 3:

- **Consistency** - All nodes see same data at same time
- **Availability** - System responds to all requests
- **Partition Tolerance** - System continues despite network partitions

**Trade-off**: CP (consistent, partition-tolerant) vs. AP (available, partition-tolerant)

### Data Structure Selection

Choose based on operation frequency:

- **Array** - O(1) access, O(n) insert/delete
- **Linked List** - O(1) insert/delete at ends, O(n) access
- **Hash Table** - O(1) average insert/lookup/delete, O(n) worst case
- **Binary Search Tree** - O(log n) balanced, O(n) unbalanced
- **Heap** - O(1) find-min, O(log n) insert/delete
- **Graph** - Adjacency list vs. matrix (sparse vs. dense)

## Quick Analysis Steps

### Step 1: Define the Problem (3 min)

- What is the input? What size (n)?
- What is the desired output?
- What operations are frequent vs. rare?
- What are the performance requirements?

### Step 2: Complexity Analysis (8 min)

- Identify loops and recursion
- Count nested operations
- Express as function of n
- Simplify to Big-O notation
- Check against known algorithm complexities

### Step 3: Tractability Check (5 min)

- Is this a known problem? (search literature)
- Is it NP-complete? (reduction from known problem)
- What's the input size in practice?
- Can we afford exponential? (n < 20 maybe OK)
- Do we need exact or approximate solution?

### Step 4: Data Structure Selection (7 min)

- List required operations and frequencies
- Calculate weighted complexity for each structure
- Consider space constraints
- Evaluate cache locality and memory patterns
- Choose structure optimizing for actual usage

### Step 5: Distributed Systems Analysis (7 min)

- What consistency guarantees are needed?
- What availability is required?
- How do we handle network partitions?
- Apply CAP theorem to trade-offs
- Consider eventual consistency models

### Step 6: Optimization Opportunities (5 min)

- Can we reduce complexity class? (O(n²) → O(n log n))
- Apply algorithm design paradigm (dynamic programming, greedy)
- Consider preprocessing or caching
- Evaluate parallelization potential
- Check for better data structure

## Key Algorithms to Know

### Sorting (O(n log n))

- **Merge Sort** - Stable, O(n) space, guaranteed O(n log n)
- **Quick Sort** - In-place, average O(n log n), worst O(n²)
- **Heap Sort** - In-place, guaranteed O(n log n)

### Searching

- **Binary Search** - O(log n) on sorted array
- **Hash Table** - O(1) average, O(n) worst
- **BFS/DFS** - O(V + E) graph traversal

### Graph Algorithms

- **Dijkstra** - O((V + E) log V) shortest paths (non-negative weights)
- **Bellman-Ford** - O(VE) shortest paths (handles negative weights)
- **Floyd-Warshall** - O(V³) all-pairs shortest paths
- **Prim/Kruskal** - O(E log V) minimum spanning tree

### Dynamic Programming Classics

- **Fibonacci** - O(n) vs. O(2ⁿ) naive recursion
- **Knapsack** - O(nW) pseudo-polynomial
- **Longest Common Subsequence** - O(mn)
- **Edit Distance** - O(mn)

## Resources

### Quick Learning

- **"Big-O Cheat Sheet"** - Common complexity classes
- **Visualgo** - Algorithm animations
- **LeetCode Patterns** - Common problem types

### Deep Dive

- **"Introduction to Algorithms"** (CLRS) - Comprehensive reference
- **"The Algorithm Design Manual"** - Practical guide with problem catalog
- **"Grokking Algorithms"** - Visual introductions

### Online Practice

- **LeetCode** - Interview-style problems
- **Codeforces** - Competitive programming
- **Project Euler** - Mathematical computing challenges

## Common Patterns

### Pattern: Preprocessing

Invest O(n log n) preprocessing to enable O(log n) queries. Example: Sort array once to enable binary search.

### Pattern: Space-Time Trade-off

Use O(n) space (hash table, memoization) to reduce O(2ⁿ) to O(n). Common in dynamic programming.

### Pattern: Divide and Conquer

Break O(n²) problems into O(n log n) by dividing in half. Examples: merge sort, fast Fourier transform.

### Pattern: Greedy vs. Dynamic Programming

Greedy (local optimal): O(n log n) when it works. Dynamic programming (global optimal): O(n²) or worse but guaranteed correct.

### Pattern: Amortization

Operation appears expensive but averages to O(1). Examples: dynamic array doubling, splay trees.

## Red Flags

**Warning Signs:**

- O(2ⁿ) or O(n!) with n > 20
- O(n²) with n > 10,000
- Claiming to solve NP-complete problem in polynomial time
- Nested loops where O(n log n) or O(n) exists
- Not considering input size growth
- Ignoring space complexity
- Sorting repeatedly instead of once

## Integration Tips

Combine with other skills:

- **Physicist** - Computational complexity connects to entropy and energy
- **Systems Thinker** - Distributed systems theory
- **Engineer** - Practical algorithm implementation
- **Cybersecurity** - Cryptographic hardness assumptions
- **Data Scientist** - Algorithm selection for ML pipelines

## Success Metrics

You've done this well when:

- Time and space complexity are explicitly stated
- Scalability to production data sizes is verified
- NP-complete problems are identified early
- Appropriate data structures chosen for operations
- CAP theorem trade-offs are understood for distributed systems
- Algorithm choice is justified by complexity analysis
- Optimization targets algorithmic improvements first
- Lower bounds and theoretical limits are considered
- Constant factors are considered when they dominate
