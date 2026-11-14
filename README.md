# FinThread

Graph-based detection of layered money-laundering networks (Build Beyond'26, PS 2.1).
Investigation support and risk prioritisation only, not proof of wrongdoing.

Read `PROJECT_CONTRACT.md` before writing code.

| Folder | Owner | Branch |
|---|---|---|
| `frontend/` | Member 1 | `feat/frontend` |
| `backend/app` (core, detection, pipeline) | Member 2 (Integration Lead) | `feat/backend` |
| `backend/app/intelligence`, `backend/app/evaluation`, `backend/scripts`, `backend/data` | Member 3 | `feat/intel` |

## Run the backend (Windows)

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
API docs: http://localhost:8000/docs
