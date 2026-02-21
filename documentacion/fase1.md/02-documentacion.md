ESTA ES LA ARQUITECTURA GENERAL DEL SISTEMA, PARA TENER UN MAYOR CONTROL DE ESTA MISMA. 

social_bot/
│
├── core/
│   ├── emotion_engine.py
│   ├── memory.py
│   └── decision_engine.py
│
├── models/
│   ├── state.py
│   └── interaction.py
│
├── storage/
│   └── database.py
│
├── utils/
│   ├── text_analyzer.py
│   └── logger.py
│
├── config/
│   └── settings.py
│
├── main.py
└── requirements.txt


EL FLUJO QUE SE TOMO PARA ESTA FASE ES LA SIGUIENTE 




---------------------------------------------------

PASO 1 MODELOS

models/state.py
definimos un estado emocional del bot 

models/interaction.py
Define una interacción con un usuario.

PASO 2 UTILIDADES 

utils/text_analyzer.py
Análisis de sentimiento básico sin ML externo.

utils/logger.py
Logger simple para depuración.

PASO 3 ALMACENAMIENTO

storage/database.py
Usaremos SQLite para persistencia simple.

PASO 4 CORE - MEMORIA

core/memory.py
Gestiona recuerdos a corto y largo plaZO

PASO 5 CORE - EMOTION ENGINE

core/emotion_engine.py
Maneja el estado emocional y sus transiciones.

PASO 6 CORE - DECISION ENGINE 

core/decision_engine.py
Toma decisiones sobre qué responder basado en el estado y la memoria.

PASO 7 CONFIGURACION

config/settings.py
Variables de configuración centralizadas.

PASO 8 MAIN CLI DE PRUEBA 

main.py
Punto de entrada con bucle de consola para probar.