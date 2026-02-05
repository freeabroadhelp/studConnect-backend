"""
Data Adapter for Recommendation Engine

Reads from existing production tables (programs, universities) and transforms
JSON-based attributes into a normalized format for the recommendation engine.

This is a pure READ + TRANSFORM layer:
- NO scoring logic
- NO ranking/classification
- NO DB writes
- NO AI/LLM usage
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String

from models.models import Program, UniversityModel


# Country code to name mapping
COUNTRY_CODE_MAP = {
    "AU": "Australia",
    "CA": "Canada", 
    "DE": "Germany",
    "GB": "United Kingdom",
    "UK": "United Kingdom",
    "IE": "Ireland",
    "US": "United States",
    "USA": "United States",
    "NZ": "New Zealand",
    "SG": "Singapore",
    "NL": "Netherlands",
    "FR": "France",
}

# Reverse mapping: Full name to codes (for SQL filtering)
COUNTRY_NAME_TO_CODES = {
    "australia": ["AU", "au", "Australia"],
    "canada": ["CA", "ca", "Canada"],
    "germany": ["DE", "de", "Germany"],
    "united kingdom": ["GB", "UK", "gb", "uk", "United Kingdom"],
    "ireland": ["IE", "ie", "Ireland"],
    "united states": ["US", "USA", "us", "usa", "United States"],
    "new zealand": ["NZ", "nz", "New Zealand"],
    "singapore": ["SG", "sg", "Singapore"],
    "netherlands": ["NL", "nl", "Netherlands"],
    "france": ["FR", "fr", "France"],
}


def normalize_degree_level(raw_degree_text: Optional[str]) -> str:
    """
    Normalize inconsistent degree labels to standard categories.
    
    Returns one of: 'bachelors', 'masters', 'diploma', 'phd', 'unknown'
    
    Args:
        raw_degree_text: Raw degree level string from database
        
    Returns:
        Normalized degree level
    """
    if not raw_degree_text:
        return "unknown"
    
    # Convert to lowercase for case-insensitive matching
    text = raw_degree_text.lower().strip()
    
    # Masters patterns
    masters_patterns = ["master", "msc", "ma", "mba", "meng", "mtech", "ms", "m.sc", "m.a", "m.eng"]
    if any(pattern in text for pattern in masters_patterns):
        return "masters"
    
    # PhD patterns
    phd_patterns = ["phd", "ph.d", "doctorate", "doctoral"]
    if any(pattern in text for pattern in phd_patterns):
        return "phd"
    
    # Bachelors patterns
    bachelors_patterns = ["bachelor", "bsc", "ba", "beng", "btech", "bs", "b.sc", "b.a", "b.eng", "undergraduate"]
    if any(pattern in text for pattern in bachelors_patterns):
        return "bachelors"
    
    # Diploma patterns
    diploma_patterns = ["diploma", "certificate", "foundation", "postgraduate diploma", "pgdip"]
    if any(pattern in text for pattern in diploma_patterns):
        return "diploma"
    
    return "unknown"


def _get_country_name(code_or_name: str) -> str:
    """Convert country code to full name."""
    if not code_or_name:
        return ""
    upper = code_or_name.upper()
    return COUNTRY_CODE_MAP.get(upper, code_or_name)


def _safe_get(data: Optional[Dict], *keys, default=None):
    """Safely traverse nested dicts."""
    if data is None:
        return default
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return default
        if result is None:
            return default
    return result


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object."""
    if not date_str:
        return None
    try:
        if isinstance(date_str, date):
            return date_str
        if isinstance(date_str, datetime):
            return date_str.date()
        # Try common formats
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None
    except Exception:
        return None


def _normalize_signal(value: Any, thresholds: tuple = (40, 70)) -> str:
    """
    Normalize a numeric value to LOW/MEDIUM/HIGH signal.
    Thresholds: (low_max, high_min)
    """
    if value is None:
        return "UNKNOWN"
    try:
        num = float(value)
        low_max, high_min = thresholds
        if num < low_max:
            return "LOW"
        elif num >= high_min:
            return "HIGH"
        else:
            return "MEDIUM"
    except (ValueError, TypeError):
        return "UNKNOWN"


def _normalize_turnaround(value: Any) -> str:
    """Normalize turnaround time signal."""
    if value is None:
        return "UNKNOWN"
    try:
        num = float(value)
        if num >= 70:
            return "FAST"
        elif num >= 40:
            return "AVERAGE"
        else:
            return "SLOW"
    except (ValueError, TypeError):
        return "UNKNOWN"


