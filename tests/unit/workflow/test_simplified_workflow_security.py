"""
Test suite for security considerations in SIMPLIFIED_WORKFLOW.md.

Tests validate:
- Security Considerations section exists and is comprehensive
- Command injection prevention guidance with examples
- Input validation for file paths
- Secrets protection patterns
- Authentication best practices
- Security review checklist
- Escalation guidance for security incidents
"""

import re
from pathlib import Path

import pytest


@pytest.fixture
def workflow_file():
    """Path to SIMPLIFIED_WORKFLOW.md"""
    return Path(".claude/workflow/SIMPLIFIED_WORKFLOW.md")


@pytest.fixture
def workflow_content(workflow_file):
    """Load workflow file content"""
    assert workflow_file.exists(), f"SIMPLIFIED_WORKFLOW.md not found at {workflow_file}"
    return workflow_file.read_text(encoding="utf-8")


@pytest.fixture
def security_section(workflow_content):
    """Extract Security Considerations section"""
    pattern = r"##\s+Security Considerations.*?(?=##\s+[A-Z]|\Z)"
    match = re.search(pattern, workflow_content, re.DOTALL | re.IGNORECASE)
    assert match, "Security Considerations section not found"
    return match.group(0)


class TestSecuritySectionPresence:
    """Test presence and location of Security Considerations section"""

    def test_security_section_exists(self, workflow_content):
        """Security Considerations section must exist"""
        assert re.search(r"##\s+Security Considerations", workflow_content, re.IGNORECASE), (
            "Missing Security Considerations section"
        )

    def test_security_section_before_best_practices(self, workflow_content):
        """Security section should appear before Best Practices section"""
        security_match = re.search(r"##\s+Security Considerations", workflow_content, re.IGNORECASE)
        practices_match = re.search(r"##\s+Best Practices", workflow_content, re.IGNORECASE)

        if security_match and practices_match:
            assert security_match.start() < practices_match.start(), (
                "Security Considerations should appear before Best Practices"
            )

    def test_security_section_after_steps(self, workflow_content):
        """Security section should appear after all workflow steps"""
        security_match = re.search(r"##\s+Security Considerations", workflow_content, re.IGNORECASE)
        step15_match = re.search(r"##\s+Step 15:", workflow_content)

        if security_match and step15_match:
            assert security_match.start() > step15_match.start(), (
                "Security Considerations should appear after Step 15"
            )


class TestCommandInjectionPrevention:
    """Test command injection prevention guidance"""

    def test_addresses_command_injection(self, security_section):
        """Must address command injection prevention"""
        assert re.search(
            r"command.*injection|injection.*prevent", security_section, re.IGNORECASE
        ), "Must address command injection prevention"

    def test_shows_safe_unsafe_patterns(self, security_section):
        """Must show both safe and unsafe command patterns"""
        # Check for safe/unsafe markers (emoji or text)
        has_safe_marker = bool(re.search(r"✅|SAFE|\bsafe\b", security_section, re.IGNORECASE))
        has_unsafe_marker = bool(
            re.search(r"❌|UNSAFE|DANGEROUS|\bdangerous\b", security_section, re.IGNORECASE)
        )

        assert has_safe_marker, "Must show safe command patterns (✅ or SAFE)"
        assert has_unsafe_marker, "Must show unsafe command patterns (❌ or UNSAFE/DANGEROUS)"

    def test_includes_variable_quoting_guidance(self, security_section):
        """Must include guidance on variable quoting"""
        # Should mention "$VAR" vs $VAR or variable quoting
        assert re.search(r'"\$|variable.*quot|quot.*variable', security_section, re.IGNORECASE), (
            "Must include variable quoting guidance"
        )

    def test_includes_command_examples(self, security_section):
        """Must include actual command examples"""
        # Should have code blocks or command examples with $
        assert re.search(r"```|`.*\$|git|gh|az", security_section), "Must include command examples"


