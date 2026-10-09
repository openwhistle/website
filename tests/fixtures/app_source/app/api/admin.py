from fastapi import APIRouter

router = APIRouter(prefix="/admin")
_LOGIN_METHODS = ["GET", "POST"]


@router.get("/dashboard")
async def dashboard() -> None: ...


@router.post("/reports/{report_id}/status")
async def status() -> None: ...


@router.api_route("/review-login", methods=_LOGIN_METHODS)
async def review_login() -> None: ...


@router.api_route("/anything")
async def anything() -> None: ...