def _extract_intakes(intakes_data: Optional[List[Dict]]) -> List[Dict]:
    """Extract and normalize intake information."""
    if not intakes_data:
        return []
    
    result = []
    for intake in intakes_data:
        if not isinstance(intake, dict):
            continue
        
        normalized = {
            "open_date": _parse_date(_safe_get(intake, "openDate")),
            "start_date": _parse_date(_safe_get(intake, "startDate")),
            "deadline": _parse_date(_safe_get(intake, "submissionDeadline")),
            "overall_score": _safe_get(intake, "overallScore"),
            "intent": _safe_get(intake, "intent"),
        }
        
        # Extract score details if present
        score_details = _safe_get(intake, "scoreDetails")
        if score_details and isinstance(score_details, list):
            for detail in score_details:
                label = _safe_get(detail, "scoreTypeLabel", default="").lower()
                score = _safe_get(detail, "score")
                
                if "conversion" in label:
                    normalized["conversion_score"] = score
                elif "seat" in label or "availability" in label:
                    normalized["seat_availability_score"] = score
                elif "turnaround" in label or "time" in label:
                    normalized["turnaround_score"] = score
        
        result.append(normalized)
    
    return result


def transform_program(program: Program, university: Optional[UniversityModel] = None) -> Dict[str, Any]:
    """
    Transform a single program record into normalized format.
    
    Args:
        program: Program ORM object
        university: Optional UniversityModel (if not embedded in program.attributes)
    
    Returns:
        Normalized dict ready for recommendation engine
    """
    attrs = program.attributes or {}
    school = attrs.get("school", {}) or {}
    
    # Use provided university or extract from program's school data
    uni_attrs = {}
    if university and university.attributes:
        uni_attrs = university.attributes
    
    # Extract program intakes
    intakes_raw = attrs.get("programIntakes", [])
    intakes = _extract_intakes(intakes_raw)
    
    # Get best intake scores (from first intake with scores, or overall)
    best_conversion = None
    best_seat = None
    best_turnaround = None
    
    for intake in intakes:
        if best_conversion is None and intake.get("conversion_score") is not None:
            best_conversion = intake["conversion_score"]
        if best_seat is None and intake.get("seat_availability_score") is not None:
            best_seat = intake["seat_availability_score"]
        if best_turnaround is None and intake.get("turnaround_score") is not None:
            best_turnaround = intake["turnaround_score"]
    
    # Also check top-level scoreDetails
    score_details = attrs.get("scoreDetails", [])
    if score_details and isinstance(score_details, list):
        for detail in score_details:
            label = _safe_get(detail, "scoreTypeLabel", default="").lower()
            score = _safe_get(detail, "score")
            
            if best_conversion is None and "conversion" in label:
                best_conversion = score
            if best_seat is None and ("seat" in label or "availability" in label):
                best_seat = score
            if best_turnaround is None and ("turnaround" in label or "time" in label):
                best_turnaround = score
    
    # Extract tuition fee
    tuition_fee = None
    tuition_data = attrs.get("tuitionFee")
    if tuition_data:
        if isinstance(tuition_data, (int, float)):
            tuition_fee = float(tuition_data)
        elif isinstance(tuition_data, dict):
            tuition_fee = _safe_get(tuition_data, "amount") or _safe_get(tuition_data, "value")
            if tuition_fee:
                tuition_fee = float(tuition_fee)
    
    # Extract cost of living
    cost_of_living = None
    col_data = attrs.get("costOfLiving") or _safe_get(school, "costOfLiving")
    if col_data:
        if isinstance(col_data, (int, float)):
            cost_of_living = float(col_data)
        elif isinstance(col_data, dict):
            cost_of_living = _safe_get(col_data, "amount") or _safe_get(col_data, "value")
            if cost_of_living:
                cost_of_living = float(cost_of_living)
    
    # Determine rank
    rank = None
    rank_data = uni_attrs.get("rank") or school.get("rank") or attrs.get("rank")
    if rank_data:
        try:
            rank = int(rank_data)
        except (ValueError, TypeError):
            pass
    
    return {
        # IDs
        "program_id": attrs.get("id") or program.id,
        "university_id": school.get("id") or (university.id if university else None),
        
        # University info
        "university_name": school.get("name") or uni_attrs.get("name") or "",
        "country": _get_country_name(school.get("country") or uni_attrs.get("country") or school.get("countryCode") or ""),
        "city": school.get("city") or uni_attrs.get("city") or "",
        "rank": rank,
        "institution_type": school.get("type") or uni_attrs.get("type") or "",
        "logo_thumbnail_url": school.get("logoThumbnailUrl") or school.get("logo", {}).get("url_thumbnail") if isinstance(school.get("logo"), dict) else school.get("logoThumbnailUrl") or "",
        
        # Program info
        "program_name": attrs.get("name") or "",
        "degree_level": attrs.get("level") or attrs.get("degreeLevel") or "",
        "tuition_fee": tuition_fee,
        "cost_of_living": cost_of_living,
        "application_fee": attrs.get("applicationFee"),
        
        # Signals (normalized)
        "conversion_signal": _normalize_signal(best_conversion),
        "seat_availability": _normalize_signal(best_seat),
        "turnaround_time": _normalize_turnaround(best_turnaround),
        
        # Raw scores for detailed analysis
        "conversion_score": best_conversion,
        "seat_availability_score": best_seat,
        "turnaround_score": best_turnaround,
        "overall_score": attrs.get("overallScore"),
        
        # Intakes
        "intakes": intakes,
        
        # Additional metadata
        "slug": attrs.get("slug"),
        "program_type": program.type,
    }


