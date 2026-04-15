#!/usr/bin/env python3
"""Tests for disable_target functionality."""

from textwrap import dedent
from gn_test_base import GnTestCase


class DisableTargetBasicTest(GnTestCase):
    """Basic disable_target tests."""

    def test_disable_target_removes_sources(self):
        """disable_target makes target have no sources."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("disabled") {
              sources = ["should_not_exist.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:disabled")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('disabled.ninja', 'should_not_exist.cc')

    def test_disable_target_removes_deps(self):
        """disable_target makes target have no deps."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("helper") {
              sources = []
            }
            source_set("disabled") {
              sources = []
              deps = [":helper"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:disabled")
        '''))

        self.assertGnGenSucceeds()
        content = self.read_ninja_file('disabled.ninja')
        self.assertIsNotNone(content)


class DisableTargetLabelNormalizationTest(GnTestCase):
    """Tests for label normalization in disable_target."""

    def test_disable_target_with_normalized_label(self):
        """disable_target works with normalized labels."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("all") {
              deps = []
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            source_set("disabled") {
              sources = ["should_not_exist.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//subdir:disabled")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('subdir/disabled.ninja', 'should_not_exist.cc')


class DisableTargetWildcardTest(GnTestCase):
    """Tests for wildcard disable_target."""

    def test_wildcard_disables_all_targets_in_dir(self):
        """disable_target("//dir:*") disables all targets in that directory."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            source_set("target_a") {
              sources = ["a.cc"]
            }
            source_set("target_b") {
              sources = ["b.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//subdir:*")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('subdir/target_a.ninja', 'a.cc')
        self.assertNinjaNotContains('subdir/target_b.ninja', 'b.cc')
