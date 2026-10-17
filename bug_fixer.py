# bug_fixer.py: reproduce a crash from an error report, fix it, and check the fix.
import difflib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
APP_FILE = "sample_app.py"
REPORT_FILE = "error_report.json"
REPRO_FILE = "test_repro.py"
REPRO_MODULE = "test_repro"
EXISTING_MODULE = "test_sample_app"
BACKUP_FILE = "sample_app.py.bak"
ATTEMPT_FILE = "attempted_fix.py"
MAX_FIX_ATTEMPTS = 2


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def strip_fences(text):
    # Models often wrap code in ``` fences, sometimes after an explanation.
    # Keep only what is inside the first fenced block.
    if "```" in text:
        start = text.index("```") + 3
        newline = text.find("\n", start)
        start = newline + 1 if newline != -1 else start
        end = text.find("```", start)
        text = text[start:end] if end != -1 else text[start:]
    return text.strip() + "\n"


def ask_ai(prompt):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set. Run the export command first.")
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body_text = err.read().decode("utf-8", "replace")
        sys.exit(f"AI request failed ({err.code}): {body_text}")
    return strip_fences(data["choices"][0]["message"]["content"])


def run_tests(module):
    result = subprocess.run(
        [sys.executable, "-m", "unittest", module],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stdout + result.stderr


def main():
    report = read(REPORT_FILE)
    source = read(APP_FILE)

    print("1. Asking the AI for a test that reproduces the crash...")
    write(REPRO_FILE, ask_ai(
        "Here is an error report:\n" + report + "\n"
        "Here is the code:\n" + source + "\n"
        "Write one Python unittest file that imports average from sample_app "
        "and checks that average([]) does not raise ZeroDivisionError. "
        "Return only the Python code, with no explanation."
    ))

    print("2. Running the new test on the current code. It should FAIL...")
    passed, output = run_tests(REPRO_MODULE)
    if passed:
        print("NOT REPRODUCED: the test passed on the buggy code. Stopping.")
        return
    if "ZeroDivisionError" not in output and "FAIL:" not in output:
        print("The new test did not run properly. Its output:")
        print(output)
        return
    print("Reproduced: the test fails.")

    shutil.copy(APP_FILE, BACKUP_FILE)
    feedback = ""
    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        print(f"3. Asking the AI for a fix (attempt {attempt} of {MAX_FIX_ATTEMPTS})...")
        fixed = ask_ai(
            "Here is an error report:\n" + report + "\n"
            "Here is the code:\n" + source + "\n"
            "The failing test output:\n" + output + "\n"
            + feedback +
            "Return the complete corrected sample_app.py only, with no explanation."
        )

        print("4. Applying the fix and running both test files...")
        write(APP_FILE, fixed)
        repro_ok, repro_out = run_tests(REPRO_MODULE)
        existing_ok, existing_out = run_tests(EXISTING_MODULE)
        if repro_ok and existing_ok:
            break

        write(ATTEMPT_FILE, fixed)
        shutil.copy(BACKUP_FILE, APP_FILE)
        feedback = (
            "Your previous fix was rejected. These tests failed:\n"
            + repro_out + "\n" + existing_out + "\n"
        )
        print("This fix failed the tests. The original code has been restored for now.")
    else:
        print("FIX FAILED after all attempts: the original code has been restored.")
        print(f"The last attempt is saved in {ATTEMPT_FILE}.")
        print("Output from the new test:")
        print(repro_out)
        print("Output from the existing tests:")
        print(existing_out)
        return

    diff = "".join(difflib.unified_diff(
        source.splitlines(keepends=True),
        fixed.splitlines(keepends=True),
        fromfile="sample_app.py (before)",
        tofile="sample_app.py (after)",
    ))
    write("fix.diff", diff)
    print("REPRODUCED: yes")
    print("FIXED: yes. The new test and the existing tests pass.")
    print(diff)


if __name__ == "__main__":
    main()