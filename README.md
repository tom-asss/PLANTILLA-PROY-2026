# PROY-2026-GRUPO 1

Repositorio del grupo 1 para el proyecto del ramo *Proyecto Inicial (IWG400)* – 2026.

## 👥 Integrantes del grupo

| Nombre y Apellido | Usuario GitHub | Correo USM               | Rol USM      |
| ----------------- | -------------- | ------------------------ | ------------ |
| Antonella Zavala  | @antoinsana    | azavalao@usm.cl          |202630007-2   |
| Fernanda Cisternas| @ferpou        | fcisternas@usm.cl        |202630033-1   |
| Tomás Farías      | @tom-asss      | tfariasp@usm.cl          |202630004-8   |

## 📝 Descripción breve del proyecto

> *B.R.U.N.E:(Buen Rendimiento Académico, No Excusas), un programa el cual te ayudará a estudiar sin reestricciones,
> .*

---

## 🎯 Objetivos

- Objetivo general:
  Creación de un programa que permita bloquear ventanas y programas a la hora de estudiar, además de monitorear pulso cardíaco, de estrés y somnolencia.
- Objetivos específicos:
  -Creación de software que bloquee ventanas y programas.
  -Conexión de sensores de pulso cardíaco y sensor de respuesta galvánica de la piel, que midan niveles de estrés y somnolencia. Estará conectado al programa y notificará en caso de detectar niveles alterados.
  -Implementar monitoreo de somnolencia a través de una webcam, que en caso de percibir que los ojos se estén cerrando, mande una señal de alerta para despertar al usuario.
  -Vinculación del software a distintas páginas y aplicaciones asignadas por el usuario.

---

## 🧩 Alcance del proyecto

> El proyecto a futuro, busca mejorar la precisión de los sensores. Sin embargo, algunas de nuestras limitaciones son nuestro conocimiento en programación, la baja precisión del sensor de pulso cardíaco debido a su tamaño, y el tiempo que tenemos podría ser insuficiente para lograr todos nuestros objetivos.  

---

## 🛠️ Tecnologías y herramientas utilizadas

- Lenguaje(s) de programación:
  - C++
- Microcontroladores
  - Arduino UNO Q
  - Sensores de pulso cardíaco, sensor de respuesta galvánica de la piel, buzzer.

---

## 🗂️ Estructura del repositorio

```
/PROY-2026-GRUPOX
│
├── docs/               # Documentación general y reportes
├── src/                # Código fuente del proyecto
├── tests/              # Casos de prueba
├── assets/             # Imágenes, diagramas, etc.
└── README.md           # Este archivo
```

---

## 🚀 Instrucciones de Instalacion y Uso


## 1. REQUISITOS PREVIOS:
 -Python 3.10 o superior
- Micrófono conectado
- Conexión a internet
## 2. INSTALACIÓN
### Opción A — Automática
- Descargar todos los archivos del repositorio (botón verde **Code → Download ZIP**)
- Descomprimir la carpeta
- Hacer doble clic en `instalar_brune.bat`
- Seguir las instrucciones en pantalla

### Opción B - Manual

1. Desde la carpeta de BRUNE, ejecutar la consola de comandos e instalar librerías necesarias ejecutando `pip install -r requirements.txt`
2. Ejecutar `python -c "import whisper; whisper.load_model('base')"`

### 3. EJECUCIÓN
```bash
python brune.py
```

---

## 📐 Diseño del Sistema
![Diagrama de Conexiones](./assets/diagrama_conexiones.png)

*Explicacion grafica de como es la conexion entre el microcontrolador y los sensores*

---

## 📅 Cronograma de trabajo

[Carta Gantt](https://google.com)

---

## 📚 Bibliografía

[Google Gemini API](https://ai.google.dev/gemini-api/docs)

---

## 📌 Notas adicionales

> *Espacio para dejar cualquier comentario útil, como pendientes, acuerdos del grupo, consideraciones especiales, etc.*
