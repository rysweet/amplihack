---- MODULE DistributedRetrievalContract ----
EXTENDS FiniteSets, Sequences, TLC

\* Scoped target for issue #3497.
\* This spec models the distributed retrieval contract, not a full hive runtime.

CONSTANTS Agents, Questions, Facts, NullQuestion

ASSUME Agents # {}
ASSUME NullQuestion \notin Questions

VARIABLES
    activeAgents,
    originalQuestion,
    normalizedQuery,
    shardResults,
    failedAgents,
    mergedResult,
    phase

vars ==
    << activeAgents, originalQuestion, normalizedQuery, shardResults,
       failedAgents, mergedResult, phase >>

EmptyResults == [a \in Agents |-> {}]

SeqToSet(seq) == {seq[i] : i \in 1..Len(seq)}

Init ==
    /\ activeAgents \subseteq Agents
    /\ activeAgents # {}
    /\ originalQuestion = NullQuestion
    /\ normalizedQuery = NullQuestion
    /\ shardResults = EmptyResults
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
    /\ failedAgents' = {}
    /\ mergedResult' = <<>>
    /\ phase' = "dispatch"
    /\ UNCHANGED activeAgents

RecordShardSuccess(a, facts) ==
    /\ phase = "dispatch"
    /\ a \in activeAgents
    /\ facts \subseteq Facts
    /\ shardResults' = [shardResults EXCEPT ![a] = facts]
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, failedAgents,
                   mergedResult, phase>>

RecordShardFailure(a) ==
    /\ phase = "dispatch"
    /\ a \in activeAgents
    /\ failedAgents' = failedAgents \cup {a}
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, shardResults,
                   mergedResult, phase>>

ReportedAgents ==
    {a \in activeAgents : shardResults[a] # {}} \cup failedAgents

AllAgentsAccounted ==
    activeAgents \subseteq ReportedAgents

CompleteRequest ==
    /\ phase = "dispatch"
    /\ AllAgentsAccounted
    /\ failedAgents = {}
    /\ mergedResult' \in Seq(Facts)
    /\ SeqToSet(mergedResult') \subseteq
       UNION {shardResults[a] : a \in activeAgents}
    /\ phase' = "complete"
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, shardResults,
                   failedAgents>>

FailRequest ==
    /\ phase = "dispatch"
    /\ failedAgents # {}
    /\ phase' = "failed"
    /\ UNCHANGED <<activeAgents, originalQuestion, normalizedQuery, shardResults,
                   failedAgents, mergedResult>>

Reset ==
    /\ phase \in {"complete", "failed"}
    /\ originalQuestion' = NullQuestion
    /\ normalizedQuery' = NullQuestion
    /\ shardResults' = EmptyResults
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
    /\ failedAgents \subseteq activeAgents
    /\ mergedResult \in Seq(Facts)
    /\ phase \in {"idle", "dispatch", "complete", "failed"}

OriginalQuestionPreserved ==
    [](phase \in {"dispatch", "complete", "failed"} =>
      originalQuestion # NullQuestion)

NoSilentLocalFallback ==
    [](failedAgents # {} => phase # "complete")

CompleteOnlyAfterAllAgents ==
    [](phase = "complete" => AllAgentsAccounted /\ failedAgents = {})

MergedFactsComeFromShards ==
    [](phase = "complete" =>
      SeqToSet(mergedResult) \subseteq UNION {shardResults[a] : a \in activeAgents})

Spec == Init /\ [][Next]_vars

=============================================================================
