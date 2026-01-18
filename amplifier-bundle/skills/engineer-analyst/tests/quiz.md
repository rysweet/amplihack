# Engineer Analyst - Domain Validation Quiz

## Purpose

This quiz validates that the engineer analyst applies engineering principles correctly, identifies technical constraints and failure modes, and provides evidence-based system design analysis. Each scenario requires demonstration of engineering reasoning, quantitative analysis, and safety-critical thinking.

---

## Scenario 1: Bridge Structural Failure Investigation

**Event Description**:
A 45-year-old steel truss bridge carrying 85,000 vehicles daily experiences catastrophic failure during evening rush hour, collapsing into the river below. Thirteen people die, 47 are injured. Preliminary investigation reveals: (1) A critical gusset plate connecting truss members was undersized by 50% (original design error), (2) The bridge underwent deck resurfacing 8 times over its life, adding 20% dead load beyond design specifications, (3) Annual inspections consistently rated the bridge as "fair" condition with minor corrosion noted but no structural concerns flagged, (4) The state DOT had classified the bridge as "structurally deficient" 15 years ago but "functionally adequate," placing it low on replacement priority list, (5) Failure occurred during construction work that concentrated heavy equipment on one span.

**Analysis Task**:
Analyze the bridge failure from an engineering perspective and identify systemic issues.

### Expected Analysis Elements

- [ ] **Structural Analysis and Failure Mechanics**:
  - Gusset plate undersizing: 50% reduction in load-bearing capacity
  - Dead load increase: 20% additional weight from repeated resurfacing (cumulative oversight)
  - Stress concentration: Construction equipment created localized overload
  - Truss behavior: Loss of one member triggers progressive collapse
  - Buckling vs. tensile failure: Compression members vulnerable to buckling
  - Factor of safety erosion: Combination of defects reduced safety margin below 1.0

- [ ] **Design and Construction Phase Failures**:
  - Original design error: Gusset plate undersizing (calculation error or drawing mistake)
  - Design review gaps: Error not caught during plan check
  - Construction quality control: As-built verification
  - Design assumptions: Did not anticipate repeated resurfacing load accumulation
  - Engineering judgment: Conservative design would have provided buffer

- [ ] **Inspection and Maintenance Issues**:
  - Inspector qualifications: Did inspectors have structural analysis expertise?
  - Visual inspection limitations: Gusset plate internal stress not visible
  - Rating system: "Structurally deficient" label did not convey urgency
  - Load rating: Did inspections include load capacity analysis?
  - Corrosion assessment: Minor corrosion noted but not integrated with stress analysis
  - Inspection frequency: Annual adequate for critical infrastructure?

- [ ] **Risk Assessment and Prioritization Failures**:
  - "Structurally deficient but functionally adequate": Confusing classification
  - Replacement prioritization: 85,000 daily vehicles (high consequence) not weighted adequately
  - Budget constraints: Deferred maintenance/replacement due to funding
  - Risk matrix: Probability x consequence not properly evaluated
  - Resilience: No redundancy (single-point failure mode)

- [ ] **Systemic and Institutional Issues**:
  - Aging infrastructure: 45-year-old bridge beyond typical design life (50 years for modern)
  - Underfunding: Infrastructure investment gap
  - Regulatory gaps: No requirement for detailed structural analysis between design and failure
  - Institutional knowledge: Original design error not identified over 45 years
  - Communication failures: Engineer concerns (if any) not escalated to decision-makers

- [ ] **Engineering Ethics and Professional Responsibility**:
  - Public safety: Engineers' paramount obligation (NSPE Code of Ethics)
  - Duty to report: Should inspectors have raised alarms?
  - Whistleblowing: Were concerns suppressed or ignored?
  - Professional liability: Design engineers, inspection engineers, DOT engineers
  - Standard of care: Did engineers meet reasonable standard given era and knowledge?

- [ ] **Lessons and Recommendations**:
  - **Immediate**: Emergency inspections of similar truss bridges with gusset plates
  - **Short-term**: Non-destructive testing (ultrasonic, radiographic) for hidden defects
  - **Long-term**: Structural health monitoring systems (sensors, real-time data)
  - **Systemic**: Increase infrastructure funding, improve inspection protocols
  - **Design**: Redundancy, fail-safe design, higher factors of safety
  - **Institutional**: Better risk communication, prioritize high-traffic bridges

