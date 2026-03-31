---- MODULE DistributedRetrievalBestEffort ----
EXTENDS FiniteSets, Naturals, Sequences, TLC

\* Refined spec modeling the ACTUAL hive mind implementation semantics.
\* Unlike DistributedRetrievalContract.tla (which requires strict completion),
\* this spec models the best-effort collection pattern used in production:
\*   - Shard failures are logged but do not prevent completion
\*   - Partial results are returned (better than nothing)
\*   - Deterministic merge of whatever did respond
\*
\* This captures what distributed_hive_graph.py actually guarantees.

CONSTANTS Agents, Questions, Facts, NullQuestion

ASSUME Agents # {}
ASSUME NullQuestion \notin Questions

VARIABLES
    activeAgents,
    originalQuestion,
    normalizedQuery,
    shardResults,
    respondedAgents,
    failedAgents,
    mergedResult,
    phase

vars ==
    << activeAgents, originalQuestion, normalizedQuery, shardResults, respondedAgents,
       failedAgents, mergedResult, phase >>

EmptyResults == [a \in Agents |-> {}]

SeqToSet(seq) == {seq[i] : i \in 1..Len(seq)}

RECURSIVE CanonicalizeSet(_)
CanonicalizeSet(factSet) ==
    IF factSet = {} THEN <<>>
    ELSE LET chosen == CHOOSE f \in factSet : TRUE
         IN <<chosen>> \o CanonicalizeSet(factSet \ {chosen})

Init ==
    /\ activeAgents \in SUBSET Agents
    /\ activeAgents # {}
    /\ originalQuestion = NullQuestion
    /\ normalizedQuery = NullQuestion
    /\ shardResults = EmptyResults
    /\ respondedAgents = {}
    /\ failedAgents = {}
    /\ mergedResult = <<>>
    /\ phase = "idle"

StartRequest(q, nq) ==
    /\ phase = "idle"
    /\ q \in Questions
    /\ nq \in Questions
    /\ originalQuestion' = q
    /\ normalizedQuery' = nq
    /\ shardResults' = EmptyResults
    /\ respondedAgents' = {}
    /\ failedAgents' = {}
    /\ mergedResult' = <<>>
    /\ phase' = "dispatch"
    /\ UNCHANGED activeAgents

RecordShardSuccess(a, facts) ==
    /\ phase = "dispatch"
    /\ a \in activeAgents
    /\ a \notin respondedAgents   \* Each agent responds at most once
    /\ a \notin failedAgents
    /\ facts \subseteq Facts
    /\ shardResults' = [shardResults EXCEPT ![a] = facts]
    /\ respondedAgents' = respondedAgents \cup {a}
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, failedAgents,
                   mergedResult, phase>>

RecordShardFailure(a) ==
    /\ phase = "dispatch"
    /\ a \in activeAgents
    /\ a \notin respondedAgents   \* Each agent responds at most once
    /\ a \notin failedAgents
    /\ failedAgents' = failedAgents \cup {a}
    \* Best-effort: failed shard gets empty result (not tracked as error)
    /\ shardResults' = [shardResults EXCEPT ![a] = {}]
    /\ respondedAgents' = respondedAgents \cup {a}
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery,
                   mergedResult, phase>>

\* The key difference from the strict contract:
\* Merged facts come from whatever responded, including empty sets from failures
RespondedFactsSet ==
    UNION {shardResults[a] : a \in respondedAgents}

CanonicalMerge ==
    CanonicalizeSet(RespondedFactsSet)

AllAgentsAccounted ==
    activeAgents \subseteq (respondedAgents \cup failedAgents)

\* Best-effort completion: allowed even when some agents failed
\* (their empty results are already in shardResults)
CompleteRequest ==
    /\ phase = "dispatch"
    /\ AllAgentsAccounted
    /\ mergedResult' = CanonicalMerge
    /\ phase' = "complete"
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, shardResults,
                   respondedAgents, failedAgents>>

\* Timeout: not all agents responded, but we return what we have
TimeoutRequest ==
    /\ phase = "dispatch"
    /\ ~AllAgentsAccounted
    /\ respondedAgents # {}   \* At least one agent responded
    /\ mergedResult' = CanonicalMerge
    /\ phase' = "complete"
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, shardResults,
                   respondedAgents, failedAgents>>

\* Total failure: no agents responded at all
FailRequest ==
    /\ phase = "dispatch"
    /\ respondedAgents = {}
    /\ failedAgents = activeAgents
    /\ phase' = "failed"
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, shardResults,
                   respondedAgents, failedAgents, mergedResult>>

Reset ==
    /\ phase \in {"complete", "failed"}
    /\ originalQuestion' = NullQuestion
    /\ normalizedQuery' = NullQuestion
    /\ shardResults' = EmptyResults
    /\ respondedAgents' = {}
    /\ failedAgents' = {}
    /\ mergedResult' = <<>>
    /\ phase' = "idle"
    /\ UNCHANGED activeAgents

Next ==
    \/ \E q \in Questions, nq \in Questions :
        StartRequest(q, nq)
    \/ \E a \in activeAgents, facts \in SUBSET Facts :
        RecordShardSuccess(a, facts)
    \/ \E a \in activeAgents :
        RecordShardFailure(a)
    \/ CompleteRequest
    \/ TimeoutRequest
    \/ FailRequest
    \/ Reset

TypeInvariant ==
    /\ activeAgents \subseteq Agents
    /\ originalQuestion \in Questions \cup {NullQuestion}
    /\ normalizedQuery \in Questions \cup {NullQuestion}
    /\ shardResults \in [Agents -> SUBSET Facts]
    /\ respondedAgents \subseteq activeAgents
    /\ failedAgents \subseteq activeAgents
    /\ mergedResult \in Seq(Facts)
    /\ phase \in {"idle", "dispatch", "complete", "failed"}

\* --- INVARIANTS (what the best-effort system actually guarantees) ---

OriginalQuestionPreserved ==
    phase \in {"dispatch", "complete", "failed"} =>
      originalQuestion # NullQuestion

\* Best-effort: completion IS allowed with failures.
\* But merged results must come only from actual responses.
MergedFactsComeFromResponses ==
    phase = "complete" =>
      SeqToSet(mergedResult) = RespondedFactsSet

\* Determinism: same inputs produce same merge regardless of response order
DeterministicMerge ==
    phase = "complete" =>
      mergedResult = CanonicalizeSet(RespondedFactsSet)

\* Failed shards contribute empty results, not garbage
FailedShardsContributeNothing ==
    \A a \in failedAgents : shardResults[a] = {}

\* Total failure only when nobody responded
FailOnlyWhenNoResponses ==
    phase = "failed" => respondedAgents = {}

\* At least partial results when someone responded
PartialResultsWhenPossible ==
    (phase = "complete" /\ respondedAgents # {}) =>
      mergedResult # <<>> \/ RespondedFactsSet = {}

Spec == Init /\ [][Next]_vars

=============================================================================
