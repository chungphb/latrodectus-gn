#!/usr/bin/env python3
"""Tests for update_target functionality."""

from textwrap import dedent
from gn_test_base import GnTestCase


class UpdateTargetBasicTest(GnTestCase):
    """Basic update_target tests."""

    def test_update_adds_sources(self):
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

    def test_update_appends_to_existing(self):
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

    def test_update_adds_deps(self):
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

    def test_update_overrides_value(self):
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

    def test_update_removes_existing_source(self):
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

    def test_update_removes_nonexistent_source_fails(self):
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


class UpdateTargetMultipleTest(GnTestCase):
    """Tests for multiple updates on same target."""

    def test_multiple_updates_applied_in_order(self):
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

    def test_multiple_update_blocks_override_sources_last_wins(self):
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

    def test_multiple_update_blocks_subtract_sources_sequentially(self):
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

    def test_label_without_target_name_normalized(self):
        """//foo is normalized to //foo:foo."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("all") {
              deps = ["//subdir"]
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            source_set("subdir") {
              sources = ["original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//subdir:subdir") {
              sources += ["normalized.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('subdir/subdir.ninja', 'normalized.cc')


class UpdateTemplateInstanceTest(GnTestCase):
    """Tests for update_template_instance."""

    def test_update_template_instance(self):
        """update_template_instance modifies template-created targets."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("from_template") {
              sources = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:from_template") {
              sources += ["template_added.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('from_template.ninja', 'template_added.cc')
