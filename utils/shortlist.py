from typing import Iterable, List
from ..models.models import University, ShortlistPreference, ShortlistItem

def score_universities(unis: Iterable[University], prefs: ShortlistPreference) -> List[ShortlistItem]:
    items: List[ShortlistItem] = []
    for u in unis:
        score = 0.5
        if prefs.country and prefs.country.lower() == u.country.lower():
            score += 0.2
        if prefs.program and prefs.program in u.programs:
            score += 0.2
        if prefs.budget and u.tuition <= prefs.budget:
            score += 0.1
        items.append(ShortlistItem(university=u.name, country=u.country, tuition=u.tuition, programs=u.programs, match_score=round(score,2)))
    return sorted(items, key=lambda x: x.match_score, reverse=True)
