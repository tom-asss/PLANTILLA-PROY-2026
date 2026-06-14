@echo off
chcp 65001 > nul
echo.
echo ============================================
echo       INSTALADOR DE BRUNE v1.0
echo   Buen Rendimiento Universitario, No Excusas
echo ============================================
echo.

:: Verificar que Python esté instalado
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado en tu PC.
    echo Descárgalo desde: https://www.python.org/downloads/
    echo Asegúrate de marcar "Add Python to PATH" al instalar.
    pause
    exit /b
)

echo [1/4] Python detectado correctamente.
echo.

:: Instalar librerías
echo [2/4] Instalando librerías necesarias...
pip install google-genai pyttsx3 pyaudio sounddevice openai-whisper psutil
echo.

:: Descargar modelo Whisper
echo [3/4] Descargando modelo de reconocimiento de voz (Whisper base ~74MB)...
echo       Esto puede tardar 1-3 minutos dependiendo de tu internet.
python -c "import whisper; whisper.load_model('base'); print('Modelo descargado correctamente.')"
echo.

:: Recordatorio API key
echo [4/4] IMPORTANTE: Antes de ejecutar BRUNE debes agregar tu API key de Gemini.
echo.
echo       1. Ve a https://aistudio.google.com y crea una cuenta Google
echo       2. Haz clic en "Get API key" y copia tu key
echo       3. Abre el archivo brune.py con cualquier editor de texto
echo       4. Busca la línea que dice: GEMINI_API_KEY = "PEGA_TU_API_KEY_AQUÍ"
echo       5. Reemplaza PEGA_TU_API_KEY_AQUÍ por tu key (sin borrar las comillas)
echo       6. Guarda el archivo
echo.
echo ============================================
echo  Instalación completada. 
echo  Completa el paso 4 y luego ejecuta brune.py
echo ============================================
echo.
pause