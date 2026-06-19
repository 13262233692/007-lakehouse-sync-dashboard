import uvicorn
from pathlib import Path
import os

if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
