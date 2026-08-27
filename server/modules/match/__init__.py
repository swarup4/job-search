"""Public interface of the match module."""

from modules.match.models import (
    KeywordReview,
    KeywordSelection,
    Match,
    MatchFindings,
    MatchRead,
    MatchWrite,
    MissingKeyword,
    PendingCounts,
    PresentKeyword,
    ReviewState,
    RiskFlag,
)
from modules.match.router import router
from modules.match.service import (
    MatchNotFound,
    UnknownKeyword,
    get_match,
    pending_counts,
    record_selection,
    write_match,
)

NAME = "match"

__all__ = [
    "NAME",
    "KeywordReview",
    "KeywordSelection",
    "Match",
    "MatchFindings",
    "MatchNotFound",
    "MatchRead",
    "MatchWrite",
    "MissingKeyword",
    "PendingCounts",
    "PresentKeyword",
    "ReviewState",
    "RiskFlag",
    "UnknownKeyword",
    "get_match",
    "pending_counts",
    "record_selection",
    "router",
    "write_match",
]
