import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from jsonschema import validate, ValidationError

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CANDIDATES_DIR = DATA_DIR / "candidates"
RUBRIC_PATH = DATA_DIR / "candidate_rubric.json"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-5.6-luna"

rubric = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))

EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert academic data extractor. Read the candidate story carefully and extract a structured CV record. "
    "Follow these strict rules:\n"
    "1. If a fact is not stated, return null (never estimate or guess).\n"
    "2. Convert GPAs to a 4.0 scale and record the original scale beside it.\n"
    "3. A paper is published ONLY if explicitly stated as published or accepted. Submitted, under review, in preparation, or in press are NOT published (record them separately, do not count them).\n"
    "4. If there are contradictions, set the field to null and note the contradiction."
)

SCORING_SYSTEM_PROMPT = (
    "You are an objective scholarship evaluator. Based on the candidate's extracted profile and story, "
    "evaluate the candidate against the provided rubric. Output ONLY a JSON object with scores from 0 to 5 for each criterion."
)

def extract_cv(story_text: str) -> dict:
    prompt = f"Candidate Story:\n{story_text}\n\nExtract the structured CV as a JSON object."
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

def score_candidate(profile: dict) -> dict:
    prompt = (
        f"Rubric:\n{json.dumps(rubric, indent=2)}\n\n"
        f"Candidate Profile:\n{json.dumps(profile, indent=2)}\n\n"
        "Provide integer scores from 0 to 5 for each criterion defined in the rubric as a JSON object."
    )
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {}

def run_hard_sublab():
    print("=== Sublab Hard: CV Extraction & Ranking ===")
    story_files = sorted(CANDIDATES_DIR.glob("story-*.md"))
    
    candidates_data = []
    
    for path in story_files:
        story_text = path.read_text(encoding="utf-8")
        print(f"\nProcessing {path.name}...")
        
        # Часть 1: Извлечение CV
        cv_record = extract_cv(story_text)
        
        # Часть 2: Оценка по рубрике
        scores = score_candidate(cv_record)
        
        candidates_data.append({
            "filename": path.name,
            "cv": cv_record,
            "scores": scores
        })

    # Расчет победителя в коде на основе весов из рубрики
    print("\n=== COMPUTED RANKINGS ===")
    weights = rubric.get("weights", {"criteria_1": 0.4, "criteria_2": 0.3, "criteria_3": 0.3}) # пример весов, если они заданы в рубрике
    
    scored_results = []
    for cand in candidates_data:
        scores = cand["scores"]
        # Используем веса из rubric.json: academic (0.5), research (0.3), experience (0.2)
        academic_score = float(scores.get("academic", 0))
        research_score = float(scores.get("research", 0))
        experience_score = float(scores.get("experience", 0))
        
        total_score = round(0.5 * academic_score + 0.3 * research_score + 0.2 * experience_score, 2)
        
        scored_results.append({
            "candidate": cand["filename"],
            "cv": cand["cv"],
            "scores": scores,
            "total_weighted_score": total_score
        })

    # Сортировка по убыванию баллов
    scored_results.sort(key=lambda x: x["total_weighted_score"], reverse=True)

    for rank, res in enumerate(scored_results, 1):
        print(f"{rank}. {res['candidate']} — Score: {res['total_weighted_score']:.2f} (Scores: {res['scores']})")

    # Часть 2 (продолжение): Запрос модели на текстовое мнение (prose ranking)
    prose_prompt = (
        f"Here are the summarized profiles and scores of all candidates:\n{json.dumps(scored_results, indent=2)}\n\n"
        "In prose, explain who should win the scholarship and why."
    )
    prose_res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prose_prompt}]
    )
    print("\n=== MODEL PROSE RANKING ===")
    print(prose_res.choices[0].message.content)

if __name__ == "__main__":
    run_hard_sublab()