def fetch_and_transform_programs(
    db: Session,
    limit: int = 100,
    offset: int = 0,
    country_filter: Optional[str] = None,
    target_degree_level: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch programs from DB and transform to normalized format.
    
    HARD FILTERS (applied before scoring):
    - Degree level (if specified) - MANDATORY
    - Country (if specified)
    
    Args:
        db: Database session
        limit: Max records to return after filtering
        offset: Pagination offset
        country_filter: Optional country filter
        target_degree_level: Optional degree level filter (bachelors/masters/diploma/phd)
    
    Returns:
        List of normalized program dicts
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # OPTIMIZATION: Use smaller fetch limit and apply SQL-level filtering where possible
    # This reduces data transfer from DB and speeds up processing
    fetch_limit = min(200, limit * 3) if (country_filter or target_degree_level) else limit
    
    logger.info(f"🔍 Fetching programs from DB (limit={fetch_limit}, offset={offset})")
    
    # Build query with SQL-level country filtering if possible
    query = db.query(Program)
    
    # PostgreSQL JSON filtering for country (much faster than Python filtering)
    # NOTE: We search for BOTH full country names AND country codes
    if country_filter:
        country_lower = country_filter.lower()
        
        # Get all possible search terms (country codes + full name)
        search_terms = COUNTRY_NAME_TO_CODES.get(country_lower, [country_filter])
        search_terms.append(country_filter)  # Include original input
        
        # Build OR conditions for all search terms
        conditions = []
        for term in search_terms:
            # Search for the term in JSON attributes
            # stricter pattern: look for quoted term (e.g. "IE", "USA")
            pattern = f'%"{term}"%' 
            conditions.append(cast(Program.attributes, String).ilike(pattern))
            
            # Only use broad unquoted matching for longer terms (e.g. "Ireland")
            # This prevents "ie" matching "science" or "field"
            if len(term) > 3:
                pattern2 = f'%{term}%'
                conditions.append(cast(Program.attributes, String).ilike(pattern2))
        
        if conditions:
            query = query.filter(or_(*conditions))
        
        logger.info(f"🔍 Country filter applied for: {search_terms}")
    
    # SQL-level Degree Filtering (Heuristic)
    # This prevents fetching 200 "Bachelors" programs when user wants "Masters"
    if target_degree_level:
        degree_keywords = {
            "masters": ["master", "msc", "ma ", "mba", "m.sc", "m.a", "post grad"],
            "bachelors": ["bachelor", "bsc", "ba ", "undergrad", "b.sc", "b.a"],
            "phd": ["phd", "doctor", "dphil"],
            "diploma": ["diploma", "certificate", "associate"]
        }
        
        keywords = degree_keywords.get(target_degree_level.lower(), [])
        if keywords:
            degree_conditions = []
            for kw in keywords:
                # Search case-insensitive in the whole JSON dump
                # This is "good enough" for pre-filtering
                degree_conditions.append(cast(Program.attributes, String).ilike(f'%{kw}%'))
            
            if degree_conditions:
                query = query.filter(or_(*degree_conditions))
                logger.info(f"🎓 Degree pre-filter applied for {target_degree_level}: {keywords}")

    programs = query.offset(offset).limit(fetch_limit).all()
    logger.info(f"📊 Programs fetched from DB: {len(programs)}")
    
    results = []
    degree_filtered_count = 0
    degree_match_count = 0
    degree_unknown_count = 0
    
    for program in programs:
        try:
            normalized = transform_program(program)
            
            # HARD FILTER 1: Degree Level (3-state handling)
            if target_degree_level:
                # Extract degree from ALL available text sources (CRITICAL FIX)
                # Degree info is embedded in program names, not in a clean field
                program_name = normalized.get("program_name", "")
                raw_degree_field = normalized.get("degree_level", "")
                
                # Combine all text sources for degree detection
                degree_source_text = " ".join([
                    str(raw_degree_field or ""),
                    str(program_name or "")
                ]).strip()
                
                # Normalize based on combined text
                normalized_degree = normalize_degree_level(degree_source_text)
                
                # Store normalized degree for later use
                normalized["normalized_degree_level"] = normalized_degree
                
                # Determine degree match status
                degree_match_status = "unknown"
                
                if normalized_degree == target_degree_level:
                    degree_match_status = "match"
                    degree_match_count += 1
                elif normalized_degree == "unknown":
                    degree_match_status = "unknown"
                    degree_unknown_count += 1
                else:
                    # Clear mismatch (e.g., bachelors vs masters)
                    degree_filtered_count += 1
                    continue  # EXCLUDE only clear mismatches
                
                # Attach metadata to candidate for scoring penalty
                normalized["degree_match_status"] = degree_match_status
            
            # NOTE: Country filtering is now done at SQL level (see above)
            # No need for duplicate Python-level filtering
            
            results.append(normalized)
            
            # Stop once we have enough results
            if len(results) >= limit:
                break
                
        except Exception as e:
            # Log but don't fail on individual record errors
            logger.warning(f"Failed to transform program {program.id}: {e}")
            continue
    
    # Debug logging for pipeline visibility
    if target_degree_level:
        logger.info(f"🎓 Degree matches (exact): {degree_match_count}")
        logger.info(f"❓ Degree unknown (included with penalty): {degree_unknown_count}")
        logger.info(f"❌ Degree mismatches (excluded): {degree_filtered_count}")
    if country_filter:
        logger.info(f"🌍 Country filter applied at SQL level: {country_filter}")
    logger.info(f"✅ Final candidate pool sent to scoring engine: {len(results)}")
    
    return results


def fetch_single_program(db: Session, program_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch and transform a single program by ID.
    
    Args:
        db: Database session
        program_id: Program ID (string)
    
    Returns:
        Normalized program dict or None
    """
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        return None
    
    # Try to get associated university
    university = None
    school_id = _safe_get(program.attributes, "school", "id")
    if school_id:
        university = db.query(UniversityModel).filter(
            UniversityModel.id == str(school_id)
        ).first()
    
    return transform_program(program, university)


def get_programs_by_university(
    db: Session,
    university_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get all programs for a specific university.
    
    Args:
        db: Database session
        university_id: University ID
        limit: Max programs to return
    
    Returns:
        List of normalized program dicts
    """
    # Get the university
    university = db.query(UniversityModel).filter(
        UniversityModel.id == university_id
    ).first()
    
    # Fetch programs and filter by school.id in Python
    programs = db.query(Program).limit(limit * 3).all()
    
    results = []
    for program in programs:
        try:
            attrs = program.attributes or {}
            school = attrs.get("school", {}) or {}
            school_id = str(school.get("id", ""))
            
            if school_id != university_id:
                continue
                
            normalized = transform_program(program, university)
            results.append(normalized)
            
            if len(results) >= limit:
                break
        except Exception as e:
            print(f"Warning: Failed to transform program {program.id}: {e}")
            continue
    
    return results


# =============================================================================
# VALIDATION / SANITY CHECK
# =============================================================================

def validate_adapter(db: Session) -> Dict[str, Any]:
    """
    Validation helper - fetches one program and shows the normalized output.
    For developer sanity check only, not production.
    
    Args:
        db: Database session
    
    Returns:
        Dict with validation results
    """
    import json
    
    program = db.query(Program).first()
    if not program:
        return {"success": False, "error": "No programs found in database"}
    
    try:
        normalized = transform_program(program)
        
        # Pretty print for debugging
        print("=" * 60)
        print("ADAPTER VALIDATION")
        print("=" * 60)
        print(f"\nOriginal Program ID: {program.id}")
        print(f"Original Attributes Keys: {list((program.attributes or {}).keys())}")
        print(f"\n--- NORMALIZED OUTPUT ---")
        print(json.dumps(normalized, indent=2, default=str))
        print("=" * 60)
        
        return {
            "success": True,
            "original_id": program.id,
            "normalized": normalized
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_validation():
    """Run the validation check (entry point for testing)."""
    import sys
    sys.path.insert(0, ".")
    from db import SessionLocal
    
    db = SessionLocal()
    try:
        result = validate_adapter(db)
        return result
    finally:
        db.close()


if __name__ == "__main__":
    run_validation()