class TestInputValidation:
    """Test input validation guidance"""

    def test_addresses_input_validation(self, security_section):
        """Must address input validation"""
        assert re.search(
            r"input.*validat|validat.*input|path.*validat", security_section, re.IGNORECASE
        ), "Must address input validation"

    def test_addresses_path_traversal(self, security_section):
        """Must address path traversal prevention"""
        # Should mention .. or directory traversal
        assert re.search(
            r"\.\.|path.*traversal|directory.*traversal", security_section, re.IGNORECASE
        ), "Must address path traversal prevention"

    def test_addresses_file_extension_validation(self, security_section):
        """Should address file extension validation"""
        assert re.search(r"extension|file.*type", security_section, re.IGNORECASE), (
            "Should address file extension validation"
        )


class TestSecretsProtection:
    """Test secrets and credentials protection guidance"""

    def test_addresses_secrets_protection(self, security_section):
        """Must address secrets protection"""
        assert re.search(
            r"secret|credential|password|token|API.*key", security_section, re.IGNORECASE
        ), "Must address secrets protection"

    def test_lists_what_not_to_commit(self, security_section):
        """Must list what should never be committed"""
        # Should mention tokens, passwords, keys, or provide examples
        secret_terms = [r"token", r"password", r"API.*key", r"credential"]
        matches = sum(
            1 for term in secret_terms if re.search(term, security_section, re.IGNORECASE)
        )

        assert matches >= 2, (
            f"Must list at least 2 types of secrets to avoid committing (found {matches})"
        )

    def test_provides_safe_alternatives(self, security_section):
        """Must provide safe alternatives for secrets handling"""
        # Should mention environment variables, CLI auth, or vault
        safe_patterns = [r"environment.*variable", r"CLI.*auth", r"vault", r"keychain"]
        matches = sum(
            1 for pattern in safe_patterns if re.search(pattern, security_section, re.IGNORECASE)
        )

        assert matches >= 1, "Must provide at least one safe alternative for secrets handling"


class TestAuthenticationPatterns:
    """Test authentication best practices"""

    def test_addresses_github_cli_auth(self, security_section):
        """Must address GitHub CLI authentication"""
        assert re.search(r"gh.*auth|github.*auth", security_section, re.IGNORECASE), (
            "Must address GitHub CLI authentication"
        )

    def test_addresses_azure_devops_auth(self, security_section):
        """Must address Azure DevOps authentication"""
        assert re.search(r"az.*login|azure.*devops.*auth", security_section, re.IGNORECASE), (
            "Must address Azure DevOps authentication"
        )

    def test_discourages_hardcoded_tokens(self, security_section):
        """Must discourage hardcoded tokens"""
        assert re.search(
            r"not.*hardcod|never.*hardcod|avoid.*hardcod", security_section, re.IGNORECASE
        ), "Must discourage hardcoded tokens"


class TestPRCleanlinessSecurityEnhancement:
    """Test enhanced PR cleanliness for security-sensitive files"""

    def test_addresses_security_sensitive_artifacts(self, security_section):
        """Must address security-sensitive temporary artifacts"""
        # Should mention investigation files, CVE docs, confidential files
        sensitive_patterns = [r"INVESTIGATION", r"CVE", r"CONFIDENTIAL", r"security.*artifact"]
        matches = sum(
            1
            for pattern in sensitive_patterns
            if re.search(pattern, security_section, re.IGNORECASE)
        )

        assert matches >= 1, "Must address security-sensitive temporary artifacts"

    def test_specifies_handling_security_artifacts(self, security_section):
        """Must specify how to handle security-sensitive artifacts"""
        # Should mention moving to logs, deleting, or not committing
        assert re.search(
            r"move.*logs|delete|not.*commit|remove", security_section, re.IGNORECASE
        ), "Must specify handling of security artifacts"


