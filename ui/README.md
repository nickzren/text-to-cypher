# Text-to-Cypher UI

## 🛠 Tech Stack

- **Vue 3**
- **PrimeVue**
- **TypeScript**
- **Vite**
- **Axios**

---

## 🚀 Initial Setup

**Step 1: Install Dependencies**

From the `ui` directory, run:

```bash
npm install
```

**Step 2: ▶️ Running the Frontend & Backend**

Start the frontend development server, from the `ui` directory, run:
```bash
cd ui/
npm run dev
```

Launch the backend API (FastAPI), back to root directory, run:
```bash
uv run uvicorn src.api_server:app --reload
```

The backend exposes `/api/schema`, which the UI fetches to display a "Schema Viewer" panel listing all node labels and relationship types.

Each browser session is identified by a random ID stored in `localStorage`. This
ID is sent with API requests so that chat history is kept separate for each user
without any account system.

