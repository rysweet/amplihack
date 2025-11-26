"""Tests for the public API exports from amplihack.utils."""

import unittest


class TestUtilsPublicAPI(unittest.TestCase):
    """Test that utilities are properly exported from amplihack.utils."""

    def test_slugify_importable_from_utils(self):
        """Test that slugify can be imported from amplihack.utils."""
        from amplihack.utils import slugify

        self.assertTrue(callable(slugify))

    def test_slugify_in_all(self):
        """Test that slugify is in amplihack.utils.__all__."""
        from amplihack import utils

        self.assertIn("slugify", utils.__all__)

    def test_slugify_basic_functionality(self):
        """Test basic slugify functionality through public API."""
        from amplihack.utils import slugify

        result = slugify("Hello World")
        self.assertEqual(result, "hello-world")


if __name__ == "__main__":
    unittest.main()