#!/usr/bin/env python3
"""Run GN integration tests."""

import argparse
import os
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description='Run GN integration tests')
    parser.add_argument('--gn', help='Path to gn binary (default: auto-detect from ../out/gn)')
    parser.add_argument('--pattern', default='test_*.py', help='Test file pattern')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--show-ninja', action='store_true', help='Show ninja file contents after each test')
    parser.add_argument('tests', nargs='*', help='Specific tests to run')
    args = parser.parse_args()

    # Find GN binary
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    if args.gn:
        gn_binary = args.gn
    else:
        # Auto-detect from out/gn
        gn_binary = os.path.join(project_root, 'out', 'gn')

    if not os.path.exists(gn_binary):
        print(f"Error: GN binary not found at {gn_binary}")
        print("Build it first with: ninja -C out")
        return 1

    # Set GN binary path and options for all test classes
    import gn_test_base
    gn_test_base.GnTestCase.GN_BINARY = os.path.abspath(gn_binary)
    gn_test_base.GnTestCase.SHOW_NINJA = args.show_ninja

    print(f"Using GN binary: {gn_test_base.GnTestCase.GN_BINARY}")
    print()

    # Discover and run tests
    loader = unittest.TestLoader()

    if args.tests:
        # Run specific tests
        suite = unittest.TestSuite()
        for test_name in args.tests:
            suite.addTests(loader.loadTestsFromName(test_name))
    else:
        # Discover all tests
        suite = loader.discover(script_dir, pattern=args.pattern)

    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
