"""Public interface of the account module.

`CurrentUser` and `verify_token` are what other modules import: the first to receive
the signed-in user's id, the second to demand a signed-in caller and ignore it.
"""

from modules.account.models import Account
from modules.account.router import router
from modules.account.security import CurrentUser, verify_token

NAME = "account"

__all__ = ["NAME", "Account", "CurrentUser", "router", "verify_token"]
