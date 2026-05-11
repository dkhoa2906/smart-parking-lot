from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.init_db import init_db
from app.routers import slots, history, users, lots


app = FastAPI(
    title="Smart Parking Lot API",
    version="1.0.0",
    description=(
        "Backend API for the Smart Parking Lot system (Group 7 - CMP6210).\n\n"
        "**Authentication:** All `/slots` and `/history` endpoints require a Bearer JWT token.\n"
        "Obtain a token via `POST /users/login`, then click **Authorize** and paste the token."
    ),
    contact={"name": "Group 7", "email": "dang.cao@mail.bcu.ac.uk"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to CloudFront URL when deploying to production
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(lots.router)
api.include_router(users.router)
api.include_router(slots.router)
api.include_router(history.router)

app.include_router(api)

@app.on_event("startup")
def startup():
    init_db()  # only creates tables when USE_SQLITE=true (local test)


@app.get("/health", tags=["health"], summary="Health check")
def health_check():
    """Returns 200 OK if the API is running."""
    return {"status": "ok"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        contact=app.contact_info if hasattr(app, "contact_info") else None,
        routes=app.routes,
    )
    # Add HTTPBearer security scheme so the Swagger UI shows an "Authorize" button
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict):
                operation.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
