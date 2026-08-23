import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).parent
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def generate_verification_spec(
    requirement: str,
    code: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    spec_output_file: Optional[Path] = None,
) -> dict:
    """
    Analyzes software requirements against code using Gemini LLM reasoning
    to produce structured test specifications for downstream pytest generation.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY was not found in environment or .env file.")

    client = genai.Client(api_key=key)
    target_model = model or DEFAULT_MODEL

    # ============================================================
    # VERIFICATION PROMPT
    # ============================================================
    prompt = f"""
You are a software verification assistant.

Your job is to analyze whether an implementation actually
satisfies a given software requirement.

Do NOT assume the implementation is correct.

REQUIREMENT:
{requirement}

CODE:
{code}

Analyze the implementation and determine:

1. What the requirement means.
2. What conditions must be satisfied.
3. What violations exist.
4. What tests could prove or disprove the requirement.
5. Give a final PASS or FAIL verdict.

{{
    "verdict": "PASS or FAIL",
    "requirements": [],
    "conditions": [],
    "violations": [],
    "tests": [
        {{
            "name": "short_test_name",
            "type": "authorization",
            "target": "function_name",
            "inputs": {{}},
            "expected": "ALLOW or DENY",
            "description": "What the test should verify"
        }}
    ]
}}

For an authorization test:
- requesting_user_id must be 101
- requested_user_id must be 102

Do NOT invent IDs that are not present in the code.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "verdict": "PASS or FAIL",
    "requirements": [],
    "conditions": [],
    "violations": [],
    "tests": [
        {{
            "name": "short_test_name",
            "type": "authorization",
            "target": "function_name",
            "inputs": {{}},
            "expected": "expected_behavior",
            "description": "What the test should verify"
        }}
    ]
}}
"""


    # ============================================================
    # CALL GEMINI
    # ============================================================
    response = client.models.generate_content(
        model=target_model,
        contents=prompt,
        config={
            "response_mime_type": "application/json"
        }
    )

    # ============================================================
    # PARSE GEMINI RESPONSE
    # ============================================================
    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        print("Gemini returned invalid JSON:")
        print(response.text)
        raise

    out_file = spec_output_file or (BASE_DIR / "test_spec.json")
    out_file.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8"
    )

    return result


if __name__ == "__main__":
    requirement = "Users can only access their own profile."
    code_path = BASE_DIR / "app" / "profile.py"
    if not code_path.exists():
        raise FileNotFoundError(f"Code file not found: {code_path}")
    code = code_path.read_text(encoding="utf-8")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[!] GEMINI_API_KEY not set in .env. Checking existing test_spec.json...")
        spec_path = BASE_DIR / "test_spec.json"
        if spec_path.exists():
            print(f"[+] Found existing test_spec.json at {spec_path}")
            print(spec_path.read_text(encoding="utf-8"))
        else:
            print("[!] No existing test_spec.json found. Please set GEMINI_API_KEY in .env.")
    else:
        print(f"[+] Calling Gemini ({DEFAULT_MODEL}) to synthesize test spec...")
        result = generate_verification_spec(requirement=requirement, code=code)
        print("\n========== AI VERIFICATION SPEC ==========\n")
        print(json.dumps(result, indent=2))
        print("\n==========================================\n")