"""Catálogo de atividades usado no mapeamento de operações."""

from __future__ import annotations

from app.application.ports import ActivityRepository
from app.domain.errors import InvalidInput
from app.domain.model import Activity
from app.domain.rules import normalize_name


class ActivitiesHandler:
    def __init__(self, activities: ActivityRepository):
        self._activities = activities

    def list(self) -> list[Activity]:
        return sorted(self._activities.list(), key=lambda a: a.name.casefold())

    def create(self, name: str, description: str = "") -> Activity:
        clean = normalize_name(name)
        if not clean:
            raise InvalidInput("Informe o nome da atividade.")
        existing = next((a for a in self._activities.list() if a.name.casefold() == clean.casefold()), None)
        return existing or self._activities.add(clean, description.strip())
