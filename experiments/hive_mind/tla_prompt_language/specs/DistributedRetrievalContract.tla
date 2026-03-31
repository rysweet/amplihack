---- MODULE DistributedRetrievalContract ----
EXTENDS FiniteSets, Sequences, TLC

\* Scoped target for issue #3497.
\* This spec models the distributed retrieval contract, not a full hive runtime.

CONSTANTS Agents, Questions, Facts, NullQuestion, FactOrder

ASSUME Agents # {}
ASSUME NullQuestion \notin Questions
ASSUME SeqToSet(FactOrder) = Facts
ASSUME Len(FactOrder) = Cardinality(Facts)

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

RECURSIVE FilterBySet(_, _)
FilterBySet(seq, keepSet) ==
    IF seq = <<>> THEN <<>>
    ELSE IF Head(seq) \in keepSet
            THEN <<Head(seq)>> \o FilterBySet(Tail(seq), keepSet)
            ELSE FilterBySet(Tail(seq), keepSet)

Init ==
    /\ activeAgents \subseteq Agents
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
    /\ facts \subseteq Facts
    /\ shardResults' = [shardResults EXCEPT ![a] = facts]
    /\ respondedAgents' = respondedAgents \cup {a}
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, failedAgents,
                   mergedResult, phase>>

RecordShardFailure(a) ==
    /\ phase = "dispatch"
    /\ a \in activeAgents
    /\ failedAgents' = failedAgents \cup {a}
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, shardResults,
                   respondedAgents,
                   mergedResult, phase>>

MergedFactsSet ==
    UNION {shardResults[a] : a \in respondedAgents}

CanonicalMerge ==
    FilterBySet(FactOrder, MergedFactsSet)

AllAgentsAccounted ==
    activeAgents \subseteq (respondedAgents \cup failedAgents)

CompleteRequest ==
    /\ phase = "dispatch"
    /\ AllAgentsAccounted
    /\ failedAgents = {}
    /\ activeAgents \subseteq respondedAgents
    /\ mergedResult' = CanonicalMerge
    /\ phase' = "complete"
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, shardResults,
                   respondedAgents, failedAgents>>

FailRequest ==
    /\ phase = "dispatch"
    /\ failedAgents # {}
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

OriginalQuestionPreserved ==
    phase \in {"dispatch", "complete", "failed"} =>
      originalQuestion # NullQuestion

NoSilentLocalFallback ==
    failedAgents # {} => phase # "complete"

CompleteOnlyAfterAllAgents ==
    phase = "complete" => activeAgents \subseteq respondedAgents /\ failedAgents = {}

MergedFactsComeFromShards ==
    phase = "complete" =>
      /\ mergedResult = CanonicalMerge
      /\ SeqToSet(mergedResult) = MergedFactsSet

Spec == Init /\ [][Next]_vars

=============================================================================
