"""Tests for simplified profile API - simple names without URI schemes."""

from profile_management.loader import ProfileLoader


class TestSimplifiedProfileAPI:
    """Test simple name profile loading without URI schemes."""

    def test_load_builtin_by_simple_name(self, tmp_path):
        """Test loading built-in profile by simple name."""
        # Setup
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        coding_profile = profiles_dir / "coding.yaml"
        coding_profile.write_text('version: "1.0"\nname: "coding"')

        loader = ProfileLoader(builtin_profiles_dir=profiles_dir)

        # Test
        content = loader.load("coding")
        assert 'name: "coding"' in content

    def test_load_all_builtin_profiles_by_name(self, tmp_path):
        """Test loading all three built-in profiles by simple name."""
        # Setup
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()

        for profile_name in ["all", "coding", "research"]:
            profile_file = profiles_dir / f"{profile_name}.yaml"
            profile_file.write_text(f'version: "1.0"\nname: "{profile_name}"')

        loader = ProfileLoader(builtin_profiles_dir=profiles_dir)

        # Test each profile
        for profile_name in ["all", "coding", "research"]:
            content = loader.load(profile_name)
            assert f'name: "{profile_name}"' in content

    def test_simple_name_with_yaml_extension(self, tmp_path):
        """Test that simple names with .yaml extension work."""
        # Setup
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        all_profile = profiles_dir / "all.yaml"
        all_profile.write_text('version: "1.0"\nname: "all"')

        loader = ProfileLoader(builtin_profiles_dir=profiles_dir)

        # Test
        content = loader.load("all.yaml")
        assert 'name: "all"' in content

    def test_backward_compat_amplihack_scheme(self, tmp_path):
        """Test backward compatibility with amplihack:// URIs."""
        # Setup
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        coding_profile = profiles_dir / "coding.yaml"
        coding_profile.write_text('version: "1.0"\nname: "coding"')

        loader = ProfileLoader(builtin_profiles_dir=profiles_dir)

        # Test both syntaxes return same content
        content_simple = loader.load("coding")
        content_uri = loader.load("amplihack://profiles/coding")
        assert content_simple == content_uri

    def test_file_scheme_still_works(self, tmp_path):
        """Test that file:// scheme continues to work for custom profiles."""
        # Setup
        custom_profile = tmp_path / "custom.yaml"
        custom_profile.write_text('version: "1.0"\nname: "custom"')

        loader = ProfileLoader()

        # Test
        content = loader.load(f"file://{custom_profile}")
        assert 'name: "custom"' in content
