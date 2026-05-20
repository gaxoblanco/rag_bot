# Lineup — Proyecto personal
## Categoría: proyecto_detalle
## Período: Junio 2024

## Resumen
Plataforma que lee un póster de festival y genera automáticamente una playlist
en Spotify con el top 10 de cada artista. OCR especializado en texto tipográfico,
Spotify API, Python, Docker, Angular. Pipeline end-to-end sin input manual.
Sistema de corrección para nombres de bandas — redujo errores un 80%.
Disponible públicamente en GitHub.

---

## El origen

Compré entradas para el Lollapalooza antes de que publicaran el line-up del año.
Me considero un neófito en música popular — no conocía la mayoría de los artistas
que suelen tocar en ese tipo de festivales.

Quería escuchar a los artistas antes de ir para saber a cuáles me interesaba
ver en vivo. Pero también quería aprender a trabajar con modelos de IA de verdad —
no llamar a una API y recibir una respuesta, sino entender qué hay adentro y
tomar decisiones técnicas reales sobre los modelos.

El proyecto nació de las dos necesidades al mismo tiempo.

---

## La idea

Cuando saliera el póster del line-up, un software procesaría la imagen,
extraería los nombres de todos los artistas, y generaría automáticamente
una playlist en Spotify con el top 10 de cada uno.

De ese modo, antes de ir al festival, podría escuchar los mejores temas
de cada artista y decidir a cuáles priorizar.

---

## La decisión técnica más importante: modelo de imagen vs OCR

La primera aproximación fue usar un modelo de visión para extraer el texto
del póster. El problema: el modelo pesaba más de 8 GB de memoria de video —
la notebook no tenía capacidad para correrlo, y en producción el costo
de cómputo no escalaría bien.

Ahí apareció el OCR. Ya había trabajado con OCR en That Day in London,
así que sabía que era viable. Perdí la potencia de un modelo de visión general,
pero gané en eficiencia, costo y velocidad.

La decisión fue elegir un modelo OCR especializado en texto tipográfico
en lugar de un modelo de imagen general — mayor precisión en layouts
tipográficos con una fracción del cómputo.

---

## El mayor reto técnico: generalizar el reconocimiento de bandas

El desafío no fue extraer texto — fue hacerlo genérico para procesar
diferentes imágenes de line-up y reconocer los nombres de bandas correctamente.

Los pósters de festivales tienen tipografías variadas, tamaños distintos
por popularidad del artista, y nombres de bandas con múltiples palabras
que el OCR a veces fragmentaba mal.

Se implementó un sistema de corrección específico para nombres de bandas
con más de tres palabras. Eso redujo el nivel de errores en el reconocimiento
de bandas en un **80%**.

Con más memoria de cómputo el problema se resuelve usando el modelo de visión
original — pero implica más costo. La solución actual es eficiente dentro
de las restricciones reales del proyecto.

---

## Stack

- Python — pipeline completo
- OCR especializado en texto tipográfico
- Spotify API — búsqueda de artistas y generación de playlist
- Docker — entorno reproducible
- Angular Standalone Components — front-end responsive
- Arquitectura de microservicios con Circuit Breaker y Retry patterns
- Semáforos para procesamiento en background — mejora de throughput del 40%

---

## Resultado

El proyecto funcionó: generó playlists reales con los artistas del Lollapalooza
y permitió descubrir muchas bandas nuevas antes del festival.

Está disponible públicamente en el repositorio de GitHub de Gastón.

---

## Lo que dejó este proyecto

- Primera experiencia tomando decisiones reales sobre modelos — no solo usarlos
- Entender el trade-off entre potencia de modelo y costo de cómputo
- Criterio para elegir herramientas específicas sobre herramientas generales
  cuando las restricciones de hardware o costo lo justifican