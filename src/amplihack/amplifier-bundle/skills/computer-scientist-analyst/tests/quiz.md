# Computer Scientist Analyst - Domain Validation Quiz

## Purpose

This quiz validates that the computer scientist analyst applies computational principles correctly, identifies appropriate algorithms and complexity analysis, and provides well-grounded analysis. Each scenario requires demonstration of computer science reasoning, framework application, and evidence-based conclusions.

---

## Scenario 1: Cryptocurrency Blockchain Security Vulnerability

**Event Description**:
A cryptocurrency announces a critical security vulnerability in their proof-of-work blockchain. An attacker controlling 35% of the network's hash power successfully executed a "selfish mining" attack, earning 47% of block rewards over a 72-hour period (vs. expected 35%). The attack works as follows: the attacker mines blocks but doesn't broadcast them immediately, maintaining a private fork. When the honest network finds a block, the attacker reveals their longer private chain, forcing the honest chain to be abandoned. Honest miners' work is wasted, while the attacker keeps their rewards. The cryptocurrency uses SHA-256 hashing with 10-minute average block time and offers no defense mechanism. Total network hash rate is 200 EH/s (exahashes per second).

**Analysis Task**:
Analyze the computer science principles of blockchain security and assess the vulnerability.

### Expected Analysis Elements

- [ ] **Blockchain Fundamentals**:
  - Distributed ledger: replicated across network nodes
  - Consensus mechanism: agreement on transaction order
  - Proof-of-work: computational puzzle solving to propose blocks
  - Longest chain rule: chain with most accumulated work is canonical
  - Immutability: changing history requires redoing work (expensive)

- [ ] **Cryptographic Hash Functions**:
  - SHA-256: one-way function, collision-resistant, deterministic
  - Mining: find nonce such that hash(block header || nonce) < target
  - Difficulty adjustment: target adjusts to maintain 10-minute block time
  - Hash rate: computational power, measured in hashes per second

- [ ] **Selfish Mining Attack Analysis**:
  - Strategy: private mining + strategic revelation
  - Network propagation delay exploited: attacker reveals at opportune times
  - Threshold: profitable at >33% hash power (Eyal & Sirer, 2013)
  - 35% hash power → 47% rewards: matches theoretical predictions
  - Honest miners waste work on orphaned blocks

- [ ] **Game Theory and Incentives**:
  - Nash equilibrium: selfish mining can be optimal strategy
  - Tragedy of the commons: network security degradation
  - Rational actors: profit-maximizing behavior destabilizes system
  - 51% attack: attacker with majority can rewrite history completely

- [ ] **Computational Complexity**:
  - Hash function: O(1) to compute, but no shortcut to find valid nonce
  - Expected mining time: exponential distribution (memoryless)
  - Attack cost: proportional to hash rate (energy + hardware)
  - Defense cost: increasing hash rate is expensive (electricity, ASICs)

- [ ] **Network Protocol Vulnerabilities**:
  - Block propagation: time for blocks to spread across network (seconds)
  - Network partitions: attacker can manipulate connectivity
  - Timestamp manipulation: slight adjustments to difficulty
  - Eclipse attacks: isolating victim nodes

- [ ] **Mitigation Strategies**:
  - **Protocol changes**: publish timestamps, penalize withholding, random chain selection
  - **Increased decentralization**: make 35% hash power harder to acquire
  - **Alternative consensus**: proof-of-stake (no mining), Byzantine fault tolerance
  - **Monitoring**: detect anomalous orphan block rates
  - **Economic**: adjust block rewards to reduce incentive

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct blockchain, cryptography, consensus mechanism principles
- **Analytical Depth** (0-10): Thoroughness of attack analysis, game theory, mitigation
- **Insight Specificity** (0-10): Clear explanation of vulnerability, specific defenses
- **Historical Grounding** (0-10): References to Eyal & Sirer, 51% attacks, real incidents
- **Reasoning Clarity** (0-10): Logical flow from protocol design to vulnerability

**Minimum Passing Score**: 35/50

---

## Scenario 2: Recommendation Algorithm Bias in Hiring Platform

**Event Description**:
A major hiring platform uses a machine learning model to rank job candidates and recommend top applicants to employers. An investigation reveals the algorithm is biased: women are ranked 30% lower than equally qualified men for technical roles. Analysis of the training data shows it contained 10 years of historical hiring decisions, during which technical roles were 85% male. The model learned to associate male-gendered words (e.g., "executed," "led") with successful candidates. The algorithm uses a neural network with 50 million parameters, trained on 5 million historical hiring decisions. The company claims the algorithm is "objective" because it doesn't explicitly use gender as a feature.

