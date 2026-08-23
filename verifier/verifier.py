import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ============================================================
# CONFIGURATION & MULTI-KEY FAILOVER
# ============================================================

load_dotenv()

def get_gemini_api_keys() -> list[str]:
    """Collect all configured Gemini API keys (supports 1 to 5+ keys for failover)."""
    keys: list[str] = []
    keys_env = os.getenv("GEMINI_API_KEYS", "")
    if keys_env:
        keys.extend([k.strip() for k in keys_env.split(",") if k.strip()])

    for var in ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"]:
        val = os.getenv(var)
        if val and val.strip() and val.strip() not in keys:
            keys.append(val.strip())

    return keys


api_keys = get_gemini_api_keys()

if not api_keys:
    print("[ERROR] No Gemini API keys found in .env (GEMINI_API_KEY or GEMINI_API_KEY_1..5)")
    print("Please configure at least one valid Gemini API key.")
    sys.exit(1)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
BASE_DIR = Path(__file__).parent


# ============================================================
# INPUT
# ============================================================

requirement = """
Users can only access their own profile.
"""

profile_path = BASE_DIR / "app" / "profile.py"
if not profile_path.exists():
    print(f"[ERROR] Profile file not found at {profile_path}")
    sys.exit(1)

code = profile_path.read_text(encoding="utf-8")


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
# CALL GEMINI WITH MULTI-KEY FAILOVER
# ============================================================

print(f"[KEY POOL] Loaded {len(api_keys)} Gemini API key(s) into failover pool.")

response = None
last_error = None

for idx, key in enumerate(api_keys):
    masked_key = f"...{key[-6:]}" if len(key) >= 6 else "***"
    print(f"[ATTEMPT] Attempting verification with Gemini API Key #{idx + 1} ({masked_key})...")
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )
        print(f"[SUCCESS] Successful response received using Key #{idx + 1}")
        break
    except Exception as e:
        print(f"[FAILOVER] Key #{idx + 1} failed: {e}")
        last_error = e

if response is None:
    print("\n[FAILED] VERIFICATION FAILED ACROSS ALL API KEYS:")
    print("Unable to verify: AI verification service is temporarily unavailable. Please try again later.")
    print(f"Last Error: {last_error}")
    sys.exit(1)


# ============================================================
# PARSE GEMINI RESPONSE
# ============================================================

try:
    result = json.loads(response.text)
except json.JSONDecodeError:
    print("[ERROR] Gemini returned invalid JSON:")
    print(response.text)
    sys.exit(1)


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

print(f"[SAVED] Saved verification result to: {spec_file}")