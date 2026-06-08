#!/usr/bin/env python3
"""Tests for disable_template_instance functionality."""

from textwrap import dedent
from gn_test_base import GnTestCase


class DisableTemplateInstanceBasicTest(GnTestCase):
    """Basic disable_template_instance tests."""

    def test_removes_sources(self):
        """disable_template_instance makes template instance have no sources."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("disabled") {
              sources = ["should_not_exist.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:disabled")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('disabled.ninja', 'should_not_exist.cc')

    def test_removes_deps(self):
        """disable_template_instance makes template instance have no deps."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            source_set("helper") {
              sources = []
            }

            my_template("disabled") {
              sources = []
              deps = [":helper"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:disabled")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('disabled.ninja', 'helper')

    def test_removes_defines(self):
        """disable_template_instance makes template instance have no defines."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("disabled") {
              sources = ["main.cc"]
              defines = ["SHOULD_NOT_EXIST=1"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:disabled")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('disabled.ninja', 'SHOULD_NOT_EXIST')

    def test_nonexistent_template_instance(self):
        """disable_template_instance on nonexistent target succeeds silently."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:nonexistent")
        '''))

        self.assertGnGenSucceeds()

    def test_depends_on_disabled(self):
        """Depending on a disabled template instance fails."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("disabled") {
              sources = ["disabled.cc"]
            }

            group("main") {
              deps = [":disabled"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:disabled")
        '''))

        self.assertGnGenFails("Dependency on disabled template instance")

    def test_multiple_template_instances(self):
        """Can disable multiple template instances."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("disabled_a") {
              sources = ["a.cc"]
            }

            my_template("disabled_b") {
              sources = ["b.cc"]
            }

            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:disabled_a")
            disable_template_instance("//:disabled_b")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('disabled_a.ninja', 'a.cc')
        self.assertNinjaNotContains('disabled_b.ninja', 'b.cc')

    def test_same_template_instance_twice(self):
        """Disabling the same template instance multiple times succeeds."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("disabled") {
              sources = ["a.cc"]
            }

            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:disabled")
            disable_template_instance("//:disabled")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('disabled.ninja', 'a.cc')

    def test_disable_dep_and_dependent(self):
        """Disabling both a template instance and its dependent succeeds."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("dep") {
              sources = ["dep.cc"]
            }

            my_template("dependent") {
              sources = ["dependent.cc"]
              deps = [":dep"]
            }

            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:dep")
            disable_template_instance("//:dependent")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('dep.ninja', 'dep.cc')
        self.assertNinjaNotContains('dependent.ninja', 'dependent.cc')


class DisableTemplateInstanceLabelNormalizationTest(GnTestCase):
    """Tests for label normalization in disable_template_instance."""

    def test_default_target_name(self):
        """//subdir normalizes to //subdir:subdir."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("all") {
              deps = ["//subdir:other"]
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("subdir") {
              sources = ["a.cc"]
            }

            my_template("other") {
              sources = ["b.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//subdir")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('subdir/subdir.ninja', 'a.cc')
        self.assertNinjaContains('subdir/other.ninja', 'b.cc')


class DisableTemplateInstanceCombineTest(GnTestCase):
    """Tests for combining disable_template_instance with other functions."""

    def test_update_then_disable(self):
        """update_template_instance then disable_template_instance results in disabled."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("target") {
              sources = ["original.cc"]
            }

            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:target") {
              sources += ["added.cc"]
            }
            disable_template_instance("//:target")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('target.ninja', 'original.cc')
        self.assertNinjaNotContains('target.ninja', 'added.cc')

    def test_disable_then_update(self):
        """disable_template_instance then update_template_instance results in disabled."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("target") {
              sources = ["original.cc"]
            }

            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:target")
            update_template_instance("//:target") {
              sources += ["added.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('target.ninja', 'original.cc')
        self.assertNinjaNotContains('target.ninja', 'added.cc')

    def test_disable_template_instance_in_disabled_file(self):
        """disable_template_instance on target in disabled file succeeds silently."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        self.write_file('disabled_dir/BUILD.gn', dedent('''
            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("target") {
              sources = ["a.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("//disabled_dir/BUILD.gn")
            disable_template_instance("//disabled_dir:target")
        '''))

        self.assertGnGenSucceeds()

    def test_disable_file_with_disabled_template_instances(self):
        """disable_file on file containing disabled template instances succeeds."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = []
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("target") {
              sources = ["a.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//subdir:target")
            disable_file("//subdir/BUILD.gn")
        '''))

        self.assertGnGenSucceeds()

    def test_depends_on_disabled_in_disabled_file(self):
        """Depending on a disabled template instance in a disabled file fails."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = ["//subdir:target"]
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("target") {
              sources = ["a.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("//subdir/BUILD.gn")
            disable_template_instance("//subdir:target")
        '''))

        self.assertGnGenFails("Unresolved dependencies")


class DisableTemplateInstanceMixedTest(GnTestCase):
    """Tests for mixing disable_template_instance with disable_target."""

    def test_disable_target_on_template_instance(self):
        """disable_target can disable a template instance."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("target") {
              sources = ["a.cc"]
            }

            group("main") {
              deps = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:target")
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('target.ninja', 'a.cc')

    def test_disable_template_instance_on_regular_target(self):
        """disable_template_instance on regular target still processes it but blocks deps."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            source_set("target") {
              sources = ["a.cc"]
            }
            group("main") {
              deps = [":target"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:target")
        '''))

        # disable_template_instance marks the target as disabled for dependency purposes
        # Even though it's a regular target, depending on it will fail
        self.assertGnGenFails("Dependency on disabled template instance")