**Analysis Task**:
Analyze the computer science principles of algorithmic bias and develop fairness solutions.

### Expected Analysis Elements

- [ ] **Machine Learning Fundamentals**:
  - Supervised learning: learn from labeled examples (hire/no hire decisions)
  - Training objective: minimize prediction error on training data
  - Generalization: apply learned patterns to new data
  - Neural networks: complex non-linear function approximation
  - "Garbage in, garbage out": model learns patterns in training data

- [ ] **Algorithmic Bias Sources**:
  - **Historical bias**: training data reflects past discrimination (85% male)
  - **Representation bias**: underrepresentation of women in training set
  - **Proxy features**: gendered language correlates with gender (learned indirect discrimination)
  - **Label bias**: hiring decisions (labels) contain human bias
  - **Feedback loops**: biased model → biased outcomes → biased future training data

- [ ] **Fairness Definitions (Multiple, Often Conflicting)**:
  - **Demographic parity**: P(hired | female) = P(hired | male)
  - **Equalized odds**: equal true positive and false positive rates across groups
  - **Calibration**: predicted probability matches actual probability within groups
  - **Individual fairness**: similar individuals get similar predictions
  - **Impossibility results**: can't satisfy all fairness criteria simultaneously (except in trivial cases)

- [ ] **Feature Engineering and Proxies**:
  - Not using gender explicitly doesn't ensure fairness
  - Correlated features: name, language, interests can proxy for gender
  - Natural language processing: word embeddings capture gender associations
  - "Executed" vs. "coordinated": historically gendered language in resumes
  - Intersectionality: multiple protected attributes interact

- [ ] **Model Interpretability and Auditing**:
  - Neural networks: "black box" models, hard to interpret
  - Feature importance: which features drive predictions?
  - Counterfactual analysis: how would prediction change if gender flipped?
  - Disparate impact testing: compare outcomes across groups
  - Regular audits: bias can emerge over time as data distribution shifts

- [ ] **Mitigation Strategies**:
  - **Pre-processing**: rebalance training data, remove biased labels
  - **In-processing**: add fairness constraints to training objective
  - **Post-processing**: adjust predictions to achieve fairness criteria
  - **Adversarial debiasing**: train model to predict outcome while being unable to predict protected attribute
  - **Human-in-the-loop**: algorithm assists but doesn't make final decision

- [ ] **Ethical and Legal Context**:
  - Title VII (US): employment discrimination illegal
  - Disparate impact: policies neutral on face but discriminatory in effect
  - EU AI Act: high-risk AI systems require fairness assessments
  - Transparency: explain automated decisions
  - Trade-off: fairness may reduce predictive accuracy (choose priorities)

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct ML principles, bias sources, fairness definitions
- **Analytical Depth** (0-10): Thoroughness of bias mechanisms, mitigation strategies
- **Insight Specificity** (0-10): Clear explanation of proxy features, specific interventions
- **Historical Grounding** (0-10): References to Amazon recruiting AI incident, fairness research
- **Reasoning Clarity** (0-10): Logical flow from training data to bias to solutions

**Minimum Passing Score**: 35/50

---

## Scenario 3: Distributed System Outage - CAP Theorem Trade-offs

**Event Description**:
A global e-commerce platform experiences a major outage during Black Friday sales. The incident began when a network partition separated their US and European data centers for 45 minutes. The system is designed for high availability using a distributed database with multi-region replication. During the partition, the US region continued accepting orders while the EU region independently accepted orders as well. When connectivity restored, the system detected 12,000 conflicting updates (same inventory items sold in both regions, overselling stock by 30%). The reconciliation process took 6 hours, during which checkout was disabled. Post-mortem reveals the system prioritized availability over consistency. Total revenue loss: $50 million.

**Analysis Task**:
Analyze the distributed systems principles and evaluate the architecture trade-offs.

### Expected Analysis Elements

- [ ] **CAP Theorem**:
  - **Consistency**: all nodes see same data at same time (single logical copy)
  - **Availability**: every request receives a response (success or failure)
  - **Partition tolerance**: system continues despite network failures
  - **CAP impossibility**: can only guarantee 2 of 3 during network partition
  - Must choose: CP (sacrifice availability) vs. AP (sacrifice consistency)

- [ ] **Consistency Models**:
  - Strong consistency: reads always return latest write (linearizability)
  - Eventual consistency: given time without updates, all replicas converge
  - Causal consistency: respects cause-effect relationships
  - Trade-off: stronger consistency requires coordination (latency, availability cost)

