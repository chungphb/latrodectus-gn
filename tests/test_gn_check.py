#!/usr/bin/env python3
"""Tests for gn check functionality.

gn check validates that C++ #include statements match the dependency graph
defined in BUILD.gn files. It ensures that if a source file includes a header,
the target containing that source file has a proper dependency on the target
that provides that header.

These tests verify the behavior of gn check including:
- Basic include validation
- check_includes configuration
- nogncheck annotation
- allow_circular_includes_from
- Public vs private headers
"""

from textwrap import dedent
from gn_test_base import GnTestCase


class GnCheckBasicTest(GnTestCase):
    """Basic tests for gn check include validation."""

    def test_valid_include_with_dependency_passes(self):
        """gn check passes when include has proper dependency."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              deps = [":lib"]
            }

            source_set("lib") {
              sources = ["lib.h", "lib.cc"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
            void lib_func() {}
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_missing_dependency_fails(self):
        """gn check fails when include lacks dependency."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              # Missing deps = [":lib"]
            }

            source_set("lib") {
              sources = ["lib.h", "lib.cc"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
            void lib_func() {}
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckFails("lib.h")

    def test_transitive_dependency_passes(self):
        """gn check passes with transitive (indirect) dependency."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              deps = [":middle"]
            }

            source_set("middle") {
              sources = ["middle.h", "middle.cc"]
              deps = [":lib"]
            }

            source_set("lib") {
              sources = ["lib.h", "lib.cc"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "middle.h"
            int main() { return 0; }
        '''))

        self.write_file('middle.h', dedent('''
            #pragma once
            #include "lib.h"
            void middle_func();
        '''))

        self.write_file('middle.cc', dedent('''
            #include "middle.h"
            void middle_func() { lib_func(); }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
            void lib_func() {}
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_self_include_passes(self):
        """gn check passes when including headers from same target."""
        self.write_file('BUILD.gn', dedent('''
            source_set("lib") {
              sources = ["lib.h", "lib.cc", "internal.h"]
            }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.write_file('internal.h', dedent('''
            #pragma once
            void internal_func();
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
            #include "internal.h"
            void lib_func() { internal_func(); }
            void internal_func() {}
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()


class GnCheckIncludesConfigTest(GnTestCase):
    """Tests for check_includes target configuration."""

    def test_check_includes_false_skips_validation(self):
        """check_includes = false disables include checking for target."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              check_includes = false
              # No deps on :lib, but check_includes = false so it passes
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_check_includes_true_enables_validation(self):
        """check_includes = true (default) enables include checking."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              check_includes = true
              # No deps on :lib, should fail
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckFails("lib.h")


class GnCheckNogncheckTest(GnTestCase):
    """Tests for nogncheck annotation to skip include validation."""

    def test_nogncheck_skips_include_check(self):
        """nogncheck comment annotation skips validation for that include."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              # No deps on :lib, but nogncheck annotation skips check
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"  // nogncheck
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_without_nogncheck_fails(self):
        """Same setup without nogncheck fails."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              # No deps on :lib
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckFails("lib.h")

    def test_nogncheck_with_reason(self):
        """nogncheck with reason comment is also valid."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"  // nogncheck(platform-specific include)
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()


class GnCheckCircularIncludesTest(GnTestCase):
    """Tests for allow_circular_includes_from configuration.

    Note: allow_circular_includes_from allows a target to include headers from
    one of its dependencies, even when that dependency also includes headers
    back from the original target. The build dependencies must NOT be circular
    - only one target depends on the other, but headers can include each other.
    """

    def test_include_from_dep_without_allow_fails(self):
        """Including header from dep that includes back fails without allow."""
        # :a depends on :b, so :a can include b.h
        # But b.h includes a.h, which means :b would need to depend on :a
        # Since :b doesn't depend on :a, this should fail gn check
        self.write_file('BUILD.gn', dedent('''
            source_set("a") {
              sources = ["a.h", "a.cc"]
              deps = [":b"]
              # Missing allow_circular_includes_from
            }

            source_set("b") {
              sources = ["b.h", "b.cc"]
              # No dep on :a - build graph is not circular
            }
        '''))

        self.write_file('a.h', dedent('''
            #pragma once
            void a_func();
        '''))

        self.write_file('a.cc', dedent('''
            #include "a.h"
            #include "b.h"
            void a_func() {}
        '''))

        self.write_file('b.h', dedent('''
            #pragma once
            #include "a.h"  // b.h includes a.h but :b doesn't depend on :a
            void b_func();
        '''))

        self.write_file('b.cc', dedent('''
            #include "b.h"
            void b_func() {}
        '''))

        self.assertGnGenSucceeds()
        # :b includes a.h but doesn't depend on :a - should fail
        self.assertGnCheckFails("a.h")

    def test_allow_circular_includes_from_permits_include(self):
        """allow_circular_includes_from permits dep's headers to include back."""
        # :a depends on :b, and allows :b's headers to include :a's headers
        self.write_file('BUILD.gn', dedent('''
            source_set("a") {
              sources = ["a.h", "a.cc"]
              deps = [":b"]
              allow_circular_includes_from = [":b"]
            }

            source_set("b") {
              sources = ["b.h", "b.cc"]
              # No dep on :a - build graph is not circular
            }
        '''))

        self.write_file('a.h', dedent('''
            #pragma once
            void a_func();
        '''))

        self.write_file('a.cc', dedent('''
            #include "a.h"
            #include "b.h"
            void a_func() {}
        '''))

        self.write_file('b.h', dedent('''
            #pragma once
            #include "a.h"  // Allowed because :a has allow_circular_includes_from = [":b"]
            void b_func();
        '''))

        self.write_file('b.cc', dedent('''
            #include "b.h"
            void b_func() {}
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()


class GnCheckPublicHeadersTest(GnTestCase):
    """Tests for public vs private header validation."""

    def test_public_headers_accessible_from_deps(self):
        """Headers in public are accessible to dependents."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              deps = [":lib"]
            }

            source_set("lib") {
              sources = ["lib.cc"]
              public = ["lib.h"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
            void lib_func() {}
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_private_headers_not_accessible_from_deps(self):
        """Headers only in sources (not public) are not accessible to dependents."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              deps = [":lib"]
            }

            source_set("lib") {
              sources = ["lib.cc", "internal.h"]
              public = ["lib.h"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "internal.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.write_file('internal.h', dedent('''
            #pragma once
            void internal_func();
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
            #include "internal.h"
            void lib_func() { internal_func(); }
            void internal_func() {}
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckFails("internal.h")


class GnCheckLabelFilterTest(GnTestCase):
    """Tests for checking specific labels with gn check."""

    def test_check_specific_label(self):
        """gn check with specific label only checks that target."""
        self.write_file('BUILD.gn', dedent('''
            source_set("good") {
              sources = ["good.cc"]
              deps = [":lib"]
            }

            source_set("bad") {
              sources = ["bad.cc"]
              # Missing deps = [":lib"]
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('good.cc', dedent('''
            #include "lib.h"
        '''))

        self.write_file('bad.cc', dedent('''
            #include "lib.h"
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        # Check only the good target - should pass
        self.assertGnCheckSucceeds(label="//:good")
        # Check only the bad target - should fail
        self.assertGnCheckFails(label="//:bad", error_substring="lib.h")

    def test_check_wildcard_label(self):
        """gn check with wildcard label checks matching targets."""
        self.write_file('BUILD.gn', dedent('''
            group("all") {
              deps = ["//good:target", "//bad:target"]
            }
        '''))

        self.write_file('lib/BUILD.gn', dedent('''
            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('lib/lib.h', dedent('''
            #pragma once
        '''))

        self.write_file('good/BUILD.gn', dedent('''
            source_set("target") {
              sources = ["main.cc"]
              deps = ["//lib"]
            }
        '''))

        self.write_file('good/main.cc', dedent('''
            #include "lib/lib.h"
        '''))

        self.write_file('bad/BUILD.gn', dedent('''
            source_set("target") {
              sources = ["main.cc"]
              # Missing deps
            }
        '''))

        self.write_file('bad/main.cc', dedent('''
            #include "lib/lib.h"
        '''))

        self.assertGnGenSucceeds()
        # Check only good/* targets - should pass
        self.assertGnCheckSucceeds(label="//good/*")


class GnCheckIncludeDirsTest(GnTestCase):
    """Tests for include_dirs and include path resolution."""

    def test_include_dirs_affects_path_resolution(self):
        """include_dirs allows includes relative to specified directories."""
        self.write_file('BUILD.gn', dedent('''
            source_set("main") {
              sources = ["main.cc"]
              include_dirs = ["include"]
              deps = [":lib"]
            }

            source_set("lib") {
              sources = ["include/lib.h", "lib.cc"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"  // Works because of include_dirs
            int main() { return 0; }
        '''))

        self.write_file('include/lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.write_file('lib.cc', dedent('''
            #include "include/lib.h"
            void lib_func() {}
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()


class GnCheckNoTargetsTest(GnTestCase):
    """Tests for edge cases with no sources or empty targets."""

    def test_group_with_deps_passes(self):
        """Group targets with deps pass check."""
        self.write_file('BUILD.gn', dedent('''
            group("all") {
              deps = [":lib"]
            }

            source_set("lib") {
              sources = ["lib.h", "lib.cc"]
            }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_empty_source_set_passes(self):
        """Source set with no sources passes check."""
        self.write_file('BUILD.gn', dedent('''
            source_set("empty") {
              sources = []
            }
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()


# =============================================================================
# Tests for custom latrodectus-gn functions with gn check
# =============================================================================


class GnCheckUpdateTargetTest(GnTestCase):
    """Tests for update_target interaction with gn check."""

    def test_update_target_adds_missing_dep(self):
        """update_target adding deps makes gn check pass."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            source_set("main") {
              sources = ["main.cc"]
              # Missing deps = [":lib"] - will be added by update_target
            }

            source_set("lib") {
              sources = ["lib.h", "lib.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:main") {
              deps = [":lib"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
            void lib_func() {}
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_update_target_appends_dep(self):
        """update_target appending to deps makes gn check pass."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            source_set("main") {
              sources = ["main.cc"]
              deps = [":lib1"]
              # Missing :lib2 - will be added by update_target
            }

            source_set("lib1") {
              sources = ["lib1.h"]
            }

            source_set("lib2") {
              sources = ["lib2.h"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:main") {
              deps += [":lib2"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib1.h"
            #include "lib2.h"
            int main() { return 0; }
        '''))

        self.write_file('lib1.h', dedent('''
            #pragma once
        '''))

        self.write_file('lib2.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_update_target_sets_check_includes_false(self):
        """update_target setting check_includes=false skips gn check."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            source_set("main") {
              sources = ["main.cc"]
              # No deps on :lib, but check_includes will be disabled
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:main") {
              check_includes = false
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_update_target_removes_dep_fails_check(self):
        """update_target removing a required dep makes gn check fail."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            source_set("main") {
              sources = ["main.cc"]
              deps = [":lib"]  # Has correct dep, but will be removed
            }

            source_set("lib") {
              sources = ["lib.h", "lib.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:main") {
              deps -= [":lib"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
            void lib_func();
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
            void lib_func() {}
        '''))

        self.assertGnGenSucceeds()
        # Dep was removed, so gn check should fail
        self.assertGnCheckFails("lib.h")

    def test_update_target_removes_transitive_dep_fails(self):
        """Removing a transitive dep breaks include chain, fails gn check."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            source_set("main") {
              sources = ["main.cc"]
              deps = [":middle"]
            }

            source_set("middle") {
              sources = ["middle.h"]
              deps = [":lib"]  # Will be removed by update_target
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_target("//:middle") {
              deps -= [":lib"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "middle.h"
            int main() { return 0; }
        '''))

        self.write_file('middle.h', dedent('''
            #pragma once
            #include "lib.h"  // Needs :lib dep
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckFails("lib.h")


class GnCheckDisableTargetTest(GnTestCase):
    """Tests for disable_target interaction with gn check."""

    def test_disable_target_removes_sources(self):
        """disable_target removes sources so no include checking needed."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            source_set("main") {
              sources = ["main.cc"]
              # No deps on :lib, would fail check if sources existed
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:main")
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        # With target disabled (sources cleared), gn check should pass
        self.assertGnCheckSucceeds()

    def test_disabling_dependency_target_fails_gen(self):
        """Disabling a target that has dependents fails gn gen."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            source_set("main") {
              sources = ["main.cc"]
              deps = [":lib"]
            }

            source_set("lib") {
              sources = ["lib.h", "lib.cc"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_target("//:lib")
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.write_file('lib.cc', dedent('''
            #include "lib.h"
        '''))

        # Disabling a target that has dependents causes gn gen to fail
        self.assertGnGenFails("Dependency on disabled target")


class GnCheckUpdateGniFileTest(GnTestCase):
    """Tests for update_gni_file interaction with gn check."""

    def test_update_gni_file_enables_dep_via_flag(self):
        """update_gni_file changing flag to enable dep makes gn check pass."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config.gni")

            source_set("main") {
              sources = ["main.cc"]
              if (enable_lib) {
                deps = [":lib"]
              }
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('config.gni', dedent('''
            enable_lib = false
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              enable_lib = true
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_update_gni_file_adds_to_deps_list(self):
        """update_gni_file appending to deps list makes gn check pass."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config.gni")

            source_set("main") {
              sources = ["main.cc"]
              deps = extra_deps
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('config.gni', dedent('''
            extra_deps = []
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              extra_deps = [":lib"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_update_gni_file_disables_dep_via_flag_fails(self):
        """update_gni_file changing flag to disable dep makes gn check fail."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config.gni")

            source_set("main") {
              sources = ["main.cc"]
              if (enable_lib) {
                deps = [":lib"]
              }
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('config.gni', dedent('''
            enable_lib = true  # Originally enabled
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              enable_lib = false  # Disable the dep
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"  // Still includes but dep is disabled
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckFails("lib.h")

    def test_update_gni_file_removes_from_deps_list_fails(self):
        """update_gni_file removing from deps list makes gn check fail."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config.gni")

            source_set("main") {
              sources = ["main.cc"]
              deps = extra_deps
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('config.gni', dedent('''
            extra_deps = [":lib"]  # Has dep
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              extra_deps = []  # Remove all deps
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckFails("lib.h")


class GnCheckDisableFileTest(GnTestCase):
    """Tests for disable_file interaction with gn check."""

    def test_disable_file_skips_targets_in_file(self):
        """disable_file prevents targets from being processed."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")

            group("all") {
              deps = []
              # Would depend on //subdir:target but it's disabled
            }
        '''))

        self.write_file('subdir/BUILD.gn', dedent('''
            source_set("target") {
              sources = ["main.cc"]
              # No deps on //lib:lib - would fail check
            }
        '''))

        self.write_file('lib/BUILD.gn', dedent('''
            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_file("//subdir/BUILD.gn")
        '''))

        self.write_file('subdir/main.cc', dedent('''
            #include "lib/lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib/lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        # subdir/BUILD.gn is disabled, so no targets to check there
        self.assertGnCheckSucceeds()


class GnCheckUpdateTemplateInstanceTest(GnTestCase):
    """Tests for update_template_instance interaction with gn check."""

    def test_update_template_instance_adds_dep(self):
        """update_template_instance adding deps makes gn check pass."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//my_template.gni")

            my_source_set("main") {
              sources = ["main.cc"]
              # Missing deps on :lib - will be added by update_template_instance
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('my_template.gni', dedent('''
            template("my_source_set") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:main") {
              deps = [":lib"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_disable_template_instance_removes_sources(self):
        """disable_template_instance clears sources so no checking needed."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//my_template.gni")

            my_source_set("main") {
              sources = ["main.cc"]
              # No deps on :lib, would fail check if not disabled
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('my_template.gni', dedent('''
            template("my_source_set") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }
        '''))

        self.write_file('updates.gni', dedent('''
            disable_template_instance("//:main")
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckSucceeds()

    def test_update_template_instance_removes_dep_fails(self):
        """update_template_instance removing required dep fails gn check."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//my_template.gni")

            my_source_set("main") {
              sources = ["main.cc"]
              deps = [":lib"]  # Has dep, will be removed
            }

            source_set("lib") {
              sources = ["lib.h"]
            }
        '''))

        self.write_file('my_template.gni', dedent('''
            template("my_source_set") {
              source_set(target_name) {
                forward_variables_from(invoker, "*")
              }
            }
        '''))

        self.write_file('updates.gni', dedent('''
            update_template_instance("//:main") {
              deps -= [":lib"]
            }
        '''))

        self.write_file('main.cc', dedent('''
            #include "lib.h"
            int main() { return 0; }
        '''))

        self.write_file('lib.h', dedent('''
            #pragma once
        '''))

        self.assertGnGenSucceeds()
        self.assertGnCheckFails("lib.h")
