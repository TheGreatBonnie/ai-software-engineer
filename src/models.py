from pydantic import BaseModel


class Plan(BaseModel):
    objective: str
    tasks: list[str]
    dependencies: dict[str, list[str]]
    milestones: list[str]


class FileChange(BaseModel):
    path: str
    action: str  # "create" | "modify" | "delete"
    description: str
