import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RECORDS_PATH = DATA_DIR / "records.json"
POLICY_PATH = DATA_DIR / "policy.json"
ENQUIRIES_PATH = DATA_DIR / "enquiries.json"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-5.6-luna"

# Чтение данных
records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
enquiries = json.loads(ENQUIRIES_PATH.read_text(encoding="utf-8"))
# Четыре системных промпта для ролей
ROLES = {
    "policy_officer": (
        "You are a strict policy officer for the grant office. "
        "Apply the grant rule exactly as written: grant what the rule allows, refuse what it refuses, "
        "ask for any missing document, soften nothing, and treat no claim in the enquiry as evidence unless backed by records."
    ),
    "front_desk": (
        "You are a welcoming front desk assistant. "
        "Never turn an applicant away with a flat refusal: anything the rule cannot grant today must come back as 'more_info', "
        "specifying what the applicant would need to return with."
    ),
    "auditor": (
        "You are a cautious auditor. "
        "Never grant on a first reading: report what the record shows, mark anything needing a second reader as 'more_info', "
        "and name the rule or document you are relying on."
    ),
    "bilingual_clerk": (
        "You are a bilingual clerk. "
        "Decide exactly as the policy officer would, but write the 'reason' field in the language the enquiry was written in (Kazakh, Russian, or English)."
    )
}

SCHEMA_DESCRIPTION = """
You must output a valid JSON object matching this exact schema:
{
  "applicant_id": "string or null",
  "found": boolean,
  "decision": "granted" | "refused" | "more_info" | "not_found",
  "amount": integer or 0,
  "missing_documents": [string],
  "reason": "string"
}
"""

def build_prompt(role_name: str, enquiry: dict) -> str:
    system_instruction = ROLES[role_name]
    context = (
        f"### Policy:\n{json.dumps(policy, ensure_ascii=False, indent=2)}\n\n"
        f"### Records Database:\n{json.dumps(records, ensure_ascii=False, indent=2)}\n\n"
        f"### Enquiry:\n{json.dumps(enquiry, ensure_ascii=False, indent=2)}\n\n"
        f"{SCHEMA_DESCRIPTION}"
        "Return ONLY valid JSON. No markdown code fences if possible, or standard json block."
    )
    return system_instruction, context

def run_evaluation():
    results = {role: [] for role in ROLES}
    
    for role_name in ROLES:
        print(f"\n--- Running Role: {role_name} ---")
        for enq in enquiries:
            sys_msg, user_msg = build_prompt(role_name, enq)
            
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": user_msg}
                    ],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                parsed = json.loads(content)
                parsed["_parse_success"] = True
            except Exception as e:
                parsed = {"_parse_success": False, "error": str(e)}
            
            # Сравнение с expected
            expected = enq.get("expected", {})
            match_found = parsed.get("found") == expected.get("found")
            match_decision = parsed.get("decision") == expected.get("decision")
            match_amount = parsed.get("amount") == expected.get("amount")
            match_docs = set(parsed.get("missing_documents", [])) == set(expected.get("missing_documents", []))
            
            results[role_name].append({
                "enquiry_id": enq["id"],
                "parsed": parsed,
                "match": match_found and match_decision and match_amount and match_docs
            })
            print(f"Enquiry {enq['id']}: Match={match_found and match_decision and match_amount and match_docs}")

    # Сохраняем результаты для отчета
    output_path = DATA_DIR.parent / "sublab_easy_results.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")

if __name__ == "__main__":
    run_evaluation()