- [ ] **Historical Context**:
  - I-35W Mississippi River Bridge collapse (Minneapolis, 2007): Undersized gusset plates, 13 deaths
  - Tacoma Narrows Bridge (1940): Aerodynamic flutter, design flaw
  - Silver Bridge collapse (1967): Eyebar failure, 46 deaths, led to NBIS
  - Morandi Bridge (Genoa, 2018): Corrosion, maintenance failures, 43 deaths
  - ASCE Infrastructure Report Card: Consistent "D" grades for US bridges
  - Engineering codes: AASHTO LRFD Bridge Design Specifications

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of structural engineering, failure analysis principles
- **Analytical Depth** (0-10): Thoroughness of technical, systemic, and institutional analysis
- **Insight Specificity** (0-10): Clear engineering recommendations, specific design and inspection improvements
- **Historical Grounding** (0-10): References to bridge failures, engineering codes, best practices
- **Reasoning Clarity** (0-10): Logical flow from failure mechanics to root causes to prevention

**Minimum Passing Score**: 35/50

---

## Scenario 2: Software System Critical Failure

**Event Description**:
A major airline's flight booking and check-in system experiences complete failure at 6:00 AM on a Monday, grounding 3,400 flights globally and stranding 450,000 passengers. The system remains down for 14 hours, costing the airline $180 million in direct losses and incalculable reputation damage. Post-incident analysis reveals: (1) A routine database maintenance script contained a logic error that corrupted the primary database, (2) Automated failover to backup database did not occur because backup was in inconsistent state (replication lag undetected), (3) Restoration from backup required 14 hours due to data volume (8TB) and lack of recent recovery rehearsals, (4) The maintenance script had been used successfully 40+ times over 3 years, but this time encountered an edge case with a new data schema deployed 2 weeks prior, (5) Testing of the script with new schema was performed but did not include the specific data pattern that triggered the failure.

**Analysis Task**:
Analyze the software system failure and identify engineering and operational issues.

### Expected Analysis Elements

- [ ] **Failure Analysis and Root Cause**:
  - Immediate cause: Database corruption from maintenance script logic error
  - Underlying cause: Script not validated against new schema edge case
  - Contributing factors: Replication lag, backup inconsistency, slow recovery
  - Failure mode: Single point of failure (primary database)
  - Cascading failure: Backup failover did not work as designed
  - Mean Time To Recovery (MTTR): 14 hours (unacceptable for critical system)

- [ ] **Software Engineering Issues**:
  - Testing gaps: Incomplete test coverage, edge cases not identified
  - Schema change management: Database migration not fully validated with all scripts
  - Code review: Was script change reviewed? Did reviewers have sufficient context?
  - Regression testing: New schema should trigger full regression suite including maintenance scripts
  - Error handling: Script did not detect or gracefully handle unexpected data pattern
  - Idempotency and atomicity: Script should be safe to retry, rollback on error

- [ ] **High Availability and Disaster Recovery Failures**:
  - Single point of failure: Primary database corruption brought down entire system
  - Backup strategy: Replication lag undetected (monitoring gap)
  - Failover mechanism: Automated failover did not work (design or configuration issue?)
  - Backup consistency: Backup in inconsistent state (integrity checks missing)
  - Recovery time objective (RTO): 14 hours far exceeds acceptable for airline operations (target: minutes to hours)
  - Recovery point objective (RPO): Data loss tolerance not met

- [ ] **Operational and DevOps Issues**:
  - Change management: Maintenance script executed without adequate validation
  - Monitoring: Replication lag not detected in real-time
  - Alerting: Backup inconsistency should have triggered alert before failure
  - Runbooks: Was recovery procedure documented and rehearsed?
  - Recovery rehearsals: Lack of recent practice led to slow restoration (muscle memory)
  - Incident response: 14-hour recovery suggests process inefficiencies

