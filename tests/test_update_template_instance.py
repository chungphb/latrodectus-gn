#!/usr/bin/env python3
"""Tests for update_template_instance functionality."""

from textwrap import dedent
from gn_test_base import GnTestCase


class UpdateTemplateInstanceBasicTest(GnTestCase):
    """Basic update_template_instance tests."""

    def test_adds(self):
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

    def test_overrides(self):
        """update_template_instance can override sources completely."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("override_template") {
              sources = ["original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:override_template") {
              sources = []
              sources = ["override.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('override_template.ninja', 'original.cc')
        self.assertNinjaContains('override_template.ninja', 'override.cc')

    def test_removes(self):
        """update_template_instance can remove sources with -=."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("subtract_template") {
              sources = ["keep.cc", "remove.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:subtract_template") {
              sources -= ["remove.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('subtract_template.ninja', 'keep.cc')
        self.assertNinjaNotContains('subtract_template.ninja', 'remove.cc')


class UpdateTemplateInstanceMultipleTest(GnTestCase):
    """Tests for multiple updates on same template instance."""

    def test_multiple_changes(self):
        """Multiple update_template_instance blocks applied in order."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("multi_template") {
              sources = []
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:multi_template") {
              sources += ["first.cc"]
            }
            update_template_instance("//:multi_template") {
              sources += ["second.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('multi_template.ninja', 'first.cc')
        self.assertNinjaContains('multi_template.ninja', 'second.cc')


class UpdateTemplateInstanceVariablesTest(GnTestCase):
    """Tests for variable access in update_template_instance."""

    def test_accesses_local_variables(self):
        """update_template_instance can access variables defined in template instance."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("var_template") {
              my_prefix = "prefix_"
              sources = ["${my_prefix}original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:var_template") {
              sources += ["${my_prefix}added.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('var_template.ninja', 'prefix_original.cc')
        self.assertNinjaContains('var_template.ninja', 'prefix_added.cc')

    def test_accesses_file_scope_variables(self):
        """update_template_instance cannot access file scope variables."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            file_prefix = "file_"

            template("my_template") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }

            my_template("file_var_template") {
              sources = ["${file_prefix}original.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:file_var_template") {
              sources += ["${file_prefix}added.cc"]
            }
        '''))

        self.assertGnGenFails("Undefined identifier")


class UpdateTemplateInstanceInvokerTest(GnTestCase):
    """Tests for modifying invoker params via update_template_instance."""

    def test_accesses_invoker_params(self):
        """update_template_instance can modify params read by template via invoker."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                sources = invoker.my_sources + ["template_default.cc"]
              }
            }

            my_template("invoker_template") {
              my_sources = ["user.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:invoker_template") {
              my_sources += ["injected.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('invoker_template.ninja', 'user.cc')
        self.assertNinjaContains('invoker_template.ninja', 'injected.cc')
        self.assertNinjaContains('invoker_template.ninja', 'template_default.cc')

    def test_overrides_invoker_params(self):
        """update_template_instance can override params read by template via invoker."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                sources = invoker.my_sources + ["template_default.cc"]
              }
            }

            my_template("invoker_override") {
              my_sources = ["user.cc", "other.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:invoker_override") {
              my_sources = []
              my_sources = ["replaced.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaNotContains('invoker_override.ninja', 'user.cc')
        self.assertNinjaNotContains('invoker_override.ninja', 'other.cc')
        self.assertNinjaContains('invoker_override.ninja', 'replaced.cc')
        self.assertNinjaContains('invoker_override.ninja', 'template_default.cc')

    def test_removes_invoker_params(self):
        """update_template_instance can remove from params read by template via invoker."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                sources = invoker.my_sources + ["template_default.cc"]
              }
            }

            my_template("invoker_remove") {
              my_sources = ["keep.cc", "remove.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:invoker_remove") {
              my_sources -= ["remove.cc"]
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('invoker_remove.ninja', 'keep.cc')
        self.assertNinjaNotContains('invoker_remove.ninja', 'remove.cc')
        self.assertNinjaContains('invoker_remove.ninja', 'template_default.cc')

    def test_overrides_string_param(self):
        """update_template_instance can override a string parameter."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                output_name = invoker.my_output_name
                sources = ["main.cc"]
              }
            }

            my_template("string_test") {
              my_output_name = "original_name"
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:string_test") {
              my_output_name = "modified_name"
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertNinjaContains('string_test.ninja', 'modified_name')
        self.assertNinjaNotContains('string_test.ninja', 'original_name')

    def test_overrides_bool_param(self):
        """update_template_instance can override a boolean parameter."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            template("my_template") {
              source_set(target_name) {
                testonly = invoker.is_test
                sources = ["main.cc"]
              }
            }

            my_template("bool_test") {
              is_test = false
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:bool_test") {
              is_test = true
            }
        '''))

        self.assertGnGenSucceeds()
        # When testonly=true, the ninja file will contain "testonly" pool reference
        content = self.read_ninja_file('bool_test.ninja')
        self.assertIsNotNone(content)
