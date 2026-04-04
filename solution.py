import re

# ------------------------------------------------------------------
# Utility to resolve an issue number from the output of the
# `step-03-create-issue` step.  The output can be either:
#   * a numeric string (e.g. "123")
#   * a GitHub issue URL (e.g. "https://github.com/user/repo/issues/123")
#   * a GitHub PR URL (e.g. "https://github.com/user/repo/pull/123")
# ------------------------------------------------------------------
def get_issue_number(issue_creation_output: str) -> str:
    """
    Extract the issue number from the raw output produced by the
    `step-03-create-issue` step.

    Parameters
    ----------
    issue_creation_output : str
        The raw text returned by the issue‑creation executable.

    Returns
    -------
    str
        The issue number as a string.

    Raises
    ------
    ValueError
        If the output cannot be parsed into an issue or PR number.
    """
    # Strip whitespace & trailing newlines
    output = issue_creation_output.strip()

    # 1. Plain numeric output (common for CLI \"echo 123\")
    if output.isdigit():
        return output

    # 2. Generic patterns for URLs
    #    Pull request URLs contain /pull/<number>
    pr_match = re.search(r'/pull/(\d+)', output)
    if pr_match:
        # For PRs we can treat the PR number as the issue number
        # for downstream logic that expects a numeric reference.
        return pr_match.group(1)

    #    Issue URLs contain /issues/<number>
    issue_match = re.search(r'/issues/(\d+)', output)
    if issue_match:
        return issue_match.group(1)

    # 3. No recognizable pattern—raise an error
    raise ValueError(
        f"Unable to extract issue number from issue_creation output: {output!r}"
    )


# ------------------------------------------------------------------
# Integration point inside `step-03b-extract-issue-number`
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Example: fetch the raw output from the orchestrator environment
    # This could come from an environment variable, a file, or a
    # subprocess capture.  Replace `raw_output` with the actual source.
    raw_output = os.getenv("ISSUE_CREATION_OUTPUT", "")
    issue_number = get_issue_number(raw_output)
    print(issue_number)  # Or write to the orchestrator DAG output