- [ ] **Systemic and Organizational Issues**:
  - Risk assessment: Routine maintenance viewed as low-risk (complacency)
  - Production environment: Was maintenance performed during low-traffic window? (No, 6 AM Monday is high traffic)
  - Separation of duties: Who approved script execution?
  - Documentation: Was schema change impact fully documented and communicated?
  - Organizational learning: Have past incidents informed improvements?

- [ ] **Engineering Best Practices Violated**:
  - **Defense in depth**: Multiple layers of protection missing
  - **Redundancy**: Backup should be independent, not rely on same replication
  - **Graceful degradation**: System should continue partial operation during failure
  - **Chaos engineering**: Proactive failure injection to test resilience
  - **Observability**: Insufficient monitoring of system health
  - **Immutable infrastructure**: Database changes should be versioned, reversible

- [ ] **Recommendations**:
  - **Immediate**: Emergency rollback procedures, hot standbys
  - **Short-term**: Comprehensive testing with new schema, fix backup replication
  - **Long-term**: Multi-region redundancy, active-active failover, sub-hour RTO target
  - **Systemic**: Chaos engineering practice, quarterly DR drills, improved monitoring
  - **Cultural**: Blameless post-mortems, learning from failures

- [ ] **Historical Context**:
  - Delta Air Lines outage (2016): Power failure, 2,300 cancellations, $150M loss
  - Southwest Airlines outage (2016): Router failure, 2,000 cancellations
  - British Airways outage (2017): Power surge, 75,000 passengers stranded
  - Facebook outage (2021): BGP misconfiguration, 6-hour global outage
  - AWS S3 outage (2017): Typo in command, cascading failure
  - Netflix Chaos Monkey: Proactive resilience engineering
  - Site Reliability Engineering (SRE): Google's approach to operations

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of software engineering, reliability principles
- **Analytical Depth** (0-10): Thoroughness of technical, operational, organizational analysis
- **Insight Specificity** (0-10): Clear engineering recommendations, specific resilience improvements
- **Historical Grounding** (0-10): References to system failures, SRE practices, reliability patterns
- **Reasoning Clarity** (0-10): Logical flow from failure to root cause to prevention

**Minimum Passing Score**: 35/50

---

## Scenario 3: Chemical Plant Safety Incident

**Event Description**:
A petrochemical plant experiences a runaway exothermic reaction in a reactor vessel, leading to overpressure, vapor release, and explosion. Four workers die, 23 are injured, and 12,000 nearby residents are evacuated. The incident occurs at 2:30 AM during a transition from Batch A (routine) to Batch B (new formulation). Investigation reveals: (1) Operators bypassed a safety interlock to increase throughput, believing it was overly conservative, (2) Temperature monitoring sensors had calibration drift (reading 5°C low), (3) Emergency cooling system activated but was undersized for the heat generation rate of the new formulation, (4) Process Hazard Analysis (PHA) was conducted 6 years ago and not updated for new formulation, (5) Operators were not trained on the new formulation's different reaction kinetics, (6) Alarm fatigue: 40-50 alarms per shift (operators frequently ignored or silenced alarms).

**Analysis Task**:
Analyze the chemical plant incident from a process safety engineering perspective.

### Expected Analysis Elements

- [ ] **Chemical Process Safety Analysis**:
  - Runaway reaction: Exothermic reaction rate exceeded heat removal capacity
  - Thermodynamics: Heat generation vs. heat removal imbalance
  - Reaction kinetics: New formulation had faster reaction rate (higher heat release)
  - Overpressure: Pressure relief system unable to handle vapor generation
  - Consequences: Explosion, toxic vapor release, fire/blast hazards
  - Layers of protection: Multiple safeguards failed (Swiss cheese model)

- [ ] **Immediate Causes**:
  - Sensor calibration drift: Temperature read 5°C low (operators unaware of actual temperature)
  - Cooling system undersized: Emergency cooling inadequate for new formulation
  - Safety interlock bypass: Operators disabled critical safeguard
  - Operator training gap: Not trained on new formulation hazards
  - New formulation: Different reaction kinetics not fully characterized

- [ ] **Systemic Safety Management Failures**:
  - Management of Change (MOC): New formulation introduced without adequate safety review
  - Process Hazard Analysis (PHA): Outdated (6 years old), not updated for new formulation
  - Pre-Startup Safety Review (PSSR): Did not identify cooling system inadequacy
  - Operating procedures: Not updated for new formulation
  - Training: Operators lacked knowledge of new formulation's hazards
  - Maintenance: Sensor calibration program inadequate

