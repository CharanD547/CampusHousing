# Roomwise frontend

The supplied design is integrated with the Roomwise FastAPI backend. Its former fixture data and fixture router have been replaced by same-origin API requests.

From the workspace root:

```powershell
.\.venv\Scripts\python.exe tools/build_frontend.py
.\.venv\Scripts\python.exe -m uvicorn roomwise.main:app --app-dir src --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/. Opening `index.html` directly or using a generic static server does not provide the API.

`src/api.js` owns loading, workspace sync, comparisons, checklist requests, AI availability and server brief retrieval. `core.js` owns browser state and display helpers. `views1.js`, `views2.js` and `views3.js` retain the supplied screens. `app.js` routes and handles input. `data.js` holds empty API-populated collections and presentation constants. The hero image is illustrative.

The main [README](../README.md) describes verification and remaining provider limits. An original input backup is retained in ignored `var/frontend-input-original.zip`.
