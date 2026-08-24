from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from config.settings import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]