- [ ] **Human Factors and Safety Culture**:
  - Normalization of deviance: Interlock bypass routine practice (cultural drift)
  - Production pressure: Throughput prioritized over safety
  - Alarm fatigue: 40-50 alarms/shift desensitized operators to warnings
  - Risk perception: Operators believed interlock was "overly conservative" (misunderstanding of risk)
  - Incident-free period: Complacency from past success
  - Management accountability: Were safety violations tolerated?

- [ ] **Safeguards and Defense in Depth**:
  - **Inherent safety**: Could formulation be less hazardous? (Reduce, substitute)
  - **Passive safeguards**: Pressure relief valves (undersized), vessel design pressure
  - **Active safeguards**: Emergency cooling (inadequate), safety interlocks (bypassed)
  - **Procedural safeguards**: Operating procedures (not updated), training (inadequate)
  - **Administrative safeguards**: PHA (outdated), MOC (not followed)
  - Multiple failures: All layers failed simultaneously (Swiss cheese alignment)

- [ ] **Regulatory and Standards Compliance**:
  - OSHA Process Safety Management (PSM) standard: Violations likely (PHA, training, MOC)
  - EPA Risk Management Program (RMP): Chemical accident prevention
  - Inherently Safer Design: Hierarchy of controls not applied
  - Industry standards: CCPS guidelines, NFPA codes
  - Enforcement: Regulatory inspections missed violations?

- [ ] **Recommendations**:
  - **Immediate**: Halt new formulation until full PHA completed, re-train all operators
  - **Short-term**: Fix sensor calibration, upgrade cooling capacity, alarm rationalization
  - **Long-term**: Safety culture transformation, MOC enforcement, inherent safety redesign
  - **Systemic**: Independent safety audits, behavioral safety programs, leadership accountability

- [ ] **Historical Context**:
  - Bhopal disaster (1984): MIC release, 3,800+ deaths, multiple safeguard failures
  - Texas City refinery explosion (2005): 15 deaths, cost-cutting, safety culture failures
  - Deepwater Horizon (2010): 11 deaths, blowout preventer failure, risk underestimation
  - Fukushima nuclear disaster (2011): Defense in depth failures, external hazard
  - Process Safety Management (PSM): OSHA standard following major chemical accidents
  - Swiss cheese model (James Reason): Layered defenses, alignment of holes leads to accident

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of process safety, chemical engineering principles
- **Analytical Depth** (0-10): Thoroughness of technical, human factors, organizational analysis
- **Insight Specificity** (0-10): Clear safety recommendations, specific safeguard improvements
- **Historical Grounding** (0-10): References to chemical incidents, safety standards, frameworks
- **Reasoning Clarity** (0-10): Logical flow from incident to root causes to prevention

**Minimum Passing Score**: 35/50

---

## Scenario 4: Renewable Energy Grid Integration

**Event Description**:
A regional power grid with 35% renewable energy (25% wind, 10% solar) experiences cascading blackouts affecting 1.2 million customers over a 6-hour period. The incident occurs on a hot summer afternoon when solar generation is high (8 GW) and electricity demand peaks (12 GW). Sequence of events: (1) A sudden weather front causes wind generation to drop from 4 GW to 0.5 GW in 15 minutes, (2) Grid operators command natural gas peaker plants to ramp up, but several plants fail to start due to maintenance issues, (3) Grid frequency drops from 60.00 Hz to 59.85 Hz, triggering automatic load shedding to prevent further instability, (4) Cascading outages occur as transmission lines trip offline due to overloads, (5) Grid restoration takes 6 hours due to complexity of black-start procedures and coordination across multiple utilities.

**Analysis Task**:
Analyze the grid stability incident and renewable energy integration challenges.

### Expected Analysis Elements

