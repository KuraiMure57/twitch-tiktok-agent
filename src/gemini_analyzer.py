prompt = f"""
Analiza este clip de vídeo de Twitch junto con la transcripción.

La transcripción procede de Whisper y puede contener errores.

Tu tarea es corregir la transcripción teniendo en cuenta:
- el audio;
- lo que ocurre visualmente en el vídeo;
- la intención del hablante;
- el tono y la emoción;
- el contexto proporcionado.

IMPORTANTE:

Una frase puede estar gramaticalmente formulada como una pregunta,
pero ser realmente una reacción de sorpresa o incredulidad.

Debes representar correctamente la intención emocional mediante la
puntuación, sin cambiar las palabras que realmente se pronuncian.

Por ejemplo:

"En serio?"

si se pronuncia como una reacción de sorpresa puede convertirse en:

"¡¿EN SERIO?!"

No debes convertir automáticamente todas las preguntas en exclamaciones.
Utiliza el vídeo y el contexto para decidirlo.

Reglas:

1. Comprende qué ocurre visualmente en el vídeo.
2. Utiliza el audio y la transcripción.
3. Corrige errores evidentes de transcripción.
4. Corrige puntuación.
5. Corrige mayúsculas y minúsculas cuando sea necesario.
6. Interpreta correctamente sorpresa, emoción, incredulidad,
   enfado, alegría u otras reacciones cuando sean evidentes.
7. Mantén exactamente los timestamps originales.
8. No inventes palabras.
9. No elimines segmentos.
10. Mantén el idioma original.
11. Devuelve únicamente JSON válido.

Información proporcionada:

{json.dumps(ai_input, ensure_ascii=False, indent=2)}

Analiza primero el vídeo y después decide la corrección.
"""
