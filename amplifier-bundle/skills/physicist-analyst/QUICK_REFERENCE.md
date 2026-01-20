# Physicist Analyst - Quick Reference

## TL;DR

Apply physics principles to any domain: first-principles thinking, energy/entropy analysis, order-of-magnitude estimation, scaling laws, conservation principles, and statistical mechanics. Use quantitative reasoning and fundamental physical constraints to analyze systems and evaluate solutions.

## When to Use

**Perfect For:**

- First-principles analysis of complex problems
- Energy efficiency and thermodynamic optimization
- Order-of-magnitude feasibility checks (Fermi problems)
- Scaling analysis (small to large, slow to fast)
- Understanding fundamental constraints and limits
- Technology assessment (computing, energy, materials)
- Quantitative reasoning and estimation
- Systems with conservation laws or symmetries

**Skip If:**

- Problem is purely qualitative or subjective
- Physical constraints are irrelevant
- Seeking social or psychological insights
- No quantitative aspects to analyze

## Core Frameworks

### First-Principles Thinking

Strip problems to fundamental physical laws:

- What are the basic constraints? (energy, entropy, speed of light, uncertainty)
- What assumptions can we eliminate?
- Can we derive from fundamentals rather than analogy?
- What does physics say is possible/impossible?

### Conservation Laws

Identify what must remain constant:

- **Energy**: Cannot be created or destroyed, only transformed
- **Momentum**: Conserved in isolated systems
- **Angular momentum**: Conserved under rotational symmetry
- **Information**: Cannot be destroyed (quantum mechanics)
- **Charge**: Total charge is conserved

### Thermodynamics

Apply the four laws:

1. **Zeroth**: Temperature equilibrium is transitive
2. **First**: Energy is conserved (ΔU = Q - W)
3. **Second**: Entropy always increases (ΔS ≥ 0)
4. **Third**: Cannot reach absolute zero

Every process has efficiency limits and generates waste heat.

### Scaling Laws

Understand how behavior changes with size:

- **Square-cube law**: Surface area ~ L², Volume ~ L³
- **Reynolds number**: Ratio of inertial to viscous forces
- **Computational complexity**: How runtime scales with input size
- **Network effects**: Value scales with users squared (Metcalfe's law)

## Quick Analysis Steps

### Step 1: Identify Physical Quantities (3 min)

- List all relevant physical quantities (energy, power, mass, time, etc.)
- Determine units and dimensions
- Identify what's known vs. unknown
- Note constraints from physics (c, h, k_B)

### Step 2: Apply Conservation Laws (5 min)

- Check energy conservation (input = output + waste)
- Verify momentum/angular momentum if relevant
- Ensure information is not destroyed
- Identify conserved quantities as simplifications

### Step 3: Order-of-Magnitude Estimation (8 min)

- Break problem into estimable factors
- Use typical values and physical constraints
- Multiply to get estimate (don't worry about factors of 2-3)
- Verify dimensional consistency
- Compare to known benchmarks

### Step 4: Check Fundamental Limits (7 min)

- **Energy/thermodynamics**: Carnot efficiency, Landauer limit
- **Speed**: Speed of light (3×10^8 m/s)
- **Quantum**: Heisenberg uncertainty (ΔxΔp ≥ ℏ/2)
- **Information**: Shannon limit, Bekenstein bound
- **Computational**: Polynomial vs. exponential complexity

### Step 5: Scaling Analysis (7 min)

- How does system behave at 10x larger/smaller?
- Identify dominant effects at different scales
- Use dimensional analysis for scaling relations
- Check for regime changes (quantum ↔ classical, laminar ↔ turbulent)

### Step 6: Test Limiting Cases (5 min)

- What happens as key parameter → 0?
- What happens as key parameter → ∞?
- Do results match known physics in these limits?
- Are results continuous and sensible?

## Key Physical Constants

### Fundamental Constants

- **Speed of light**: c = 3.0 × 10^8 m/s
- **Planck constant**: h = 6.6 × 10^-34 J·s, ℏ = h/2π
- **Boltzmann constant**: k_B = 1.4 × 10^-23 J/K
- **Elementary charge**: e = 1.6 × 10^-19 C
- **Gravitational constant**: G = 6.7 × 10^-11 N·m²/kg²

### Useful Numbers

- **Avogadro's number**: N_A = 6.0 × 10^23 mol^-1
- **Gas constant**: R = 8.3 J/(mol·K)
- **Room temperature**: ~300 K, thermal energy k_B T ~ 1/40 eV
- **Landauer limit**: E_min = k_B T ln(2) ~ 3 × 10^-21 J per bit erase

## Famous Fermi Problems

### Example: Piano Tuners in Chicago

- Population: ~3 million people
- Households: ~1 million (3 people/household)
- Pianos: ~100,000 (1 in 10 households)
- Tunings: Once per year
- Time per tuning: 2 hours
- Work year: 2000 hours
- Tunings per tuner: ~1000/year
- **Result**: ~100 piano tuners

### Approach to Any Fermi Problem

1. Clarify the question
2. Break into estimable factors
3. Use round numbers (powers of 10)
4. Don't worry about factor of 2-3 precision
5. Check answer makes intuitive sense

## Resources

### Quick Reference

- **Orders of Magnitude**: Powers of 10 thinking
- **Unit Conversions**: Wolfram Alpha, Google
- **Physical Constants**: NIST database
- **Formulas**: Physics reference handbooks

### Deep Learning

- **"Feynman Lectures on Physics"** - Complete foundation (free online)
- **"Street-Fighting Mathematics"** - Practical estimation (free PDF)
- **"Art of Insight"** - Order-of-magnitude reasoning

### Online Tools

- **Wolfram Alpha** - Calculations and unit conversion
- **Physics Stack Exchange** - Community Q&A
- **NIST** - Physical constants and reference data

## Common Patterns

### Pattern: Energy is Expensive

Moving information costs energy (Landauer limit: ~3×10^-21 J per bit at room temp). Computing at scale requires massive energy. Always consider energy budget.

### Pattern: Square-Cube Law

Surface area grows as L², volume as L³. Small things are all surface, large things are all volume. This governs cooling, strength-to-weight, diffusion, and many biological/engineering phenomena.

### Pattern: Exponential is Unsustainable

Exponential growth always eventually stops (limited resources, physical constraints). Look for where exponential transitions to linear or saturates.

### Pattern: Quantum Matters at Small Scales

Below nanometer scales or at very low temperatures, quantum mechanics dominates. Classical intuition fails. Account for uncertainty, superposition, tunneling.

## Red Flags

**Warning Signs:**

- Claimed efficiency > 100% (violates energy conservation)
- Perpetual motion machines (violates thermodynamics)
- Information destroyed (violates quantum unitarity)
- Faster-than-light communication (violates relativity)
- Exponential scaling assumed indefinitely
- Ignoring waste heat at large scale
- Dimensional inconsistency in equations

## Integration Tips

Combine with other skills:

- **Engineer** - Apply physical limits to engineering design
- **Computer Scientist** - Physical limits of computation
- **Environmentalist** - Thermodynamics of energy systems
- **Economist** - Physical constraints on economic growth
- **Chemist** - Quantum mechanics of chemical bonds

## Success Metrics

You've done this well when:

- Dimensional analysis is consistent
- Conservation laws are verified
- Order-of-magnitude estimates are reasonable
- Limiting cases match known physics
- Fundamental physical constraints are identified
- Scaling behavior is characterized
- Energy/entropy budgets are closed
- Implausible claims are caught by physics reasoning
- Quantitative bounds are established
