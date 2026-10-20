import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from jsonschema import validate, ValidationError

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RECORDS_PATH = DATA_DIR / "records.json"
POLICY_PATH = DATA_DIR / "policy.json"
CHAT_SCRIPT_PATH = DATA_DIR / "chat_script.json"
SCHEMA_PATH = DATA_DIR / "memory_state.schema.json"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-5.6-luna"

records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

SYSTEM_PROMPT = (
    "You are an assistant for the grant office. "
    "Help applicants with their inquiries, track their documents and IDs, "
    "and adhere strictly to the policy database."
)

COMPRESS_SYSTEM_PROMPT = (
    "You are a state-compression engine. Summarize the conversation history into a JSON object "
    "that strictly follows the provided JSON schema. Do not include any extra text."
)

def count_tokens_rough(text: str) -> int:
    return max(1, len(text) // 4)

def estimate_messages_tokens(messages: list) -> int:
    return sum(count_tokens_rough(m.get("content", "")) for m in messages)

def compress_history(messages: list) -> tuple[dict | None, bool]:
    history_text = json.dumps(messages, ensure_ascii=False)
    user_msg = (
        f"Current conversation history:\n{history_text}\n\n"
        f"Extract the state into this JSON schema:\n{json.dumps(schema, indent=2)}"
    )
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": COMPRESS_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        state_obj = json.loads(content)
        validate(instance=state_obj, schema=schema)
        return state_obj, True
    except (Exception, ValidationError) as e:
        print(f"[Warning] Compression failed or schema validation error: {e}")
        return None, False

def run_scripted_mode():
    script_content = CHAT_SCRIPT_PATH.read_text(encoding="utf-8")
    script_data = json.loads(script_content)
    
    # Исправлено: используем правильный ключ 'conversation' из чат-скрипта
    turns = script_data.get("conversation", []) or script_data.get("turns", [])
    probes = script_data.get("probes", [])

    print(f"[Debug] Loaded {len(turns)} turns and {len(probes)} probes from chat_script.json")

    print("=== Running Scripted Mode: UNCOMPRESSED ===")
    unc_tokens_per_call = []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    for idx, turn in enumerate(turns):
        if isinstance(turn, dict):
            user_input = turn.get("user") or turn.get("message") or turn.get("content") or turn.get("text") or ""
            turn_id = turn.get("id", idx + 1)
        else:
            user_input = str(turn)
            turn_id = idx + 1

        messages.append({"role": "user", "content": user_input})
        
        input_tokens = estimate_messages_tokens(messages)
        response = client.chat.completions.create(model=MODEL, messages=messages)
        assistant_reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_reply})
        
        out_tokens = count_tokens_rough(assistant_reply)
        unc_tokens_per_call.append({"turn": turn_id, "input": input_tokens, "output": out_tokens})

    # Проверки пробами для uncompressed
    unc_probe_results = []
    for probe in probes:
        query = probe.get("query") or probe.get("question") or probe.get("prompt") or str(probe)
        expected_fact = probe.get("expected") or probe.get("answer") or ""
        
        test_messages = messages + [{"role": "user", "content": f"Answer concisely based on history: {query}"}]
        res = client.chat.completions.create(model=MODEL, messages=test_messages)
        ans = res.choices[0].message.content or ""
        
        success = str(expected_fact).lower() in ans.lower() if expected_fact else True
        unc_probe_results.append({"probe": probe.get("id", "unknown"), "passed": success, "answer": ans})

    print("=== Running Scripted Mode: COMPRESSED ===")
    comp_tokens_per_call = []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    compressed_state = None
    
    for idx, turn in enumerate(turns):
        if isinstance(turn, dict):
            user_input = turn.get("user") or turn.get("message") or turn.get("content") or turn.get("text") or ""
            turn_id = turn.get("id", idx + 1)
        else:
            user_input = str(turn)
            turn_id = idx + 1
        
        if user_input.strip().lower() == "compress":
            state, success = compress_history(messages)
            if success:
                compressed_state = state
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "system", "content": f"Previous conversation state summary:\n{json.dumps(compressed_state, ensure_ascii=False)}"}
                ]
                print(f"[Info] Context successfully compressed at turn {turn_id}")
            else:
                print(f"[Info] Compression rejected, keeping history at turn {turn_id}")
            user_input = "Could you summarize our status?"

        messages.append({"role": "user", "content": user_input})
        input_tokens = estimate_messages_tokens(messages)
        
        response = client.chat.completions.create(model=MODEL, messages=messages)
        assistant_reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_reply})
        
        out_tokens = count_tokens_rough(assistant_reply)
        comp_tokens_per_call.append({"turn": turn_id, "input": input_tokens, "output": out_tokens})

    # Проверки пробами для compressed
    comp_probe_results = []
    for probe in probes:
        query = probe.get("query") or probe.get("question") or probe.get("prompt") or str(probe)
        expected_fact = probe.get("expected") or probe.get("answer") or ""
        
        test_messages = messages + [{"role": "user", "content": f"Answer concisely based on history: {query}"}]
        res = client.chat.completions.create(model=MODEL, messages=test_messages)
        ans = res.choices[0].message.content or ""
        
        success = str(expected_fact).lower() in ans.lower() if expected_fact else True
        comp_probe_results.append({"probe": probe.get("id", "unknown"), "passed": success, "answer": ans})

    print("\n--- SCRIPTED RUN SUMMARY ---")
    print("Uncompressed peak tokens:", max((t["input"] + t["output"] for t in unc_tokens_per_call), default=0))
    print("Compressed peak tokens:", max((t["input"] + t["output"] for t in comp_tokens_per_call), default=0))
    print("Uncompressed Probes:", unc_probe_results)
    print("Compressed Probes:", comp_probe_results)
    if compressed_state:
        print("\nFinal Compressed State Object:\n", json.dumps(compressed_state, indent=2, ensure_ascii=False))

def run_interactive_mode():
    print("=== Interactive Chat Mode (Type 'compress' to compress history, 'exit' to quit) ===")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    while True:
        user_input = input("\nApplicant: ")
        if user_input.strip().lower() == "exit":
            break
            
        if user_input.strip().lower() == "compress":
            state, success = compress_history(messages)
            if success:
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "system", "content": f"Previous conversation state summary:\n{json.dumps(state, ensure_ascii=False)}"}
                ]
                print(">>> CONTEXT COMPRESSED SUCCESSFULLY <<<")
                print(json.dumps(state, indent=2, ensure_ascii=False))
            else:
                print(">>> COMPRESSION FAILED, KEEPING HISTORY <<<")
            continue

        messages.append({"role": "user", "content": user_input})
        input_tokens = estimate_messages_tokens(messages)
        
        response = client.chat.completions.create(model=MODEL, messages=messages)
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        
        out_tokens = count_tokens_rough(reply)
        print(f"\nAssistant: {reply}")
        print(f"[Tokens cost last call — Input: {input_tokens}, Output: {out_tokens}, Total: {input_tokens + out_tokens}]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true", help="Run interactive chat mode")
    args = parser.parse_args()

    if args.interactive:
        run_interactive_mode()
    else:
        run_scripted_mode()