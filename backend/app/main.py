from fastapi import FastAPI

from app.api.responses import problem_responses
from app.api.routes import health, incidents
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.openapi import use_problem_json_in_openapi

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug, responses=problem_responses(500))
register_error_handlers(app)
use_problem_json_in_openapi(app)
app.include_router(health.router)
app.include_router(incidents.router)
