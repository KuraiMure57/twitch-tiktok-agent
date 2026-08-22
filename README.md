# Twitch TikTok Agent

Agente automático para transformar clips de Twitch en contenido listo para publicar manualmente en TikTok.

## Objetivo

Twitch → procesamiento → subtítulos → Telegram → corrección → aprobación → mensaje con datos TikTok → descargar vídeo → subir manualmente a TikTok.

## Principios

- El PC del usuario no necesita estar encendido.
- El agente no tendrá acceso a archivos personales del usuario.
- Ningún vídeo se publicará sin aprobación explícita.
- La publicación final en TikTok será siempre manual.
- El vídeo descargado desde Telegram será exactamente el vídeo final aprobado.
- Prioridad a herramientas gratuitas y open source.
- No contratar servicios de pago sin autorización.

## Componentes previstos

- Twitch API
- GitHub Actions
- FFmpeg
- IA
- Telegram

## Estado

- [x] Repositorio GitHub creado
- [x] GitHub Actions probado
- [x] Twitch API
- [x] Detección automática de clips
- [x] Descarga de clips
- [x] Procesamiento de vídeo
- [x] Análisis mediante IA
- [x] Generación de metadatos
- [x] Sistema de aprobación
- [ ] Generación de hashtags optimizados
- [ ] Mensaje final de publicación en Telegram
- [ ] Identificación de hablantes
- [ ] Colores de subtítulos por hablante
- [ ] Prueba completa