- [ ] **Power System Fundamentals**:
  - Grid frequency: 60 Hz in North America (50 Hz Europe), indicates balance of generation-load
  - Frequency drop: 59.85 Hz indicates generation shortfall (demand exceeds supply)
  - Load shedding: Automatic disconnection of load to prevent collapse
  - Cascading failure: Overloaded lines trip, redistributing load to other lines, causing further trips
  - Black-start: Restoration of grid from complete blackout (complex, time-consuming)
  - Inertia: Rotational energy in synchronous generators provides frequency stability

- [ ] **Renewable Energy Variability**:
  - Wind variability: 4 GW to 0.5 GW in 15 minutes (87% reduction)
  - Solar intermittency: Cloud cover, diurnal cycle (zero at night)
  - Forecasting: Weather-dependent, prediction errors
  - Lack of inertia: Wind and solar are inverter-based, don't provide rotational inertia
  - Capacity factor: Wind ~35%, solar ~20% (vs. fossil 85%+)
  - Geographic diversity: Distributed wind reduces correlated variability (but not fully)

- [ ] **Grid Flexibility and Ramping Requirements**:
  - Ramp rate: Speed at which conventional generation can increase output
  - Natural gas peaker plants: Fast-ramping (10-30 min to full power) but failed to start
  - Coal/nuclear: Slow ramping (hours), cannot respond quickly
  - Duck curve: Solar causes net load (demand - renewables) to ramp rapidly in evening
  - 15-minute drop: Extremely fast variability, exceeding grid's ramping capability

- [ ] **Operational and Reliability Issues**:
  - Peaker plant failures: Maintenance backlog, insufficient testing, low capacity factor → reliability issues
  - Inadequate reserves: Not enough spinning reserve or fast-response capacity
  - Transmission congestion: Lines overloaded, triggering protective relays
  - Coordination failures: Multiple utilities, ISOs, need real-time coordination
  - Situational awareness: Grid operators need better visibility into renewable output and forecasts

- [ ] **Solutions - Grid Modernization**:
  - **Energy storage**: Batteries (lithium-ion, flow batteries) provide fast response, smooth variability (4-hour duration typical)
  - **Demand response**: Controllable loads (HVAC, water heaters) reduce demand during shortfall
  - **Grid-scale batteries**: 1-4 hour duration, instant response (0.1 second), provide inertia equivalent
  - **Pumped hydro storage**: Large-scale (GWh), slower response but long duration
  - **Transmission expansion**: Interconnect distant renewables, geographic diversity reduces variability

- [ ] **Solutions - Flexible Generation**:
  - **Natural gas peakers**: Maintain reliability through regular testing, adequate maintenance funding
  - **Combined cycle gas turbines (CCGT)**: Faster ramping than coal, cleaner than simple cycle
  - **Hydrogen combustion turbines**: Zero-carbon dispatchable generation (emerging)
  - **Nuclear SMRs (Small Modular Reactors)**: Load-following capability (future)

- [ ] **Solutions - Advanced Grid Technologies**:
  - **Grid-forming inverters**: Provide synthetic inertia from renewables and batteries
  - **Wide-area monitoring**: Phasor measurement units (PMUs) for real-time grid state
  - **Advanced forecasting**: Machine learning for renewable output prediction (reduce uncertainty)
  - **Microgrids**: Localized grid islands that can operate independently during disturbances
  - **HVDC transmission**: High-voltage DC for long-distance, asynchronous grid interconnection

- [ ] **Policy and Market Design**:
  - Capacity markets: Pay for reliability, not just energy (incentivize peaker maintenance)
  - Ancillary services markets: Value fast-response resources (batteries, demand response)
  - Renewable integration standards: Require renewables to provide grid services
  - Grid interconnection: FERC Order 2023 (US) streamlining interconnection queues
  - Clean energy standards: 100% targets require grid flexibility planning

- [ ] **Historical Context**:
  - California rolling blackouts (2020): Heat wave, insufficient capacity, solar duck curve
  - Texas grid failure (2021): Winter storm, frozen gas plants, wind turbines, demand surge
  - South Australia blackout (2016): High wind penetration, storm, cascading failure
  - Germany Energiewende: 50%+ renewables, grid flexibility investments
  - ERCOT grid: Isolated, limited interconnection, reliability challenges
  - NERC (North American Electric Reliability Corporation): Grid reliability standards

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of power systems, renewable energy engineering
- **Analytical Depth** (0-10): Thoroughness of variability, flexibility, reliability analysis
- **Insight Specificity** (0-10): Clear engineering solutions, specific grid modernization measures
- **Historical Grounding** (0-10): References to grid incidents, renewable integration examples
- **Reasoning Clarity** (0-10): Logical flow from incident to causes to solutions

