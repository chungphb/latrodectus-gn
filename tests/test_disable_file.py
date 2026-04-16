#!/usr/bin/env python3
"""Tests for disable_file functionality."""

from textwrap import dedent
from gn_test_base import GnTestCase


class DisableFileBasicTest(GnTestCase):
    """Basic disable_file tests."""

    def test_skips_file_parsing(self):
        """disable_file skips parsing of the BUILD.gn file."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        # This file contains assert(false) which would fail if parsed
        self.write_file('disabled_dir/BUILD.gn', dedent('''
            assert(false, "This file should not be loaded!")
            source_set("should_not_exist") {
              sources = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("//disabled_dir/BUILD.gn")
        '''))

        # Should succeed because disabled_dir/BUILD.gn is never parsed
        self.assertGnGenSucceeds()

    def test_depends_on_target_in_disabled_file(self):
        """Depending on a target in a disabled file fails."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = ["//disabled_dir:target"]
            }
        '''))

        self.write_file('disabled_dir/BUILD.gn', dedent('''
            source_set("target") {
              sources = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("//disabled_dir/BUILD.gn")
        '''))

        # Should fail because the target doesn't exist (file is disabled)
        self.assertGnGenFails("Unresolved dependencies")

    def test_nonexistent_file(self):
        """disable_file on nonexistent file succeeds silently."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("//nonexistent/BUILD.gn")
        '''))

        self.assertGnGenSucceeds()


class DisableFileInputValidationTest(GnTestCase):
    """Tests for disable_file input validation."""

    def test_missing_path_prefix(self):
        """disable_file without // prefix fails with clear error."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("not_a_path")
        '''))

        self.assertGnGenFails("disable_file requires a full path starting with //")

    def test_relative_path(self):
        """disable_file with relative path fails."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("subdir/BUILD.gn")
        '''))

        self.assertGnGenFails("disable_file requires a full path starting with //")


class DisableFileMultipleTest(GnTestCase):
    """Tests for disabling multiple files."""

    def test_multiple_files(self):
        """Can disable multiple files."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        self.write_file('dir1/BUILD.gn', dedent('''
            assert(false, "dir1 should not be loaded!")
        '''))

        self.write_file('dir2/BUILD.gn', dedent('''
            assert(false, "dir2 should not be loaded!")
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("//dir1/BUILD.gn")
            disable_file("//dir2/BUILD.gn")
        '''))

        self.assertGnGenSucceeds()
