# Day-Zero Eval Operator Guide

Use this guide when you want the shortest path from a fresh checkout to a working eval command.

This is a how-to guide. It focuses on which repo to run from, which environment variables to set, and which command to use for each kind of eval.

## What To Run From Which Repo

| Goal                                                                   | Repo                   | Command family                                           |
| ---------------------------------------------------------------------- | ---------------------- | -------------------------------------------------------- |
| Edit the agent runtime and run the thin local wrappers                 | `amplihack`            | `python -m amplihack.eval.*`                             |
| Run the authoritative local eval CLI                                   | `amplihack-agent-eval` | `amplihack-eval run`, `amplihack-eval compare`           |
| Run the distributed Azure runner against an already live hive          | `amplihack-agent-eval` | `python -m amplihack_eval.azure.eval_distributed`        |
| Deploy Azure and run an end-to-end distributed eval                    | `amplihack-agent-eval` | `./run_distributed_eval.sh`                              |
| Orchestrate deploy, monitor, or eval scripts with the Aspire dashboard | `amplihack`            | `dotnet run apphost.cs` from `deploy/azure_hive/aspire/` |

## Bootstrap Both Repos

Clone the two repos next to each other so the wrappers can reference sibling source trees.

```bash
git clone https://github.com/rysweet/amplihack.git
git clone https://github.com/rysweet/amplihack-agent-eval.git
```

Create one shared virtual environment in the main repo, then install both repos into it.

```bash
cd amplihack
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

cd ../amplihack-agent-eval
pip install -e ".[all,dev]"
```

Export the common paths once per shell.

```bash
export AMPLIHACK_SOURCE_ROOT="$(cd ../amplihack && pwd)"
export AMPLIHACK_EVAL_SOURCE_ROOT="$(pwd)"
export PYTHONPATH="${AMPLIHACK_EVAL_SOURCE_ROOT}/src:${AMPLIHACK_SOURCE_ROOT}/src"
```

## Common Prerequisites

Most eval paths need Anthropic access for grading.

```bash
export ANTHROPIC_API_KEY=your_key_here
```

Azure paths also need Azure CLI auth.

```bash
az login
```

## Path 1: Run The Thin Local Wrapper From `amplihack`

Use this when you are editing runtime code in `amplihack` and want to exercise the local wrapper that delegates into `amplihack_eval`.

```bash
cd "${AMPLIHACK_SOURCE_ROOT}"

python -m amplihack.eval.long_horizon_memory \
  --turns 100 \
  --questions 20 \
  --output-dir /tmp/eval-run
```

For multi-seed comparison:

```bash
cd "${AMPLIHACK_SOURCE_ROOT}"

python -m amplihack.eval.long_horizon_multi_seed \
  --turns 100 \
  --questions 20 \
  --seeds 42,123,456,789 \
  --output-dir /tmp/eval-compare
```

The thin wrappers in `amplihack` do not currently expose `--question-set`. If you need `standard` versus `holdout`, use the authoritative `amplihack-agent-eval` CLI or the distributed runner paths below.

Use the progressive suite when you want the L1-L12 surface rather than the long-horizon harness.

```bash
cd "${AMPLIHACK_SOURCE_ROOT}"

python -m amplihack.eval.progressive_test_suite \
  --output-dir /tmp/eval-progressive \
  --runs 3 \
  --grader-votes 3 \
  --sdk mini
```

## Path 2: Run The Authoritative Local CLI From `amplihack-agent-eval`

Use this when you want the packaged eval CLI and report tooling rather than the thin wrappers in the main repo.

```bash
cd "${AMPLIHACK_EVAL_SOURCE_ROOT}"

amplihack-eval run \
  --turns 100 \
  --questions 20 \
  --adapter learning-agent \
  --question-set standard \
  --output-dir /tmp/eval-cli-run
```

Compare multiple seeds or question slices:

```bash
cd "${AMPLIHACK_EVAL_SOURCE_ROOT}"

amplihack-eval compare \
  --seeds 42,123,456,789 \
  --turns 100 \
  --questions 20 \
  --question-set holdout \
  --output-dir /tmp/eval-cli-compare
```

## Path 3: Deploy Azure And Run The End-To-End Distributed Wrapper

Use this when you want one command that deploys the fleet, runs the distributed eval, and writes packaged artifacts with rerun metadata.

```bash
cd "${AMPLIHACK_EVAL_SOURCE_ROOT}"

export HIVE_NAME=amplihive
export HIVE_RESOURCE_GROUP=hive-mind-eval-rg
export HIVE_LOCATION=eastus

./run_distributed_eval.sh \
  --agents 100 \
  --turns 5000 \
  --questions 50 \
  --question-set standard
```

This wrapper:

1. calls `amplihack/deploy/azure_hive/deploy.sh`
2. looks up the Event Hubs connection string
3. runs `python -m amplihack_eval.azure.eval_distributed`
4. writes `eval_report.json`, logs, metadata, and a rerun command bundle

## Path 4: Reuse An Existing Azure Hive

Use this when the fleet is already deployed and you only want another eval run.

