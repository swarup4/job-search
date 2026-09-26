"""Public interface of the agents package.

Named after the capability each performs, not the resource it touches. Phase 5 calls
these directly; Phase 8 wraps them in the LangGraph supervisor.
"""

from agents.matching import rectify
from agents.tailoring import tailor

__all__ = ["rectify", "tailor"]
