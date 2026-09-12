"""Public interface of the template module."""

from modules.template.models import Template
from modules.template.router import router
from modules.template.service import get_template, render

NAME = "template"

__all__ = ["NAME", "Template", "get_template", "render", "router"]
