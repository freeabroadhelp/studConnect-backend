from typing import Dict, Any, List
import json
from .safety_rules import SAFETY_RULES, SYSTEM_ROLE_DEFINITION, JSON_OUTPUT_FORMAT_INSTRUCTION

def build_system_prompt() -> str:
    """Constructs the static system prompt."""
    rules_str = "\n".join([f"- {rule}" for rule in SAFETY_RULES])
    
    return f"""{SYSTEM_ROLE_DEFINITION}

SAFETY RULES (NON-NEGOTIABLE):
{rules_str}

OUTPUT FORMAT:
{JSON_OUTPUT_FORMAT_INSTRUCTION}
"""

def build_user_prompt(student_profile: Dict[str, Any], engine_output: Dict[str, Any], limit: int = 5) -> str:
    """
    Constructs the user prompt from profile and engine results.
    Truncates recommendations to save tokens.
    """
    
    # 1. Sanitize and Format Profile
    profile_summary = {
        "degree_level": student_profile.get("target_degree_level"),
        "countries": student_profile.get("preferred_countries"),
        "academic_score": student_profile.get("academic_score_band"),
        "english_score": student_profile.get("language_score_band"),
        "intake_year": student_profile.get("target_intake_year"),
        "budget": student_profile.get("tuition_preference_band"),
        "work_exp": student_profile.get("work_experience_years"),
        "gap_years": student_profile.get("gap_years"),
        "field": student_profile.get("background_field")
    }
    
    # 2. Extract Top Recommendations
    # We only want to send the top N programs overall to save context
    recommendations = engine_output.get("recommendations", [])[:limit]
    
    minimized_recs = _minimize_program_data(recommendations)
    
    warnings = engine_output.get("warnings", [])
    
    user_content = f"""
STUDENT PROFILE:
{json.dumps(profile_summary, indent=2)}

ENGINE OUTPUT SUMMARY:
- Total Evaluated: {engine_output.get("summary", {}).get("total_evaluated")}
- Total Eligible: {engine_output.get("summary", {}).get("total_eligible")}
- Engine Warnings: {json.dumps(warnings)}

TOP RECOMMENDATIONS (Ranked):
{json.dumps(minimized_recs, indent=2)}

TASK:
Explain these recommendations to the student. Adhere strictly to the safety rules.
"""
    return user_content

def _minimize_program_data(programs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Helper to reduce program dict size for prompt."""
    minimized = []
    for p in programs:
        minimized.append({
            "id": p.get("program_id"),
            "university": p.get("university_name"),
            "program": p.get("program_name"),
            "country": p.get("country"),
            "score": p.get("total_score"),
            "classification": p.get("classification"),
            "tuition": p.get("tuition_fee_band")
        })
    return minimized
