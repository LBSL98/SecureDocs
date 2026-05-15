from fastapi import FastAPI

from app.routes import audit, auth, documents

app = FastAPI(title="SecureDocs")

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(audit.router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
