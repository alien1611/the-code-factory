import json
from pathlib import Path
from code_parser import parse_profile


BASE_DIR = Path(__file__).parent
SPEC_FILE = BASE_DIR / "test_spec.json"
OUTPUT_DIR = BASE_DIR / "tests" / "generated"


def load_profile_info():
    profile_file = BASE_DIR / "app" / "profile.py"

    if not profile_file.exists():
        raise FileNotFoundError(
            "app/profile.py was not found."
        )

    return parse_profile(profile_file)


def validate_test_inputs(test_spec, valid_user_ids):
    """
    Make sure Gemini did not invent user IDs.
    """

    inputs = test_spec.get("inputs", {})

    requesting_user_id = inputs.get("requesting_user_id")
    requested_user_id = inputs.get("requested_user_id")

    if requesting_user_id not in valid_user_ids:
        raise ValueError(
            f"Invalid requesting_user_id: {requesting_user_id}. "
            f"Valid IDs: {sorted(valid_user_ids)}"
        )

    if requested_user_id not in valid_user_ids:
        raise ValueError(
            f"Invalid requested_user_id: {requested_user_id}. "
            f"Valid IDs: {sorted(valid_user_ids)}"
        )


def generate_test(test_spec, valid_user_ids,valid_functions):

    validate_test_inputs(
        test_spec,
        valid_user_ids
    )

    name = test_spec["name"]

    # Pytest requires test functions to start with test_
    if not name.startswith("test_"):
        name = f"test_{name}"

    description = test_spec["description"]
    target = test_spec["target"]
    inputs = test_spec["inputs"]
    expected = test_spec["expected"]

    if target not in valid_functions:
        raise ValueError(f"Unsupported target function: {target}")

    if expected not in ["ALLOW", "DENY"]:
        raise ValueError(
            f"Invalid expected value: {expected}"
        )

    requesting_user_id = inputs["requesting_user_id"]
    requested_user_id = inputs["requested_user_id"]

    # ============================================================
    # DENY TEST
    # ============================================================

    if expected == "DENY":

        test_code = f'''from app.profile import get_profile


def {name}():
    """
    {description}
    """

    try:
        get_profile(
            {requesting_user_id},
            {requested_user_id}
        )

    except PermissionError:
        return

    raise AssertionError(
        "Expected unauthorized access to be rejected, "
        "but the profile was returned."
    )
'''

    # ============================================================
    # ALLOW TEST
    # ============================================================

    else:

        test_code = f'''from app.profile import get_profile


def {name}():
    """
    {description}
    """

    profile = get_profile(
        {requesting_user_id},
        {requested_user_id}
    )

    assert profile is not None
'''

    # ============================================================
    # WRITE TEST FILE
    # ============================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = OUTPUT_DIR / f"{name}.py"

    output_file.write_text(
        test_code,
        encoding="utf-8"
    )

    print(f"Generated: {output_file}")


def main():

    if not SPEC_FILE.exists():
        raise FileNotFoundError(
            "test_spec.json not found. Run verifier.py first."
        )

    # ============================================================
    # CLEAN UP OLD GENERATED TESTS
    # ============================================================
    # This ensures tests/generated/ always reflects only the
    # current test_spec.json, with no stale files from earlier runs.

    if OUTPUT_DIR.exists():
        for old_file in OUTPUT_DIR.glob("*.py"):
            old_file.unlink()

    profile_info = load_profile_info()
    valid_user_ids = profile_info["user_ids"]
    valid_functions = profile_info["functions"]

    data = json.loads(
        SPEC_FILE.read_text(
            encoding="utf-8"
        )
    )

    tests = data.get("tests", [])

    if not tests:
        raise ValueError(
            "Gemini returned no tests."
        )

    for test in tests:

        try:
            generate_test(
                test,
                valid_user_ids,
                valid_functions
            )

        except ValueError as error:

            print(
                f"Skipped invalid test "
                f"'{test.get('name', 'unknown')}': {error}"
            )


if __name__ == "__main__":
    main()