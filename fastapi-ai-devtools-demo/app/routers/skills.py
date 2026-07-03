"""Skills endpoint: the curated, public-safe skills the demo offers.

GET /skills lists the PROMPT-ONLY skills enabled on this endpoint. OpenJarvis
tool execution, file access, web-search, code execution, and outbound/messaging
integrations are DISABLED here; only safe, prompt-only skills are exposed.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.skills import SkillRegistry

router = APIRouter(tags=["skills"])


class SkillInfo(BaseModel):
    id: str
    label: str
    description: str
    grounded: bool


class SkillListResponse(BaseModel):
    default: str
    skills: list[SkillInfo]


@router.get(
    "/skills",
    response_model=SkillListResponse,
    summary="List the curated, public-safe skills",
)
async def list_skills() -> SkillListResponse:
    registry = SkillRegistry.default()
    return SkillListResponse(
        default=registry.default_skill.id,
        skills=[
            SkillInfo(
                id=s.id,
                label=s.label,
                description=s.description,
                grounded=s.grounded,
            )
            for s in registry.skills
        ],
    )
