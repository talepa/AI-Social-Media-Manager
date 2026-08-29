"""Specialist agents for the investigation pipeline."""

from app.agents.specialists import academic_specialist, repository_specialist, web_specialist
from app.schemas.investigation import SpecialistName, SpecialistResult, SubQuestion

_RUNNERS = {
    "web": web_specialist.run,
    "academic": academic_specialist.run,
    "repository": repository_specialist.run,
}

# Soft caps per specialist type (hard budget still comes from the plan).
_DEFAULT_CAPS: dict[SpecialistName, int] = {
    "web": 4,
    "academic": 3,
    "repository": 3,
}


def run_for_sub_question(
    sub_question: SubQuestion,
    *,
    max_tool_calls: int,
) -> SpecialistResult:
    runner = _RUNNERS.get(sub_question.specialist)
    if runner is None:
        return SpecialistResult(
            specialist=sub_question.specialist,
            sub_question_id=sub_question.id,
            error=f"Unknown specialist: {sub_question.specialist}",
        )
    cap = _DEFAULT_CAPS.get(sub_question.specialist, 4)
    return runner(sub_question, max_tool_calls=min(max_tool_calls, cap))
