#!/bin/bash
uvicorn api.app:app --host 0.0.0.0 --port 8000 &
python main.py
```

Luego en Railway en el servicio de la API ve a:
```
Settings → Deploy → Start Command
```
Cámbialo a:
```
bash start.sh