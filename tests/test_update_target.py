#!/usr/bin/env python3
"""Tests for update_target functionality."""

from textwrap import dedent
from gn_test_base import GnTestCase


class UpdateTargetBasicTest(GnTestCase):
    """Basic update_target tests."""

    def test_adds_sources(self):
        """update_target can add sources to a target."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("foo") {
              sources = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:foo") {
              sources += ["extra.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('foo.ninja', 'extra.cc')

    def test_appends_to_existing(self):
        """update_target += reads and appends to existing values."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("append") {
              sources = ["original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:append") {
              sources += ["added.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('append.ninja', 'original.cc')
        self.assertNinjaContains('append.ninja', 'added.cc')

    def test_adds_deps(self):
        """update_target can add deps to a target."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("helper") {
              sources = ["helper.cc"]
            }
            source_set("main") {
              sources = ["main.cc"]
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:main") {
              deps += [":helper"]
            }
        '''))

        self.assertGnGenSucceeds()
        build_ninja = self.read_build_ninja()
        self.assertIn('main', build_ninja)
        self.assertIn('helper', build_ninja)

    def test_overrides_value(self):
        """update_target can completely override a value by clearing first."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("override") {
              sources = ["original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:override") {
              sources = []
              sources = ["override.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('override.ninja', 'original.cc')
        self.assertNinjaContains('override.ninja', 'override.cc')

    def test_removes_existing_source(self):
        """update_target -= removes an existing source."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("remove") {
              sources = ["keep.cc", "remove_me.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:remove") {
              sources -= ["remove_me.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('remove.ninja', 'keep.cc')
        self.assertNinjaNotContains('remove.ninja', 'remove_me.cc')

    def test_removes_nonexistent_source_fails(self):
        """update_target -= on nonexistent item causes error."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("remove") {
              sources = ["keep.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:remove") {
              sources -= ["not_exists.cc"]
            }
        '''))

        self.assertGnGenFails("Item not found")

    def test_accesses_target_local_variables(self):
        """update_target block can read variables defined in the target."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("with_var") {
              my_prefix = "prefix_"
              sources = ["${my_prefix}original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:with_var") {
              sources += ["${my_prefix}added.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('with_var.ninja', 'prefix_original.cc')
        self.assertNinjaContains('with_var.ninja', 'prefix_added.cc')

    def test_overrides_target_local_variables(self):
        """update_target block can override variables defined in the target."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("override_var") {
              my_prefix = "old_"
              sources = ["${my_prefix}original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:override_var") {
              my_prefix = "new_"
              sources += ["${my_prefix}added.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('override_var.ninja', 'old_original.cc')
        self.assertNinjaContains('override_var.ninja', 'new_added.cc')

    def test_accesses_file_scope_variables(self):
        """update_target block cannot read variables defined at file scope (only target scope)."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            file_prefix = "file_"
            source_set("file_var") {
              sources = ["${file_prefix}original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:file_var") {
              sources += ["${file_prefix}added.cc"]
            }
        '''))

        self.assertGnGenFails("Undefined identifier")


class UpdateTargetMultipleTest(GnTestCase):
    """Tests for multiple updates on same target."""

    def test_multiple_adds(self):
        """Multiple updates on same target are applied in order."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("multi") {
              sources = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:multi") {
              sources += ["first.cc"]
            }
            update_target("//:multi") {
              sources += ["second.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('multi.ninja', 'first.cc')
        self.assertNinjaContains('multi.ninja', 'second.cc')

    def test_multiple_overrides(self):
        """Multiple update_target blocks overriding sources, last one wins."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("override_multi") {
              sources = ["original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:override_multi") {
              sources = []
              sources = ["first_override.cc"]
            }
            update_target("//:override_multi") {
              sources = []
              sources = ["second_override.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('override_multi.ninja', 'original.cc')
        self.assertNinjaNotContains('override_multi.ninja', 'first_override.cc')
        self.assertNinjaContains('override_multi.ninja', 'second_override.cc')

    def test_multiple_removes(self):
        """Multiple update_target blocks each removing a source sequentially."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("subtract_multi") {
              sources = ["keep.cc", "remove1.cc", "remove2.cc", "remove3.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:subtract_multi") {
              sources -= ["remove1.cc"]
            }
            update_target("//:subtract_multi") {
              sources -= ["remove2.cc"]
            }
            update_target("//:subtract_multi") {
              sources -= ["remove3.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('subtract_multi.ninja', 'keep.cc')
        self.assertNinjaNotContains('subtract_multi.ninja', 'remove1.cc')
        self.assertNinjaNotContains('subtract_multi.ninja', 'remove2.cc')
        self.assertNinjaNotContains('subtract_multi.ninja', 'remove3.cc')


class UpdateTargetLabelNormalizationTest(GnTestCase):
    """Tests for label normalization in update_target."""

    def test_short_label_normalized(self):
        """Short label like 'target' normalizes to //:target."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("target") {
              sources = ["original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("target") {
              sources += ["added.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('target.ninja', 'original.cc')
        self.assertNinjaContains('target.ninja', 'added.cc')

    def test_default_target_name(self):
        """//dir is normalized to //dir:dir (default target)."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("all") {
              deps = ["//subdir", "//subdir:other"]
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            source_set("subdir") {
              sources = ["default.cc"]
            }
            source_set("other") {
              sources = ["other.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//subdir") {
              sources += ["normalized.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('subdir/subdir.ninja', 'normalized.cc')
        self.assertNinjaNotContains('subdir/other.ninja', 'normalized.cc')


class UpdateTargetInputValidationTest(GnTestCase):
    """Tests for update_target input validation (permissive behavior)."""

    def test_single_slash_normalized(self):
        """/target normalizes to //:/target (succeeds with warning)."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("/target") {
              sources = []
            }
        '''))

        # GN normalizes /target to //:/target and succeeds (with warning about unused)
        self.assertGnGenSucceedsWithWarning("update_target")

    def test_double_colon_accepted(self):
        """Labels with multiple colons are accepted as-is."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//target:sub1:sub2") {
              sources = []
            }
        '''))

        # GN accepts this malformed label and succeeds (with warning)
        self.assertGnGenSucceedsWithWarning("update_target")

    def test_double_slashes_in_path(self):
        """Multiple // in path get normalized."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//target//sub1//sub2") {
              sources = []
            }
        '''))

        # GN normalizes and succeeds (with warning)
        self.assertGnGenSucceedsWithWarning("update_target")

    def test_empty_string_normalized(self):
        """Empty string normalizes to //:."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("") {
              sources = []
            }
        '''))

        # GN normalizes "" to //: and succeeds (with warning)
        self.assertGnGenSucceedsWithWarning("update_target")

    def test_nonexistent_target(self):
        """update_target on nonexistent target succeeds with warning."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:nonexistent") {
              sources += ["added.cc"]
            }
        '''))

        # GN warns about unused update_target but succeeds
        self.assertGnGenSucceedsWithWarning("update_target")
