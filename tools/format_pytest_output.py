import os
import re
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: format_pytest_output.py <cov_dir> <suites_list>")
        sys.exit(1)

    cov_dir = sys.argv[1]
    suites = sys.argv[2].split()

    failed = False
    max_len = max(len(s) for s in suites) if suites else 40
    # Add a bit of padding
    col_width = max(max_len + 2, 45)

    print("")  # Blank line before test list

    for suite in suites:
        tag = suite.replace("/", "_")
        log_path = os.path.join(cov_dir, f"log.{tag}")
        rc_path = os.path.join(cov_dir, f"rc.{tag}")

        rc = 1
        if os.path.exists(rc_path):
            try:
                with open(rc_path, "r") as f:
                    rc = int(f.read().strip())
            except ValueError:
                pass

        if rc == 0:
            # Success: extract summary and print a clean line
            summary = ""
            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    lines = f.readlines()
                # Search from bottom for pytest summary line
                for line in reversed(lines):
                    line_str = line.strip()
                    if "passed" in line_str and "in" in line_str:
                        # Reformat "X passed in Ys" -> "X passed (Ys)"
                        match = re.match(r"(.+?)\s+in\s+(.+)", line_str)
                        if match:
                            summary = f"{match.group(1)} ({match.group(2)})"
                        else:
                            summary = line_str
                        break
            if not summary:
                summary = "passed"

            # Print aligned success line
            # Green checkmark, bold white suite name, dim summary
            sys.stdout.write(
                f"  \033[32m✓\033[0m \033[1m{suite:<{col_width}}\033[0m \033[2m{summary}\033[0m\n"
            )
        else:
            failed = True
            # Failure: print failure line and full log output
            sys.stdout.write(
                f"  \033[31m✗\033[0m \033[1;31m{suite:<{col_width}}\033[0m \033[31mfailed\033[0m\n"
            )
            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    log_content = f.read()
                print("\n\033[31m" + "=" * 80)
                print(f"Failure Output for {suite}:")
                print("=" * 80 + "\033[0m")
                print(log_content)
                print("\033[31m" + "=" * 80 + "\033[0m\n")

    if failed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
