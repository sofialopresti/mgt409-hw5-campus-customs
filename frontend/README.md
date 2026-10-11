# Campus Customs Front Desk Board

React + Vite + TypeScript board for the agent team. It calls the desk API (`backend/main.py`) at
`http://localhost:8000`.

1. Start the backend (from `backend/`, with `.venv` active): `uvicorn main:app --reload --port 8000`
2. Start the board (from `frontend/`): `npm run dev`, then open http://localhost:5173

The board runs on port 5173 because that's the origin the backend allows (CORS).
The design rationale is in `output/design.md`.
