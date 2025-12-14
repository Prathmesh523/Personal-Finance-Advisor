from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(
    title="Personal Finance Advisor API",
    description="AI-powered financial reconciliation and analytics",
    version="1.0.0"
)

# Configure CORS (allow frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes
from app.api import routes

# Include routers
app.include_router(routes.router, prefix="/api/v1")

# Root endpoint
@app.get("/")
def root():
    return {
        "message": "Personal Finance Advisor API",
        "version": "1.0.0",
        "docs": "/docs"
    }
    