class TestSecurityReviewChecklist:
    """Test security review checklist"""

    def test_includes_security_checklist(self, security_section):
        """Must include security review checklist"""
        # Check for checklist format or enumerated items
        has_checklist = bool(
            re.search(r"- \[|checklist|review.*list", security_section, re.IGNORECASE)
        )
        has_enumerated = bool(re.search(r"\d+\.\s+", security_section))

        assert has_checklist or has_enumerated, "Must include security review checklist"

    def test_checklist_covers_secrets(self, security_section):
        """Security checklist must cover secrets scanning"""
        assert re.search(r"secret|credential|password.*check", security_section, re.IGNORECASE), (
            "Security checklist must cover secrets"
        )

    def test_checklist_covers_urls(self, security_section):
        """Security checklist should cover internal URLs"""
        assert re.search(
            r"internal.*URL|URL.*internal|private.*URL", security_section, re.IGNORECASE
        ), "Security checklist should cover internal URLs"

    def test_checklist_covers_customer_data(self, security_section):
        """Security checklist should cover customer data"""
        assert re.search(
            r"customer.*data|real.*data|production.*data", security_section, re.IGNORECASE
        ), "Security checklist should cover customer data"


class TestEscalationGuidance:
    """Test security incident escalation guidance"""

    def test_includes_escalation_guidance(self, security_section):
        """Must include security escalation guidance"""
        assert re.search(
            r"escalat|security.*team|report.*security", security_section, re.IGNORECASE
        ), "Must include escalation guidance"

    def test_specifies_when_to_escalate(self, security_section):
        """Must specify when to escalate to security team"""
        # Should mention scenarios like leaked secrets, vulnerabilities
        escalation_scenarios = [r"leak|secret.*commit|vulnerability|security.*issue"]
        matches = sum(
            1
            for scenario in escalation_scenarios
            if re.search(scenario, security_section, re.IGNORECASE)
        )

        assert matches >= 1, "Must specify scenarios requiring escalation"

    def test_includes_immediate_actions_for_leaks(self, security_section):
        """Must include immediate actions if secrets are leaked"""
        assert re.search(r"immediate|rotate|revoke|invalidate", security_section, re.IGNORECASE), (
            "Must include immediate actions for secret leaks"
        )


class TestCommandSafetyExamples:
    """Test command safety example patterns"""

    def test_uses_double_dash_separator(self, security_section):
        """Should demonstrate -- separator for git commands"""
        # Check for -- in command examples
        assert re.search(r"--\s+", security_section), "Should demonstrate -- separator usage"

    def test_demonstrates_safe_commit_messages(self, security_section):
        """Should demonstrate safe commit message patterns"""
        # Should show -F flag or proper quoting
        assert re.search(r"-F\s+|commit.*message.*quot", security_section, re.IGNORECASE), (
            "Should demonstrate safe commit message patterns"
        )


class TestSecurityIntegrationWithSteps:
    """Test security guidance integration with workflow steps"""

    def test_step10_references_security(self, workflow_content):
        """Step 10 should reference security considerations"""
        step10_pattern = r"##\s+Step 10:.*?(?=##\s+Step \d+:|##\s+[^S])"
        step10_match = re.search(step10_pattern, workflow_content, re.DOTALL)

        if step10_match:
            step10 = step10_match.group(0)
            assert re.search(r"security|secret|credential", step10, re.IGNORECASE), (
                "Step 10 should reference security considerations"
            )

    def test_step11_has_safe_command_examples(self, workflow_content):
        """Step 11 should use safe command patterns in examples"""
        step11_pattern = r"##\s+Step 11:.*?(?=##\s+Step \d+:|##\s+[^S])"
        step11_match = re.search(step11_pattern, workflow_content, re.DOTALL)

        if step11_match:
            step11 = step11_match.group(0)
            # If it has git commit examples, they should be safe
            if re.search(r"git commit", step11):
                # Should use -F flag or proper quoting
                assert re.search(r'git commit.*-F|git commit.*-m\s+"', step11), (
                    "Step 11 git commit examples should use safe patterns"
                )

    def test_step14_validates_no_sensitive_info(self, workflow_content):
        """Step 14 should validate examples don't expose sensitive info"""
        step14_pattern = r"##\s+Step 14:.*?(?=##\s+Step \d+:|##\s+[^S])"
        step14_match = re.search(step14_pattern, workflow_content, re.DOTALL)

        if step14_match:
            step14 = step14_match.group(0)
            # Should mention checking for internal infrastructure details
            assert re.search(
                r"internal|infrastructure|sensitive.*info|private.*detail", step14, re.IGNORECASE
            ), "Step 14 should validate no sensitive information exposure"
