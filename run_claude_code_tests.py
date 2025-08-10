#!/usr/bin/env python3
"""
Script to run Claude Code integration tests.
This is a convenience script to run the claude-code integration tests easily.
"""

import subprocess
import sys
import argparse

def run_tests(test_filter=None, verbose=False):
    """Run Claude Code integration tests."""
    cmd = ['python', '-m', 'pytest', 'tests/integration/claude-code/']
    
    if test_filter:
        cmd.append(f'-k {test_filter}')
    
    if verbose:
        cmd.extend(['-v', '--tb=short'])
    else:
        cmd.append('-v')
    
    # Note: timeout plugin would be added here if available
    # cmd.extend(['--timeout=300'])  # 5 minutes max per test
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run Claude Code integration tests')
    parser.add_argument(
        '-k', '--filter',
        help='Run only tests matching this pattern (e.g., "test_basic" or "auth")'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available tests without running them'
    )
    
    args = parser.parse_args()
    
    if args.list:
        # List available tests
        cmd = ['python', '-m', 'pytest', 'tests/integration/claude-code/', '--collect-only', '-q']
        subprocess.run(cmd)
        return
    
    success = run_tests(args.filter, args.verbose)
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)

if __name__ == '__main__':
    main()