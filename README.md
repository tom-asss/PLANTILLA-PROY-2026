# PROY-2026-GRUPO 1

Repositorio del grupo 1 para el proyecto del ramo *Proyecto Inicial (IWG400)* – 2026.

## 👥 Integrantes del grupo

| Nombre y Apellido | Usuario GitHub | Correo USM               | Rol USM      |
| ----------------- | -------------- | ------------------------ | ------------ |
| Antonella Zavala  | @antoinsana    | azavalao@usm.cl          |202630007-2   |
| Fernanda Cisternas| @ferpou        | fcisternas@usm.cl        |202630033-1   |
| Tomás Farías      | @tom-asss      | tfariasp@usm.cl          |202630004-8   |

## 📝 Descripción breve del proyecto

> *B.R.U.N.E:(Buen Rendimiento Académico, No Excusas), un programa el cual te ayudará a estudiar sin restricciones
> .*

---

## 🎯 Objetivos

- Objetivo general:
  Desarrollar un asistente de estudio personal controlado por voz e inteligencia artificial que permita optimizar las sesiones de estudio y el rendimiento académico.
- Objetivos específicos:
   - Implementar reconocimiento de voz local mediante Whisper de OpenAI.
  - Integrar inteligencia artificial mediante la API de Gemini para responder preguntas y ejecutar acciones.
  - Desarrollar una calculadora de notas con indique cuánto necesitas para aprobar.
  - Crear un sistema de gestión de evaluaciones con cuenta regresiva y alertas.
  - Implementar un temporizador de estudio con historial de sesiones.
  - Vincular automáticamente el material de estudio de cada ramo (Google Drive, Almacén Camello, Aula USM) al activar el modo de estudio.

---

## 🧩 Alcance del proyecto

> El proyecto tiene ciertas limitaciones. El programa depende de tener Python instalado localmente. Se pudo haber trabajado en la generación de un ejecutable .exe para no depender de esto. Además, el programa está configurado únicamente para los ramos del primer semestre de 2026, de la malla actual de Ingeniería Civil Telemática, lo que es un limitante en el caso que cualquier otra persona desee usar el programa con sus propios ramos.  

---

## 🛠️ Tecnologías y herramientas utilizadas

- **Lenguaje(s) de programación:**  Python 3.12
- **Interfaz gráfica:** Tkinter
- **Reconocimiento de voz:** Whisper (OpenAI) — modelo base, corre localmente
- **Inteligencia artificial:** Gemini API (Google) — tier gratuito
- **Síntesis de voz:** pyttsx3
- **Captura de audio:** sounddevice + numpy
- **Persistencia de datos:** JSON
---

## 🗂️ Estructura del repositorio

```
/PLANTILLA-PROY-2026
│
├── brune.py              # Código principal de BRUNE
├── instalar_brune.bat    # Instalador automático para Windows
├── requirements.txt      # Lista de librerías necesarias
├── instrucciones.txt     # Guía detallada de instalación y uso
└── README.md             # Este archivo

```

---

## 🚀 Instrucciones de Instalacion y Uso

## 1. INSTALACIÓN

### Opción A — Automática

- Descargar todos los archivos del repositorio (botón verde **Code → Download ZIP**)
- Descomprimir la carpeta
- Hacer doble clic en `instalar_brune.bat`
- Seguir las instrucciones en pantalla

### Opción B - Manual

1. Desde la carpeta de BRUNE, ejecutar la consola de comandos e instalar librerías necesarias ejecutando `pip install -r requirements.txt`
2. Ejecutar `python -c "import whisper; whisper.load_model('base')"`

### 2. EJECUCIÓN
```bash
python brune.py
```
**Instrucciones de instalación mas detalladas en el archivo `instrucciones.txt`**

---



## 📅 Cronograma de trabajo

[Carta Gantt](https://docs.google.com/spreadsheets/d/1q-dBlOUje1763kOuwquhEZ8v435y_sau/edit?usp=sharing&ouid=104493038817783717056&rtpof=true&sd=true)

---

## 📚 Bibliografía

- [Google Gemini API](https://ai.google.dev/gemini-api/docs) 
- [OpenAI Whisper](https://openai.com/index/whisper/) 
- [Python tkinter](https://docs.python.org/3/library/tkinter.html) 
- [pyttsx3](https://pypi.org/project/pyttsx3/) 
- [sounddevice](https://python-sounddevice.readthedocs.io/)

---
