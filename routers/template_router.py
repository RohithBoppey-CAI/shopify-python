from pathlib import Path
from fastapi import Request, Form, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

template_router = APIRouter(tags=["Template Serving"])


@template_router.get("/get-started", response_class=HTMLResponse)
async def get_started(request: Request, store: str):
    print(TEMPLATES_DIR)
    return templates.TemplateResponse(
        "get_started.html", {"request": request, "store": store}
    )


@template_router.post("/submit-details")
async def submit_details(
    store: str = Form(...),
    owner_name: str = Form(...),
    contact_email: str = Form(...),
    extra_info: str = Form(None),
):
    try:
        parsed_extra = json.loads(extra_info or "{}")
    except json.JSONDecodeError:
        parsed_extra = {}

    final_payload = {
        "store": store,
        "owner_name": owner_name,
        "contact_email": contact_email,
        "extra_info": parsed_extra,
    }

    print("📝 Final combined data:")
    print(final_payload)

    return {"status": "success", "message": final_payload}
