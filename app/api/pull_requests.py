from fastapi import APIRouter

from app.schemas.pull_request import PullRequestDetailResponse
from app.services.github_service import github_service

router = APIRouter(prefix="/api/pull-requests", tags=["Pull Requests"])


@router.get("/{owner}/{repo}/{number}", response_model=PullRequestDetailResponse)
async def get_pull_request_details(owner: str, repo: str, number: int):
    """
    Get detailed Pull Request metadata, commit SHAs, file-by-file patch changes, and raw diff.
    """
    pr_data = await github_service.get_pull_request(owner, repo, number)
    files = await github_service.get_pull_request_files(owner, repo, number)
    diff = await github_service.get_diff(owner, repo, number)

    return PullRequestDetailResponse(
        repository=f"{owner}/{repo}",
        pull_request=number,
        number=number,
        title=pr_data.get("title", ""),
        description=pr_data.get("description"),
        author=pr_data.get("author", "unknown"),
        state=pr_data.get("state", "open"),
        base_sha=pr_data.get("base_sha", ""),
        head_sha=pr_data.get("head_sha", ""),
        files=files,
        diff=diff
    )
