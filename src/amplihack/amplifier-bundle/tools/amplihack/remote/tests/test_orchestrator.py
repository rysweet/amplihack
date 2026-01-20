"""Unit tests for orchestrator module."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from ..errors import CleanupError, ProvisioningError
from ..orchestrator import VM, Orchestrator, VMOptions


class TestOrchestrator(unittest.TestCase):
    """Test cases for Orchestrator class."""

    @patch("subprocess.run")
    def test_verify_azlin_installed_success(self, mock_run):
        """Test successful azlin installation check."""
        mock_run.return_value = Mock(returncode=0, stdout="azlin version 1.0.0")

        # Should not raise
        orchestrator = Orchestrator()
        self.assertIsNotNone(orchestrator)

    @patch("subprocess.run")
    def test_verify_azlin_not_installed(self, mock_run):
        """Test error when azlin not installed."""
        mock_run.side_effect = FileNotFoundError()

        with self.assertRaises(ProvisioningError) as ctx:
            Orchestrator()

        self.assertIn("not found", str(ctx.exception))

    @patch("subprocess.run")
    def test_provision_new_vm_success(self, mock_run):
        """Test successful VM provisioning."""
        mock_run.return_value = Mock(returncode=0, stdout="VM created successfully", stderr="")

        orchestrator = Orchestrator(username="testuser")
        options = VMOptions(size="Standard_D2s_v3")

        vm = orchestrator._provision_new_vm(options)

        self.assertIsNotNone(vm)
        self.assertTrue(vm.name.startswith("amplihack-testuser-"))
        self.assertEqual(vm.size, "Standard_D2s_v3")

    @patch("subprocess.run")
    def test_provision_vm_timeout(self, mock_run):
        """Test VM provisioning timeout."""
        import subprocess

        # Mock azlin --version to succeed, then timeout on provision
        def run_side_effect(cmd, **kwargs):
            if "--version" in cmd:
                return Mock(returncode=0, stdout="azlin 1.0.0")
            raise subprocess.TimeoutExpired("azlin new", 600)

        mock_run.side_effect = run_side_effect

        orchestrator = Orchestrator()
        options = VMOptions()

        with self.assertRaises(ProvisioningError) as ctx:
            orchestrator._provision_new_vm(options)

        self.assertIn("timeout", str(ctx.exception).lower())

    @patch("subprocess.run")
    def test_provision_vm_quota_error(self, mock_run):
        """Test VM provisioning quota exceeded."""
        import subprocess

        # Mock azlin --version to succeed, then raise CalledProcessError for quota
        def run_side_effect(cmd, **kwargs):
            if "--version" in cmd:
                return Mock(returncode=0, stdout="azlin 1.0.0")
            raise subprocess.CalledProcessError(1, cmd, stderr="Quota exceeded for VM family")

        mock_run.side_effect = run_side_effect

        orchestrator = Orchestrator()
        options = VMOptions()

        with self.assertRaises(ProvisioningError) as ctx:
            orchestrator._provision_new_vm(options)

        # Should fail fast on quota errors
        self.assertIn("quota", str(ctx.exception).lower())

    @patch("subprocess.run")
    def test_cleanup_vm_success(self, mock_run):
        """Test successful VM cleanup."""
        mock_run.return_value = Mock(returncode=0, stdout="VM deleted")

        orchestrator = Orchestrator()
        vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")

        result = orchestrator.cleanup(vm)

        self.assertTrue(result)
        # Check that cleanup command was called (2 calls: version check + cleanup)
        self.assertEqual(mock_run.call_count, 2)
        self.assertIn("kill", mock_run.call_args[0][0])

    @patch("subprocess.run")
    def test_cleanup_vm_failure(self, mock_run):
        """Test VM cleanup failure."""
        import subprocess

        # Mock azlin --version to succeed, then raise error for cleanup when check=True
        def run_side_effect(cmd, **kwargs):
            if "--version" in cmd:
                return Mock(returncode=0, stdout="azlin 1.0.0")
            # Raise CalledProcessError only if check=True (default behavior of subprocess.run)
            if kwargs.get("check", False):
                raise subprocess.CalledProcessError(1, cmd, stderr="VM not found")
            return Mock(returncode=1, stderr="VM not found")

        mock_run.side_effect = run_side_effect

        orchestrator = Orchestrator()
        vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")

        with self.assertRaises(CleanupError):
            orchestrator.cleanup(vm, force=False)

    @patch("subprocess.run")
    def test_cleanup_vm_force_no_error(self, mock_run):
        """Test forced cleanup doesn't raise on error."""
        import subprocess

        # Mock azlin --version to succeed, then return error for cleanup
        def run_side_effect(cmd, **kwargs):
            if "--version" in cmd:
                return Mock(returncode=0, stdout="azlin 1.0.0")
            # With force=True, check=False, so return failed result instead of raising
            if kwargs.get("check", False):
                raise subprocess.CalledProcessError(1, cmd, stderr="VM not found")
            return Mock(returncode=1, stderr="VM not found")

        mock_run.side_effect = run_side_effect

        orchestrator = Orchestrator()
        vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")

        # Should not raise with force=True
        result = orchestrator.cleanup(vm, force=True)
        self.assertFalse(result)

    @patch("subprocess.run")
    def test_find_reusable_vm_found(self, mock_run):
        """Test finding reusable VM."""
        # Mock azlin list output
        list_output = """NAME                          SIZE              REGION
amplihack-testuser-20251120   Standard_D2s_v3   eastus
other-vm-123                  Standard_D4s_v3   westus
"""

        # Mock azlin --version to succeed, azlin list --json to fail, azlin list to succeed
        def run_side_effect(cmd, **kwargs):
            if "--version" in cmd:
                return Mock(returncode=0, stdout="azlin 1.0.0")
            if "--json" in cmd:
                # JSON not supported, return error
                return Mock(returncode=1, stdout="", stderr="Unknown flag --json")
            if "list" in cmd:
                # Text list succeeds
                return Mock(returncode=0, stdout=list_output, stderr="")
            return Mock(returncode=1, stdout="", stderr="Unknown command")

        mock_run.side_effect = run_side_effect

        orchestrator = Orchestrator(username="testuser")
        options = VMOptions(size="Standard_D2s_v3")

        vm = orchestrator._find_reusable_vm(options)

        self.assertIsNotNone(vm)
        self.assertEqual(vm.name, "amplihack-testuser-20251120")
        self.assertEqual(vm.size, "Standard_D2s_v3")

    @patch("subprocess.run")
    def test_find_reusable_vm_none_found(self, mock_run):
        """Test when no reusable VM found."""
        mock_run.return_value = Mock(returncode=0, stdout="NAME SIZE REGION\n", stderr="")

        orchestrator = Orchestrator()
        options = VMOptions(size="Standard_D2s_v3")

        vm = orchestrator._find_reusable_vm(options)

        self.assertIsNone(vm)

    @patch("subprocess.run")
    def test_provision_or_reuse_with_specific_vm(self, mock_run):
        """Test using specific VM name."""
        list_output = "amplihack-specific-vm Standard_D2s_v3 eastus"
        mock_run.return_value = Mock(returncode=0, stdout=list_output)

        orchestrator = Orchestrator()
        options = VMOptions(vm_name="amplihack-specific-vm")

        vm = orchestrator.provision_or_reuse(options)

        self.assertEqual(vm.name, "amplihack-specific-vm")

    def test_vm_age_calculation(self):
        """Test VM age calculation."""
        created_time = datetime.now() - timedelta(hours=5)
        vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=created_time)

        self.assertAlmostEqual(vm.age_hours, 5.0, delta=0.1)

    def test_parse_azlin_list_text(self):
        """Test parsing text output from azlin list."""
        output = """NAME                          SIZE              REGION
amplihack-ryan-20251120      Standard_D2s_v3   eastus
amplihack-ryan-20251119      Standard_D4s_v3   westus
"""
        orchestrator = Orchestrator()
        vms = orchestrator._parse_azlin_list_text(output)

        self.assertEqual(len(vms), 2)
        self.assertEqual(vms[0].name, "amplihack-ryan-20251120")
        self.assertEqual(vms[0].size, "Standard_D2s_v3")
        self.assertEqual(vms[1].size, "Standard_D4s_v3")


class TestVMOptions(unittest.TestCase):
    """Test cases for VMOptions dataclass."""

    def test_default_options(self):
        """Test default VMOptions values."""
        options = VMOptions()

        self.assertEqual(options.size, "Standard_D2s_v3")
        self.assertIsNone(options.region)
        self.assertIsNone(options.vm_name)
        self.assertFalse(options.no_reuse)
        self.assertFalse(options.keep_vm)

    def test_custom_options(self):
        """Test custom VMOptions values."""
        options = VMOptions(
            size="Standard_D4s_v3", region="westus", vm_name="my-vm", no_reuse=True, keep_vm=True
        )

        self.assertEqual(options.size, "Standard_D4s_v3")
        self.assertEqual(options.region, "westus")
        self.assertEqual(options.vm_name, "my-vm")
        self.assertTrue(options.no_reuse)
        self.assertTrue(options.keep_vm)


if __name__ == "__main__":
    unittest.main()
