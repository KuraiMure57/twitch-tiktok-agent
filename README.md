# Twitch TikTok Agent

Agente automático para transformar clips de Twitch en contenido para TikTok.

## Objetivo

Flujo previsto:

Twitch
→ detectar nuevo clip
→ obtener vídeo
→ analizar contenido
→ decidir si merece la pena
→ editar vídeo
→ formato 9:16
→ subtítulos
→ generar título
→ generar descripción
→ generar hashtags
→ revisión del usuario
→ aprobación
→ publicación en TikTok

## Principios

- El PC del usuario no necesita estar encendido.
- El agente no tendrá acceso a archivos personales del usuario.
- Ningún vídeo se publicará sin aprobación explícita.
- Prioridad a herramientas gratuitas y open source.
- No contratar servicios de pago sin autorización.
- El vídeo aprobado debe ser exactamente el vídeo publicado.

## Componentes previstos

- Twitch API
- GitHub Actions
- FFmpeg
- IA
- Telegram
- TikTok API

## Estado

- [x] Repositorio GitHub creado
- [x] GitHub Actions probado
- [ ] Twitch API
- [ ] Detección automática de clips
- [ ] Descarga de clips
- [ ] Procesamiento de vídeo
- [ ] Análisis mediante IA
- [ ] Generación de metadatos
- [ ] Sistema de aprobación
- [ ] Integración con TikTok
- [ ] Prueba completa
