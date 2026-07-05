import sys
import uvicorn

if __name__ == "__main__":
    sys.path.insert(0, '.')
    from app.main import app
    uvicorn.run(app, host='0.0.0.0', port=8000)