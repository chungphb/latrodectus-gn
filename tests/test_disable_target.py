#!/usr/bin/env python3
"""Tests for disable_target functionality."""

from textwrap import dedent
from gn_test_base import GnTestCase


class DisableTargetBasicTest(GnTestCase):
    """Basic disable_target tests."""

    def test_removes_sources(self):
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

    def test_removes_deps(self):
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
        self.assertNinjaNotContains('disabled.ninja', 'helper')

    def test_removes_defines(self):
        """disable_target makes target have no defines."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("disabled") {
              sources = ["main.cc"]
              defines = ["SHOULD_NOT_EXIST=1"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:disabled")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('disabled.ninja', 'SHOULD_NOT_EXIST')

    def test_nonexistent_target(self):
        """disable_target on nonexistent target succeeds silently."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:nonexistent")
        '''))

        self.assertGnGenSucceeds()

    def test_depends_on_disabled(self):
        """Depending on a disabled target fails."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("disabled") {
              sources = ["disabled.cc"]
            }
            group("main") {
              deps = [":disabled"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:disabled")
        '''))

        self.assertGnGenFails("Dependency on disabled target")

    def test_multiple_targets(self):
        """Can disable multiple targets."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("disabled_a") {
              sources = ["a.cc"]
            }
            source_set("disabled_b") {
              sources = ["b.cc"]
            }
            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:disabled_a")
            disable_target("//:disabled_b")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('disabled_a.ninja', 'a.cc')
        self.assertNinjaNotContains('disabled_b.ninja', 'b.cc')

    def test_same_target_twice(self):
        """Disabling the same target multiple times succeeds."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("disabled") {
              sources = ["a.cc"]
            }
            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:disabled")
            disable_target("//:disabled")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('disabled.ninja', 'a.cc')

    def test_disable_dep_and_dependent(self):
        """Disabling both a target and its dependent succeeds."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("dep") {
              sources = ["dep.cc"]
            }
            source_set("dependent") {
              sources = ["dependent.cc"]
              deps = [":dep"]
            }
            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:dep")
            disable_target("//:dependent")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('dep.ninja', 'dep.cc')
        self.assertNinjaNotContains('dependent.ninja', 'dependent.cc')


class DisableTargetLabelNormalizationTest(GnTestCase):
    """Tests for label normalization in disable_target."""

    def test_short_label_normalized(self):
        """Short label like 'target' normalizes to //:target."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("target") {
              sources = ["a.cc"]
            }
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("target")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('target.ninja', 'a.cc')

    def test_default_target_name(self):
        """//subdir normalizes to //subdir:subdir."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("all") {
              deps = ["//subdir:other"]
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            source_set("subdir") {
              sources = ["a.cc"]
            }
            source_set("other") {
              sources = ["b.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//subdir")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('subdir/subdir.ninja', 'a.cc')
        self.assertNinjaContains('subdir/other.ninja', 'b.cc')


class DisableTargetInputValidationTest(GnTestCase):
    """Tests for disable_target input validation (permissive behavior)."""

    def test_single_slash_normalized(self):
        """/target normalizes to //:/target (succeeds with warning)."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("/target")
        '''))

        # GN normalizes /target to //:/target and succeeds (with warning about unused)
        self.assertGnGenSucceedsWithWarning("disable_target")

    def test_double_colon_accepted(self):
        """Labels with multiple colons are accepted as-is."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//target:sub1:sub2")
        '''))

        # GN accepts this malformed label and succeeds (with warning)
        self.assertGnGenSucceedsWithWarning("disable_target")

    def test_double_slashes_in_path(self):
        """Multiple // in path get normalized."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//target//sub1//sub2")
        '''))

        # GN normalizes //target//sub1//sub2 to //target//sub1//sub2:sub2 and succeeds (with warning)
        self.assertGnGenSucceedsWithWarning("disable_target")

    def test_empty_string_normalized(self):
        """Empty string normalizes to //:."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("")
        '''))

        # GN normalizes "" to //: and succeeds (with warning)
        self.assertGnGenSucceedsWithWarning("disable_target")


class DisableTargetWildcardTest(GnTestCase):
    """Tests for wildcard disable_target."""

    def test_wildcard_disables_all(self):
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


class DisableTargetCombineTest(GnTestCase):
    """Tests for combining disable_target with other functions."""

    def test_update_then_disable(self):
        """update_target then disable_target results in disabled target."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("target") {
              sources = ["original.cc"]
            }
            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:target") {
              sources += ["added.cc"]
            }
            disable_target("//:target")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('target.ninja', 'original.cc')
        self.assertNinjaNotContains('target.ninja', 'added.cc')

    def test_disable_then_update(self):
        """disable_target then update_target results in disabled target."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("target") {
              sources = ["original.cc"]
            }
            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:target")
            update_target("//:target") {
              sources += ["added.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('target.ninja', 'original.cc')
        self.assertNinjaNotContains('target.ninja', 'added.cc')

    def test_disable_target_in_disabled_file(self):
        """disable_target on target in disabled file succeeds silently."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        self.write_file('disabled_dir/BUILD.gn', dedent('''
            source_set("target") {
              sources = ["a.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("//disabled_dir/BUILD.gn")
            disable_target("//disabled_dir:target")
        '''))

        self.assertGnGenSucceeds()

    def test_disable_file_with_disabled_targets(self):
        """disable_file on file containing disabled targets succeeds."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            source_set("target") {
              sources = ["a.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//subdir:target")
            disable_file("//subdir/BUILD.gn")
        '''))

        self.assertGnGenSucceeds()

    def test_depends_on_disabled_in_disabled_file(self):
        """Depending on a disabled target in a disabled file fails."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = ["//subdir:target"]
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            source_set("target") {
              sources = ["a.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("//subdir/BUILD.gn")
            disable_target("//subdir:target")
        '''))

        self.assertGnGenFails("Unresolved dependencies")
