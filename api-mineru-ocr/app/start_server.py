from app.main import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.start_server:app", host="0.0.0.0", port=8000)


