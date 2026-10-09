from fastapi import APIRouter, Response

router = APIRouter()
_CSRF_COOKIE = "ow_csrf"


async def submit_get(response: Response) -> None:
    response.set_cookie("ow_session", "x")
    response.set_cookie(key="ow-lang", value="en")


router.add_api_route("/submit/{org_slug}", submit_get, methods=["GET"])
router.add_api_route("/submit/{org_slug}/restart", submit_get, methods=["POST"])
router.include_router(APIRouter())