```bash
cd "${AMPLIHACK_EVAL_SOURCE_ROOT}"

export SKIP_DEPLOY=1
export HIVE_NAME=amplihive3175e
export HIVE_RESOURCE_GROUP=hive-pr3175-rg

./run_distributed_eval.sh \
  --agents 100 \
  --turns 5000 \
  --questions 50 \
  --question-set holdout
```

## Path 5: Run The Distributed Runner Directly

Use this when you already know the Event Hubs connection string and hub names.
Do not paste the secret directly into the Python command line; load it into a shell
variable first so it does not end up in your shell history or process list.

```bash
cd "${AMPLIHACK_EVAL_SOURCE_ROOT}"

read -rsp "Event Hubs connection string: " EH_CONN && echo

python -m amplihack_eval.azure.eval_distributed \
  --connection-string "$EH_CONN" \
  --input-hub "hive-events-amplihive3175e" \
  --response-hub "eval-responses-amplihive3175e" \
  --agents 100 \
  --agents-per-app 5 \
  --turns 5000 \
  --questions 50 \
  --seed 42 \
  --question-set standard \
  --parallel-workers 1 \
  --question-failover-retries 2 \
  --answer-timeout 0 \
  --output /tmp/eval_report.json

unset EH_CONN
```

## Path 6: Use Aspire To Orchestrate The Scripts Locally

Use this when you want the Aspire dashboard, OTEL wiring, and a local control surface around the existing Python and bash entrypoints.

The AppHost in this repo is a file-based C# AppHost. Launch it from its own directory:

```bash
cd "${AMPLIHACK_SOURCE_ROOT}/deploy/azure_hive/aspire"
dotnet run apphost.cs
```

### Aspire Deploy-Only Flow

This starts the `azure-hive-deploy` executable resource and sends OTEL telemetry to the Aspire dashboard.

```bash
export HIVE_NAME=amplihive
export HIVE_DEPLOYMENT_PROFILE=federated-100
export HIVE_AGENT_COUNT=100
export AMPLIHACK_ASPIRE_ENABLE_AZURE_DEPLOY=true

cd "${AMPLIHACK_SOURCE_ROOT}/deploy/azure_hive/aspire"
dotnet run apphost.cs
```

### Aspire Monitor And Eval Flow

The monitor and eval resources are only added when the Event Hubs connection string and hub names are set.

```bash
read -rsp "Event Hubs connection string: " EH_CONN && echo
export AMPLIHACK_EH_INPUT_HUB="hive-events-amplihive3175e"
export AMPLIHACK_EH_RESPONSE_HUB="eval-responses-amplihive3175e"
export HIVE_AGENT_COUNT=100

export AMPLIHACK_ASPIRE_ENABLE_EVAL_MONITOR=true
export AMPLIHACK_ASPIRE_ENABLE_LONG_HORIZON_EVAL=true
export AMPLIHACK_ASPIRE_EVAL_TURNS=5000
export AMPLIHACK_ASPIRE_EVAL_QUESTIONS=50

cd "${AMPLIHACK_SOURCE_ROOT}/deploy/azure_hive/aspire"
dotnet run apphost.cs

unset EH_CONN
```

### Aspire Security Eval Flow

```bash
read -rsp "Event Hubs connection string: " EH_CONN && echo
export AMPLIHACK_EH_INPUT_HUB="hive-events-amplihive3175e"
export AMPLIHACK_EH_RESPONSE_HUB="eval-responses-amplihive3175e"
export HIVE_AGENT_COUNT=100

export AMPLIHACK_ASPIRE_ENABLE_SECURITY_EVAL=true
export AMPLIHACK_ASPIRE_SECURITY_TURNS=300
export AMPLIHACK_ASPIRE_SECURITY_QUESTIONS=50
export AMPLIHACK_ASPIRE_SECURITY_CAMPAIGNS=12

cd "${AMPLIHACK_SOURCE_ROOT}/deploy/azure_hive/aspire"
dotnet run apphost.cs

unset EH_CONN
```

## Outputs To Expect

| Path                                              | Typical output                                                       |
| ------------------------------------------------- | -------------------------------------------------------------------- |
| `python -m amplihack.eval.progressive_test_suite` | `summary.json` plus per-level score files                            |
| `python -m amplihack.eval.long_horizon_memory`    | `eval_report.json`-style report output                               |
| `amplihack-eval run` or `compare`                 | report directories under your chosen `--output-dir`                  |
| `./run_distributed_eval.sh`                       | `/tmp/eval-results-*` with report, metadata, logs, and rerun command |
| Aspire monitor                                    | `aspire_eval_monitor_progress.json` unless overridden                |

## Common Operator Mistakes

- Running the local wrappers with only `PYTHONPATH=src`, which can import a globally installed `amplihack_eval` instead of the sibling checkout you are editing
- Running the direct Azure runner without the sibling `amplihack` checkout available on `PYTHONPATH`
- Expecting the Aspire AppHost to create monitor or eval resources without `EH_CONN`, `AMPLIHACK_EH_INPUT_HUB`, and `AMPLIHACK_EH_RESPONSE_HUB`
- Treating Aspire as a replacement for the Python eval harness; it is an orchestration layer around the existing scripts

## Related Docs

- [Distributed hive evaluation overview](./EVAL.md)
- [How the eval stack fits together](./EVAL_COMPONENTS.md)
