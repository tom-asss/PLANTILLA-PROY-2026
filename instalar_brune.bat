@echo off
chcp 65001 > nul
echo.
echo ============================================
echo       INSTALADOR DE BRUNE v1.0
echo   Buen Rendimiento Universitario, No Excusas
echo ============================================
echo.

:: Detectar comando de Python disponible
set PYTHON_CMD=
python --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :python_encontrado
)
py --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :python_encontrado
)
python3 --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto :python_encontrado
)

:: Si llegó aquí, no encontró Python
echo [ERROR] No se encontró Python en tu PC.
echo.
echo Sigue estos pasos:
echo  1. Ve a https://www.python.org/downloads/
echo  2. Descarga Python 3.10 o superior
echo  3. Al instalar, MARCA la casilla "Add Python to PATH"
echo  4. Vuelve a ejecutar este archivo
echo.
pause
exit /b

:python_encontrado
echo [1/4] Python detectado correctamente. (comando: %PYTHON_CMD%)
echo.

:: Instalar librerias
echo [2/4] Instalando librerias necesarias...
%PYTHON_CMD% -m pip install google-genai pyttsx3 pyaudio sounddevice openai-whisper
echo.

:: Descargar modelo Whisper
echo [3/4] Descargando modelo de reconocimiento de voz (Whisper base ~74MB)...
echo       Esto puede tardar 1-3 minutos dependiendo de tu internet.
%PYTHON_CMD% -c "import whisper; whisper.load_model('base'); print('Modelo descargado correctamente.')"
echo.

:: Recordatorio API key
echo [4/4] IMPORTANTE: Antes de ejecutar BRUNE debes agregar tu API key de Gemini.
echo.
echo       1. Ve a https://aistudio.google.com y crea una cuenta Google
echo       2. Haz clic en "Get API key" y copia tu key
echo       3. Abre el archivo brune.py con cualquier editor de texto
echo       4. Busca la linea que dice: GEMINI_API_KEY = "PEGA_TU_API_KEY_AQUI"
echo       5. Reemplaza PEGA_TU_API_KEY_AQUI por tu key (sin borrar las comillas)
echo       6. Guarda el archivo
echo.
echo ============================================
echo  Instalacion completada.
echo  Completa el paso 4 y luego ejecuta brune.py
echo ============================================
echo.
pause
