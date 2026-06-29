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


class CodeOutput(BaseModel):
    files_created: list[FileChange] = []
    files_modified: list[FileChange] = []
    summary: str = ""
    dependencies_installed: list[str] = []


class TestSuiteResult(BaseModel):
    passed: int = 0
    failed: int = 0
    errors: list[str] = []
    tracebacks: list[str] = []
    coverage_pct: float | None = None
    test_files: list[str] = []


class ReviewIssue(BaseModel):
    file: str
    line: int | None = None
    severity: str = "info"
    description: str
    root_cause: str
    fix_suggestion: str


class ReviewFindings(BaseModel):
    issues: list[ReviewIssue] = []
    summary: str = ""
    should_fix: bool = True


class DocOutput(BaseModel):
    files_created: list[str] = []
    summary: str = ""


class GateResult(BaseModel):
    passed: bool
    issues: list[str] = []
    severity: str = "blocking"


class PipelineResult(BaseModel):
    status: str = "unknown"
    plan: Plan | None = None
    code: CodeOutput | None = None
    test_results: list[TestSuiteResult] = []
    review: ReviewFindings | None = None
    doc: DocOutput | None = None
    files: list[str] = []
    error: str | None = None
    iterations_used: int = 0
    elapsed_seconds: float = 0.0
