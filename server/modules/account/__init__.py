"""Public interface of the account module."""

from modules.account.models import Account
from modules.account.router import router

NAME = "account"

__all__ = ["NAME", "Account", "router"]
