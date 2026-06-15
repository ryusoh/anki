import os
import sys

sys.path.append(os.path.join(os.getcwd(), 'enhance_main_window'))
import debug

debug.startDebug()


def test_vulnerability_and_features():

    print("Testing security (no eval):")
    # This should now just print the string literal because eval is gone.
    debug.debug("User sent: {user_input}")

    print("\nTesting file parameter (sys.stderr):")
    # This should print to stderr
    debug.debug("This should go to stderr", file=sys.stderr)

    print("\nTesting legacy level parameter (should not crash):")
    # This should ignore the level parameter and not crash
    debug.debug("This has a level parameter", level=2)


if __name__ == "__main__":
    test_vulnerability_and_features()
