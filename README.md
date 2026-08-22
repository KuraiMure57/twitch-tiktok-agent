# Twitch TikTok Agent

Agente automático para transformar clips de Twitch en contenido vertical preparado para revisión y publicación manual en TikTok.

## Objetivo

Twitch → descarga del clip → transcripción con Whisper → revisión del audio y transcripción con Gemini → generación de subtítulos → identificación de hablantes → colores por hablante → renderizado vertical → revisión mediante Telegram → correcciones → regeneración del vídeo → aprobación → publicación manual en TikTok.

## Principios

- El PC del usuario no necesita estar encendido.
- El agente no tendrá acceso a archivos personales del usuario.
- Ningún vídeo se publicará sin aprobación explícita.
- La publicación final en TikTok será siempre manual.
- El vídeo descargado desde Telegram será exactamente el vídeo final aprobado.
- Las correcciones realizadas desde Telegram regeneran el vídeo antes de su aprobación.
- Prioridad a herramientas gratuitas y open source.
- No contratar servicios de pago sin autorización.

## Componentes

- Twitch API
- GitHub Actions
- FFmpeg
- Whisper
- Google Gemini
- Telegram Bot API
- Python

## Flujo del sistema

### 1. Obtención del clip

El agente obtiene un clip de Twitch y descarga el vídeo para su procesamiento.

### 2. Transcripción

Whisper genera una primera transcripción con timestamps.

Esta transcripción se utiliza como base para el análisis posterior.

### 3. Revisión mediante Gemini

Gemini analiza el vídeo y escucha directamente el audio completo.

Compara el audio con la transcripción de Whisper para:

- Detectar frases omitidas.
- Corregir palabras mal transcritas.
- Mantener expresiones coloquiales y tacos.
- Añadir puntuación natural.
- Detectar exclamaciones.
- Mantener timestamps cuando sean correctos.
- Estimar timestamps para frases nuevas.
- Identificar diferentes hablantes.
- Mantener un identificador consistente para cada voz.

El streamer principal se identifica como:

`kuraimure`

Otros hablantes utilizan identificadores como:

` speaker_2`

` speaker_3`

etc.

### 4. Validación

La respuesta de Gemini se valida antes de continuar.

Se comprueba:

- Estructura JSON.
- Campos obligatorios.
- Segmentos válidos.
- Timestamps.
- Orden cronológico.
- Ausencia de solapamientos.
- Identificación de hablantes.

### 5. Generación de subtítulos

Los subtítulos se generan en formato ASS.

Cada hablante puede tener un estilo/color diferente.

Los subtítulos incluyen:

- Texto grande para formato vertical.
- Color asociado al hablante.
- Contorno para mejorar la legibilidad.
- Censura automática de determinadas palabras.
- Identificación mediante estilos ASS.

### 6. Renderizado vertical

El vídeo se prepara para formato vertical 1080x1920 utilizando FFmpeg.

Los subtítulos se incrustan directamente en el vídeo final.

### 7. Revisión mediante Telegram

El vídeo se envía automáticamente al bot de Telegram.

El usuario puede:

- ✅ Autorizar el clip.
- ✏️ Corregir los subtítulos.
- ❌ Descartar el clip.

Al seleccionar "Corregir texto", Telegram muestra los subtítulos actuales numerados.

Ejemplo:

1. Hola chicos  
2. Esto es increíble  
3. No puede ser  

### 8. Corrección de subtítulos desde Telegram

Se pueden corregir únicamente los textos sin necesidad de volver a escribir el hablante.

Formato:

`3. Texto corregido`

También se puede cambiar el hablante:

`3. @speaker_3`

O hacer ambas cosas:

`3. @speaker_3 Texto corregido`

Esto permite separar fácilmente:

- Corrección de texto.
- Cambio de hablante.
- Corrección de texto + cambio de hablante.

### 9. Inserción de nuevas frases

También es posible insertar nuevas frases entre subtítulos existentes.

Ejemplo:

`2.1 Nueva frase`

`2.2 Otra frase`

`3.1 Frase después del 3`

El sistema calcula automáticamente los tiempos cuando existe espacio disponible.

También se pueden especificar manualmente:

`2.1 [0.4-0.5] Nueva frase`

### 10. Regeneración

Después de una corrección:

1. Se actualizan los subtítulos.
2. Se guarda la nueva versión.
3. Se vuelve a generar el ASS.
4. Se vuelve a renderizar el vídeo.
5. El nuevo vídeo se envía a Telegram.
6. El usuario vuelve a revisarlo.

El proceso puede repetirse hasta que el vídeo sea correcto.

### 11. Aprobación

Cuando el usuario pulsa:

`✅ Autorizar`

el clip queda marcado como aprobado.

Si pulsa:

`❌ Descartar`

el clip queda rechazado.

### 12. Publicación

Actualmente la publicación final en TikTok es manual.

El agente prepara el contenido y proporciona los datos necesarios para la publicación.

No se realiza ninguna publicación automática sin autorización.

## Estado actual

- [x] Repositorio GitHub creado
- [x] GitHub Actions configurado
- [x] FFmpeg configurado
- [x] Twitch API
- [x] Descarga de clips
- [x] Procesamiento de vídeo
- [x] Transcripción mediante Whisper
- [x] Análisis mediante Gemini
- [x] Revisión del audio completo mediante Gemini
- [x] Corrección de transcripciones
- [x] Detección de frases omitidas
- [x] Identificación de hablantes
- [x] Identificadores consistentes por hablante
- [x] Colores de subtítulos por hablante
- [x] Generación de subtítulos ASS
- [x] Censura automática de determinadas palabras
- [x] Vídeo vertical 1080x1920
- [x] Validación de la respuesta de Gemini
- [x] Sistema de revisión mediante Telegram
- [x] Corrección de subtítulos desde Telegram
- [x] Cambio de hablante desde Telegram
- [x] Inserción de nuevas frases
- [x] Control manual de timestamps
- [x] Regeneración automática del vídeo tras una corrección
- [x] Revisión repetida del vídeo
- [x] Sistema de aprobación
- [x] Sistema de descarte
- [x] Generación de metadatos
- [x] Generación de hashtags
- [x] Mensaje final para publicación
- [x] Prueba completa del flujo
