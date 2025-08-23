import os
from app.factory import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MINERU_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