**Minimum Passing Score**: 35/50

---

## Scenario 5: Autonomous Vehicle Sensor Failure

**Event Description**:
An autonomous vehicle (SAE Level 4) operating in a geofenced urban area strikes and kills a pedestrian crossing mid-block at night. The pedestrian was wearing dark clothing and crossed outside a crosswalk. Investigation reveals: (1) LiDAR sensor failed to detect pedestrian (sensor misclassified pedestrian as non-obstacle due to low reflectivity), (2) Radar detected object but algorithm assigned low confidence (stationary object filtering), (3) Camera system did not detect pedestrian (low light conditions, inadequate illumination), (4) Sensor fusion algorithm weighted LiDAR and camera highly, discounted radar, (5) Vehicle was traveling 35 mph (speed limit), did not brake or swerve, (6) Safety driver was present but inattentive (watching movie on phone), failed to intervene, (7) Emergency braking could have reduced impact to 15 mph if activated 1.5 seconds earlier. Company had 2.5 million miles of testing with no previous serious incidents.

**Analysis Task**:
Analyze the autonomous vehicle incident from a systems engineering and safety perspective.

### Expected Analysis Elements

- [ ] **Sensor Systems and Failure Modes**:
  - LiDAR: Time-of-flight laser ranging, 3D point clouds, misclassified pedestrian (low reflectivity)
  - Radar: Doppler/range, good in low visibility, but filtered out stationary objects
  - Camera: Visual, context-rich, failed in low light despite being sensitive to humans
  - Sensor fusion: Combining multiple sensors should provide redundancy, but algorithm had flawed logic
  - Single-point failure: No single sensor should be able to cause miss-detection

- [ ] **Perception and Decision-Making Failures**:
  - Object classification: LiDAR misclassified pedestrian as "non-obstacle" (training data gap?)
  - Confidence scoring: Radar's detection assigned low confidence, discarded by fusion
  - Sensor weighting: Algorithm over-weighted LiDAR/camera, under-weighted radar
  - Stationary object filtering: Radar filtered out "stationary" objects to reduce false positives (but pedestrian was moving slowly)
  - Algorithm validation: Did testing include dark-clothed pedestrians at night?
  - Edge case: Combination of low reflectivity, low light, mid-block crossing

- [ ] **System Safety and Redundancy**:
  - Defense in depth: Multiple sensors should provide redundancy, but fusion logic negated this
  - Graceful degradation: System should slow/stop when sensor confidence is low
  - Conservative decision-making: Unclear obstacle should trigger cautious behavior (slow down)
  - Fail-safe design: Default to braking when uncertain
  - Operational design domain (ODD): Was night operation in ODD? If so, should be safe.

- [ ] **Human Factors and Safety Driver Role**:
  - Safety driver: Present but inattentive (automation complacency)
  - Monitoring task: Boring, sustained attention difficult (research shows human vigilance decays)
  - Takeover time: 1.5 seconds needed, but safety driver was not monitoring road
  - Level 4 autonomy: System should not require human intervention in ODD (but company still included driver)
  - Liability: Is inattentive safety driver liable? Or company for inadequate monitoring?

- [ ] **Testing and Validation Issues**:
  - 2.5 million miles: Seems extensive, but rare edge cases require billions of miles
  - Scenario coverage: Were dark-clothed pedestrians in low light tested?
  - Simulation: Did virtual testing include this scenario?
  - Test-driven development: Use crash scenarios to expand test suite
  - Statistical significance: Autonomous vehicles must be provably safer than humans (human rate: 1 fatality per 100M miles)

