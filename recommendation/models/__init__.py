# Export all recommendation models for easy imports
from .base import Base
from .university import RecUniversity
from .program import RecProgram
from .intake import RecIntake
from .eligibility_snapshot import RecEligibilitySnapshot
from .context_knowledge import RecContextKnowledge

__all__ = [
    "Base",
    "RecUniversity",
    "RecProgram",
    "RecIntake",
    "RecEligibilitySnapshot",
    "RecContextKnowledge",
]
