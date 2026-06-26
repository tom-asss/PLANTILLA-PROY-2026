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

echo [ERROR] No se encontro Python en tu PC.
echo.
echo Sigue estos pasos:
echo  1. Ve a https://www.python.org/downloads/
echo  2. Descarga Python 3.12 (recomendado)
echo  3. Al instalar, MARCA la casilla "Add Python to PATH"
echo  4. Reinicia el computador
echo  5. Vuelve a ejecutar este archivo
echo.
pause
exit /b

:python_encontrado
echo [1/6] Python detectado correctamente. (comando: %PYTHON_CMD%)
%PYTHON_CMD% --version
echo.

:: Actualizar pip
echo Actualizando pip...
%PYTHON_CMD% -m pip install --upgrade pip
echo.

:: Instalar librerias base
echo [2/6] Instalando librerias principales...
%PYTHON_CMD% -m pip install google-genai sounddevice openai-whisper pywin32
echo.

:: Instalar pyttsx3 (voz)
echo [3/6] Instalando modulo de voz (pyttsx3)...
%PYTHON_CMD% -m pip install pyttsx3==2.90
if errorlevel 1 (
    echo     Intentando version alternativa de pyttsx3...
    %PYTHON_CMD% -m pip install pyttsx3
)
if errorlevel 1 (
    echo     [AVISO] pyttsx3 no se pudo instalar.
    echo     BRUNE funcionara sin voz. Esto puede ocurrir con Python 3.14 o superior.
    echo     Se recomienda usar Python 3.12 para tener voz.
)
echo.

:: Instalar pyaudio con metodos alternativos
echo [4/6] Instalando PyAudio (microfono)...
%PYTHON_CMD% -m pip install pyaudio > nul 2>&1
if not errorlevel 1 (
    echo     PyAudio instalado correctamente.
    goto :pyaudio_ok
)
echo     Metodo 1 fallo, intentando con pipwin...
%PYTHON_CMD% -m pip install pipwin > nul 2>&1
pipwin install pyaudio > nul 2>&1
if not errorlevel 1 (
    echo     PyAudio instalado correctamente con pipwin.
    goto :pyaudio_ok
)
echo.
echo     [AVISO] PyAudio no pudo instalarse automaticamente.
echo     El microfono puede no funcionar.
echo     Para instalarlo manualmente ejecuta:
echo        pip install pipwin
echo        pipwin install pyaudio
echo.

:pyaudio_ok
echo.

:: Descargar modelo Whisper
echo [5/6] Descargando modelo de reconocimiento de voz Whisper (~74MB)...
echo       Esto puede tardar varios minutos segun tu internet.
echo       NO cierres esta ventana.
%PYTHON_CMD% -c "import whisper; whisper.load_model('base'); print('[OK] Modelo Whisper descargado correctamente.')"
if errorlevel 1 (
    echo.
    echo     [ERROR] No se pudo descargar Whisper.
    echo     Verifica tu conexion a internet e intenta de nuevo.
    echo     O ejecuta manualmente:
    echo        python -c "import whisper; whisper.load_model('base')"
)
echo.

:: Recordatorio API key
echo [6/6] Configuracion de API key de Gemini (IA)
echo ============================================
echo.
echo  IMPORTANTE: Para que la inteligencia artificial funcione
echo  necesitas obtener una API key gratuita de Gemini:
echo.
echo  1. Ve a https://aistudio.google.com
echo  2. Inicia sesion con tu cuenta Google
echo  3. Haz clic en "Get API key" y luego "Create API key"
echo  4. Copia el codigo que aparece (empieza con AIza...)
echo  5. Abre el archivo brune.py con el Bloc de notas
echo  6. Busca la linea 25 que dice:
echo        GEMINI_API_KEY = "PEGA_TU_API_KEY_AQUI"
echo  7. Reemplaza PEGA_TU_API_KEY_AQUI por tu key
echo     (mantén las comillas "")
echo  8. Guarda el archivo con Ctrl+S
echo.
echo ============================================
echo  Instalacion completada!
echo  Completa el paso de la API key y ejecuta brune.py
echo ============================================
echo.
pause
