#!/usr/bin/env python3
"""Tests for disable_file functionality."""

from textwrap import dedent
from gn_test_base import GnTestCase


class DisableFileBasicTest(GnTestCase):
    """Basic disable_file tests."""

    def test_disable_file_prevents_loading(self):
        """disable_file prevents a BUILD.gn from being loaded."""
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

    def test_disabled_file_targets_not_available(self):
        """Targets in disabled files are not available for deps."""
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
        self.assertGnGenFails()


class DisableFileMultipleTest(GnTestCase):
    """Tests for disabling multiple files."""

    def test_disable_multiple_files(self):
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
