import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

client = genai.Client(api_key=api_key)

MODEL = "gemini-3.6-flash"

BASE_DIR = Path(__file__).parent


# ============================================================
# INPUT
# ============================================================

requirement = """
Users can only access their own profile.
"""

code = (BASE_DIR / "app" / "profile.py").read_text(encoding="utf-8")


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
    model=MODEL,
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


# ============================================================
# DISPLAY RESULT
# ============================================================

print("\n========== AI VERIFICATION ==========\n")

print(json.dumps(result, indent=2))

print("\n=====================================\n")


# ============================================================
# SAVE RESULT FOR TEST GENERATOR
# ============================================================

spec_file = BASE_DIR / "test_spec.json"

spec_file.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8"
)

print(f"Saved verification result to: {spec_file}")