- [ ] **Regulatory and Ethical Considerations**:
  - SAE levels: Level 4 means full autonomy in defined ODD (company's system failed this requirement)
  - NHTSA oversight: Minimal AV regulation in US (self-certification)
  - Public trust: High-profile fatalities erode confidence in AV technology
  - Liability: Is manufacturer liable for algorithm failures? Safety driver for inattention?
  - Trolley problem: Not directly relevant (this was perception failure, not ethical dilemma)

- [ ] **Recommendations**:
  - **Immediate**: Halt operations, investigate all sensor fusion logic, expand test scenarios
  - **Short-term**: Conservative decision-making (brake when uncertain), redundant sensor validation
  - **Long-term**: Remove safety driver (if system is truly L4) or make monitoring task engaging, night operation restrictions if safety cannot be assured
  - **Systemic**: Industry-wide sensor fusion best practices, mandatory scenario testing, independent safety audits

- [ ] **Historical Context**:
  - Uber AV fatality (Tempe, 2018): Pedestrian struck at night, sensor detected but classified incorrectly, safety driver inattentive
  - Tesla Autopilot crashes: Multiple fatalities, L2 system misused as L4/5
  - Waymo: 20M+ miles, no fatalities (as of incident date), extensive simulation
  - NHTSA Standing General Order: Reporting of AV crashes
  - ISO 26262: Functional safety standard for automotive
  - Sensor fusion literature: Bayesian estimation, Kalman filters, multi-hypothesis tracking

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of autonomous systems, sensor fusion, safety engineering
- **Analytical Depth** (0-10): Thoroughness of technical, human factors, validation analysis
- **Insight Specificity** (0-10): Clear engineering recommendations, specific safety improvements
- **Historical Grounding** (0-10): References to AV incidents, safety standards, sensor technologies
- **Reasoning Clarity** (0-10): Logical flow from sensor failure to system design to prevention

**Minimum Passing Score**: 35/50

---

## Overall Quiz Assessment

### Scoring Summary

| Scenario                     | Max Score | Passing Score |
| ---------------------------- | --------- | ------------- |
| 1. Bridge Structural Failure | 50        | 35            |
| 2. Software System Failure   | 50        | 35            |
| 3. Chemical Plant Safety     | 50        | 35            |
| 4. Renewable Energy Grid     | 50        | 35            |
| 5. Autonomous Vehicle Sensor | 50        | 35            |
| **Total**                    | **250**   | **175**       |

### Passing Criteria

To demonstrate engineer analyst competence:

- **Minimum per scenario**: 35/50 (70%)
- **Overall minimum**: 175/250 (70%)
- **Must pass at least 4 of 5 scenarios**

### Evaluation Dimensions

Each scenario is scored on:

1. **Domain Accuracy** (0-10): Correct application of engineering principles and methods
2. **Analytical Depth** (0-10): Thoroughness and sophistication of technical analysis
3. **Insight Specificity** (0-10): Clear, actionable engineering recommendations
4. **Historical Grounding** (0-10): Use of precedents, standards, best practices
5. **Reasoning Clarity** (0-10): Logical flow, coherent technical argument

### What High-Quality Analysis Looks Like

**Excellent (45-50 points)**:

- Applies engineering principles accurately (mechanics, thermodynamics, systems theory)
- Considers technical, human factors, organizational, and regulatory dimensions
- Makes specific, prioritized engineering recommendations with quantitative justification
- Cites relevant failures, standards, and research literature
- Clear logical flow from failure to root cause to prevention
- Acknowledges uncertainties and trade-offs
- Identifies non-obvious failure modes and solutions

**Good (35-44 points)**:

- Applies key engineering concepts correctly
- Considers main technical and safety factors
- Makes reasonable engineering recommendations
- References some precedents or standards
- Clear reasoning
- Provides useful engineering insights

**Needs Improvement (<35 points)**:

- Misapplies engineering concepts or principles
- Ignores critical failure modes or safety factors
- Vague or technically incorrect recommendations
- Lacks grounding in engineering precedents or standards
- Unclear or illogical reasoning
- Superficial technical analysis

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

agent = Agent.load("engineer-analyst")
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

- Add new scenarios as engineering failures occur
- Update expected elements as standards and practices evolve
- Refine scoring criteria based on analyst performance patterns
- Use failures to improve engineer analyst skill

---

**Quiz Version**: 1.0.0
**Last Updated**: 2025-11-16
**Status**: Production Ready