- [ ] **System Architecture Analysis**:
  - Multi-region replication: copies of data in US and EU
  - During partition: each region acts independently (AP system)
  - Conflict: both regions modified same data (inventory counts)
  - Inventory overselling: classic lost update problem
  - **Critical flaw**: inventory requires strong consistency (can't oversell)

- [ ] **Consensus Algorithms**:
  - Paxos, Raft: achieve consensus in distributed systems
  - Majority quorum: require majority of nodes to agree (CP system)
  - During partition: minority partition becomes unavailable
  - Appropriate for: critical data like inventory, financial transactions
  - Cost: higher latency, reduced availability

- [ ] **Conflict Resolution**:
  - Last-write-wins: simple but loses data
  - Vector clocks: detect concurrent updates
  - CRDTs (Conflict-free Replicated Data Types): mathematically guarantee convergence
  - Application-level: business logic to resolve conflicts (e.g., compensate oversold customers)
  - **Inventory problem**: no automatic resolution (physical constraint)

- [ ] **System Design Recommendations**:
  - **Inventory**: CP system with strong consistency (use consensus, accept unavailability during partition)
  - **Product catalog**: AP system with eventual consistency (can tolerate stale data briefly)
  - **User sessions**: regional (no cross-region coordination needed)
  - Partition inventory: reserve region-specific stock (avoid cross-region conflicts)
  - Circuit breaker: detect partition, gracefully degrade (show "out of stock" vs. oversell)

- [ ] **Trade-offs and Business Context**:
  - Availability priority: makes sense for most e-commerce (uptime > perfect consistency)
  - Inventory exception: overselling causes customer dissatisfaction, refunds, reputation damage
  - Partition rarity: network failures uncommon, but impact catastrophic
  - Cost-benefit: 45-minute unavailability < $50M loss + 6-hour reconciliation

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct CAP theorem, consistency models, consensus principles
- **Analytical Depth** (0-10): Thoroughness of trade-off analysis, architecture evaluation
- **Insight Specificity** (0-10): Clear design recommendations, specific solutions
- **Historical Grounding** (0-10): References to CAP theorem (Brewer), real outages (Amazon, etc.)
- **Reasoning Clarity** (0-10): Logical assessment of trade-offs and appropriate choices

**Minimum Passing Score**: 35/50

---

## Scenario 4: Quantum Algorithm Threat to Cryptographic Security

**Event Description**:
Security researchers warn that advances in quantum computing threaten current cryptographic systems. Shor's algorithm, running on a sufficiently large quantum computer, can factor large numbers and compute discrete logarithms in polynomial time (vs. exponential time for classical computers). This breaks RSA, Diffie-Hellman, and elliptic curve cryptography, which secure most internet communications (HTTPS, VPNs, digital signatures). Current estimates suggest a quantum computer with 4,000-10,000 logical qubits could break 2048-bit RSA in hours. Leading quantum computing efforts have achieved ~1,000 physical qubits (not yet logical qubits with error correction). Projections suggest "Q-day" (when quantum computers can break current encryption) could occur in 10-30 years. "Harvest now, decrypt later" attacks are already underway: adversaries collect encrypted data to decrypt once quantum computers are available.

**Analysis Task**:
Analyze the computational complexity implications and recommend cryptographic transitions.

### Expected Analysis Elements

- [ ] **Computational Complexity Fundamentals**:
  - P: problems solvable in polynomial time (efficient)
  - NP: problems verifiable in polynomial time
  - P vs. NP question: unknown if P = NP
  - Exponential time: intractable for large inputs
  - Quantum complexity classes: BQP (bounded-error quantum polynomial time)

- [ ] **Classical Cryptography Foundations**:
  - RSA: security based on integer factorization hardness
  - Factoring: best classical algorithms (GNFS) take exp(O(n^(1/3))) time
  - 2048-bit RSA: ~2^112 classical security (billions of years to break)
  - Discrete logarithm problem: similar hardness assumption
  - Elliptic curve: smaller keys, same security level (based on discrete log)

- [ ] **Shor's Algorithm Analysis**:
  - Quantum algorithm: factors N in O((log N)³) time (polynomial)
  - Period finding: exploits quantum Fourier transform
  - 2048-bit RSA: solvable in ~hours with sufficient quantum computer
  - Breaks ALL current public-key cryptography based on factoring/discrete log
  - Symmetric crypto (AES): only modest quantum speedup (Grover's algorithm)

- [ ] **Quantum Computing Requirements**:
  - Physical qubits: noisy, error-prone
  - Logical qubits: error-corrected via quantum error correction (requires many physical qubits)
  - Overhead: ~1000-10,000 physical qubits per logical qubit (depending on error rate)
  - Shor's algorithm: requires ~2n logical qubits for n-bit RSA
  - 2048-bit RSA: ~4,000 logical qubits = potentially millions of physical qubits

- [ ] **Post-Quantum Cryptography (PQC)**:
  - Lattice-based: learning with errors (LWE), NTRU
  - Hash-based signatures: Merkle trees, SPHINCS+
  - Code-based: McEliece cryptosystem
  - Multivariate polynomial: Rainbow (broken), others
  - NIST PQC standardization: selected algorithms (2022-2024)

- [ ] **Transition Strategy**:
  - **Timeline**: 10-30 years to Q-day, but 10+ years to transition infrastructure
  - **Urgency**: "Harvest now, decrypt later" threat requires immediate action for long-term secrets
  - **Hybrid approach**: combine classical + PQC (defense in depth)
  - **Cryptographic agility**: design systems to easily swap algorithms
  - **Inventory**: identify all cryptographic dependencies

- [ ] **Risk Assessment**:
  - High-value targets: government secrets, financial records, healthcare data, intellectual property
  - Data lifetime: if data must remain secret for 20+ years, at risk now
  - False alarms: previous "crypto is doomed" predictions (differential cryptanalysis, etc.)
  - Quantum computing uncertainty: timeline highly uncertain, technical challenges remain

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct complexity theory, Shor's algorithm, PQC principles
- **Analytical Depth** (0-10): Thoroughness of threat analysis, transition planning
- **Insight Specificity** (0-10): Clear risk assessment, specific migration strategies
- **Historical Grounding** (0-10): References to NIST PQC, quantum computing progress
- **Reasoning Clarity** (0-10): Logical evaluation of threat timeline and response

**Minimum Passing Score**: 35/50

---

## Scenario 5: Large Language Model Hallucination and Reliability

**Event Description**:
A company deploys a large language model (LLM) for customer service, generating responses to user queries. Within weeks, significant problems emerge: the model confidently provides incorrect information (hallucinations) in 15% of responses, including fabricated product specifications, wrong troubleshooting steps, and non-existent company policies. The model is a 175-billion parameter transformer trained on internet text. When users challenge incorrect answers, the model often doubles down, providing elaborate but false justifications. The company's initial assumption was that larger models would be more reliable, but hallucination rates are higher than smaller models for some query types. Estimated cost of errors: customer churn, support staff correcting AI mistakes, potential safety incidents.

**Analysis Task**:
Analyze the computer science principles of LLM behavior and develop reliability improvements.

### Expected Analysis Elements

- [ ] **Neural Network and Transformer Architecture**:
  - Transformers: attention mechanism, parallel processing, context window
  - Pre-training: predict next token on massive text corpora
  - Autoregressive generation: sample next token, repeat
  - Parameters: learned weights (175B = 175 billion weights)
  - Emergent behavior: capabilities not explicitly programmed

- [ ] **Training Objective and Limitations**:
  - Objective: maximize likelihood of training data
  - No explicit truth/factuality objective (just predict likely text)
  - Correlation vs. causation: learns statistical patterns, not reasoning
  - Memorization: can reproduce training data (including false information)
  - Knowledge cutoff: no information after training date

- [ ] **Hallucination Mechanisms**:
  - Sampling stochasticity: probabilistic generation can produce low-probability but incorrect text
  - Interpolation vs. extrapolation: generates plausible-sounding but false information
  - Confirmation bias: model reinforces initial generation (coherence over accuracy)
  - Lack of uncertainty: expresses high confidence even when uncertain
  - Adversarial examples: slight input variations produce wildly different outputs

- [ ] **Scaling Laws and Emergent Phenomena**:
  - Larger models: better performance on many tasks (power law relationship)
  - But: hallucinations don't monotonically decrease with scale
  - Inverse scaling: some capabilities get worse with size
  - Grokking: sudden capability jumps at certain scales
  - Unpredictability: hard to forecast model behavior

- [ ] **Evaluation and Safety**:
  - Accuracy metrics: precision, recall, F1 (require labeled test data)
  - Factuality benchmarks: TruthfulQA, etc. (LLMs score poorly)
  - Human evaluation: expensive, subjective, doesn't scale
  - Red-teaming: adversarial testing to find failures
  - Deployment challenges: real-world distribution differs from evaluation

- [ ] **Mitigation Strategies**:
  - **Retrieval-augmented generation (RAG)**: ground responses in retrieved documents
  - **Fine-tuning**: train on company-specific data, correct responses
  - **Reinforcement learning from human feedback (RLHF)**: optimize for human preferences
  - **Uncertainty quantification**: model expresses when uncertain (but difficult)
  - **Human-in-the-loop**: AI drafts, human reviews before sending
  - **Constrained generation**: limit to retrieval-based responses (less creative but more accurate)

- [ ] **System Design Principles**:
  - **Don't use LLMs for factual accuracy-critical tasks** (without validation)
  - Appropriate use: creative writing, brainstorming, summarization, style transfer
  - Inappropriate use: medical advice, legal guidance, safety-critical systems (without oversight)
  - Complementary: combine LLM strengths (language) with structured systems (databases, rules)
  - Monitoring: continuous evaluation of deployed model performance

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct neural network, training objective, hallucination mechanisms
- **Analytical Depth** (0-10): Thoroughness of limitations, evaluation, mitigation analysis
- **Insight Specificity** (0-10): Clear explanation of failure modes, specific architectural improvements
- **Historical Grounding** (0-10): References to GPT-3/4, scaling laws, factuality research
- **Reasoning Clarity** (0-10): Logical assessment of appropriate vs. inappropriate use cases

**Minimum Passing Score**: 35/50

---

## Overall Quiz Assessment

### Scoring Summary

| Scenario                       | Max Score | Passing Score |
| ------------------------------ | --------- | ------------- |
| 1. Blockchain Security         | 50        | 35            |
| 2. Algorithmic Bias            | 50        | 35            |
| 3. Distributed Systems Outage  | 50        | 35            |
| 4. Quantum Cryptography Threat | 50        | 35            |
| 5. LLM Hallucination           | 50        | 35            |
| **Total**                      | **250**   | **175**       |

### Passing Criteria

To demonstrate computer scientist analyst competence:

- **Minimum per scenario**: 35/50 (70%)
- **Overall minimum**: 175/250 (70%)
- **Must pass at least 4 of 5 scenarios**

### Evaluation Dimensions

Each scenario is scored on:

1. **Domain Accuracy** (0-10): Correct application of algorithms, complexity, system principles
2. **Analytical Depth** (0-10): Thoroughness and sophistication of technical analysis
3. **Insight Specificity** (0-10): Clear, actionable technical insights and solutions
4. **Historical Grounding** (0-10): Use of empirical data, research papers, real incidents
5. **Reasoning Clarity** (0-10): Logical flow from principles to analysis to recommendations

### What High-Quality Analysis Looks Like

**Excellent (45-50 points)**:

- Applies fundamental computer science principles correctly (algorithms, complexity, systems)
- Provides rigorous algorithmic and complexity analysis
- Considers multiple technical approaches and trade-offs
- Cites research papers, real-world incidents, and empirical evidence
- Clear logical flow from theory to practice to solutions
- Identifies technical constraints and limitations
- Recognizes when theoretical guarantees vs. practical performance differ

**Good (35-44 points)**:

- Applies key CS principles correctly
- Makes reasonable algorithmic and system design assessments
- Considers main technical factors
- References some empirical evidence
- Clear reasoning
- Provides useful technical insights

**Needs Improvement (<35 points)**:

- Misapplies CS principles
- Lacks algorithmic or complexity analysis
- Ignores important technical constraints
- No empirical grounding
- Unclear or illogical reasoning
- Superficial or incorrect technical analysis

---

## Using This Quiz

### For Self-Assessment

1. Attempt each scenario analysis
2. Compare your analysis to expected elements
3. Score yourself honestly on each dimension
4. Identify areas for improvement

### For Automated Testing (Claude Agent SDK)

```python
from claude_agent_sdk import Agent, TestHarness

agent = Agent.load("computer-scientist-analyst")
quiz = load_quiz_scenarios("tests/quiz.md")

results = []
for scenario in quiz.scenarios:
    analysis = agent.analyze(scenario.event)
    score = evaluate_analysis(analysis, scenario.expected_elements)
    results.append({"scenario": scenario.name, "score": score})

assert sum(r["score"] for r in results) >= 175  # Overall passing
assert sum(1 for r in results if r["score"] >= 35) >= 4  # At least 4 scenarios pass
```

### For Continuous Improvement

- Add new scenarios as computer science challenges emerge
- Update expected elements as algorithms and systems evolve
- Refine scoring criteria based on analysis quality patterns
- Use failures to improve computer scientist analyst skill

---

**Quiz Version**: 1.0.0
**Last Updated**: 2025-11-16
**Status**: Production Ready
