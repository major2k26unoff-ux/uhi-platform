from fastapi import FastAPI

app = FastAPI(
    title="Urban Heat Island API",
    description="Serves satellite-derived heat and greenery layers",
    version="0.1.0"
)

@app.get("/")
def root():
    return {"message": "UHI API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}
