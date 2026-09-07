# Sistema de Procesamiento y Consulta de Documentos del DOF

## Índice
- [Introducción](#introducción)
- [Características principales](#características-principales)
- [Requisitos y dependencias](#requisitos-y-dependencias)
- [Instalación](#instalación)
- [Uso](#uso)
  - [Procesamiento de documentos](#procesamiento-de-documentos)
  - [Consulta de documentos](#consulta-de-documentos)
- [Estructura del código](#estructura-del-código)
  - [Configuración inicial](#configuración-inicial)
  - [Estructura de la base de datos](#estructura-de-la-base-de-datos)
  - [Procesamiento de texto](#procesamiento-de-texto)
  - [Generación de embeddings](#generación-de-embeddings)
  - [Almacenamiento en base de datos](#almacenamiento-en-base-de-datos)
- [Funcionamiento técnico](#funcionamiento-técnico)
  - [Detección de encabezados](#detección-de-encabezados)
  - [División de texto por páginas](#división-de-texto-por-páginas)
  - [Construcción de encabezados contextuales](#construcción-de-encabezados-contextuales)
  - [Algoritmo de encabezados jerárquicos](#algoritmo-de-encabezados-jerárquicos)
- [Sistema de consulta con Gemini](#sistema-de-consulta-con-gemini)
  - [Búsqueda vectorial](#búsqueda-vectorial)
  - [Contexto expandido](#contexto-expandido)
  - [Consulta a Gemini 2.0](#consulta-a-gemini-20)
  - [Modos de operación](#modos-de-operación)
- [Flujo de trabajo](#flujo-de-trabajo)
  - [Procesamiento de documentos](#procesamiento-de-documentos-1)
  - [Consulta de información](#consulta-de-información)
- [Versiones del sistema](#versiones-del-sistema)
  - [extract_embeddings_1_page.py](#extract_embeddings_1_pagepy)
  - [extract_embeddings_structured_headers.py](#extract_embeddings_structured_headerspy)
- [Limitaciones y consideraciones](#limitaciones-y-consideraciones)

## Introducción

Este sistema procesa documentos del Diario Oficial de la Federación (DOF) almacenados en formato Markdown. Su objetivo principal es extraer el contenido, detectar la estructura jerárquica de los documentos, dividir el texto en fragmentos basados en páginas y generar embeddings vectoriales para permitir búsquedas semánticas eficientes.

Los documentos procesados se almacenan en una base de datos SQLite optimizada para búsquedas vectoriales, permitiendo consultas por similitud semántica en el contenido del DOF.

El sistema también incluye un módulo de consulta que permite realizar búsquedas semánticas y obtener respuestas contextualizadas utilizando el modelo Gemini 2.0 de Google.

## Características principales

- Procesamiento de archivos Markdown del DOF
- Extracción inteligente de la estructura jerárquica mediante detección de encabezados
- Algoritmo de seguimiento de encabezados abiertos/activos para mantener el contexto
- División de texto en chunks basados en marcadores de página
- Generación de embeddings vectoriales usando SentenceTransformer
- Almacenamiento en base de datos SQLite con capacidades vectoriales mediante sqlite-vec
- Creación de encabezados contextuales para mejorar la búsqueda semántica
- Generación de archivos de depuración para verificar la segmentación del texto
- Búsqueda semántica mediante distancia euclidiana entre embeddings
- Obtención de contexto expandido (chunks adyacentes) para mejorar respuestas
- Consultas a Gemini 2.0 con instrucciones específicas para procesar documentos del DOF
- Modo interactivo para realizar consultas continuas
- Sistema de logging para seguimiento del procesamiento

## Requisitos y dependencias

El sistema depende de las siguientes bibliotecas y tecnologías:

- typer: para la interfaz de línea de comandos
- fastlite: para manipulación simplificada de bases de datos SQLite
- sqlite-vec: para habilitar capacidades vectoriales en SQLite
- sentence-transformers: para la generación de embeddings
- tokenizers: para tokenizar el texto
- tqdm: para mostrar barras de progreso
- google.generativeai: para integración con el modelo Gemini 2.0
- numpy: para procesamiento numérico
- python-dotenv: para cargar variables de entorno

## Instalación

1. Clona el repositorio o descarga los scripts
2. Instala las dependencias necesarias usando uv (instalador de paquetes más rápido y moderno):

```bash
# Instalar uv si no lo tienes
curl -sSf https://astral.sh/uv/install.sh | sh

# Instalar dependencias con uv
uv pip install typer fastlite sqlite-vec sentence-transformers tokenizers tqdm google-generativeai numpy python-dotenv
```

3. Configura una API key de Google Gemini en un archivo .env:

```
GOOGLE_API_KEY=tu_api_key_aquí
```

4. Asegúrate de tener una estructura de directorios adecuada para almacenar los archivos del DOF en formato Markdown

## Uso

### Procesamiento de documentos

Para procesar todos los archivos Markdown en un directorio específico, hay dos scripts disponibles con diferentes enfoques para el manejo de encabezados:

```bash
# Versión básica
python extract_embeddings_1_page.py /ruta/a/directorio/con/archivos/md

# Versión con manejo alternativo de encabezados
python extract_embeddings_structured_headers.py /ruta/a/directorio/con/archivos/md
```

Los scripts realizarán las siguientes acciones:
1. Procesarán cada archivo Markdown en el directorio
2. Extraerán la estructura jerárquica de los documentos
3. Dividirán el texto en chunks basados en marcadores de página
4. Generarán embeddings para cada chunk
5. Almacenarán todo en la base de datos SQLite
6. Crearán archivos de depuración con el nombre "nombre_archivo_chunks.txt" que muestran cómo se dividió el texto

## Estructura del código

### Configuración inicial

El script comienza inicializando los modelos y configuraciones necesarias:

- Carga del tokenizador y modelo de embeddings (nomic-ai/modernbert-embed-base)
- Configuración del sistema de logging para depuración y seguimiento
- Inicialización de la base de datos SQLite con extensiones vectoriales

### Estructura de la base de datos

La base de datos consta de dos tablas principales:

1. **documents**: Almacena metadatos de los documentos
   - id: Identificador único
   - title: Título del documento
   - url: URL al documento original en el DOF
   - file_path: Ruta al archivo local
   - created_at: Fecha y hora de procesamiento

2. **chunks**: Almacena los fragmentos de texto y sus embeddings
   - id: Identificador único
   - document_id: Relación con el documento original
   - text: Texto del fragmento
   - header: Encabezado contextual para mejorar la búsqueda
   - embedding: Vector de embeddings serializado
   - created_at: Fecha y hora de procesamiento

### Procesamiento de texto

El sistema implementa distintas funciones para procesar los documentos, que varían según la versión del script:

#### Funciones en extract_embeddings_1_page.py (versión básica)
- `split_text_by_page_break`: Divide el texto en secciones basadas en marcadores de página
- `extract_headings`: Extrae todos los encabezados presentes en el texto
- `build_chunk_header`: Construye encabezados contextuales para cada chunk con formato "Document: título | Section: encabezado1 > encabezado2 | Page: número"
- `get_url_from_filename`: Genera la URL del DOF a partir del nombre de archivo

#### Funciones en extract_embeddings_structured_headers.py (versión alternativa)
- `split_text_by_page_break`: Divide el texto en secciones basadas en marcadores de página (igual que en la versión básica)
- `get_heading_level`: Detecta el nivel (1-6) y texto de un encabezado markdown
- `update_open_headings`: Mantiene una lista actualizada de encabezados "abiertos" según la jerarquía del documento
- `build_header`: Construye encabezados que preservan la estructura jerárquica completa en formato Markdown
- `get_url_from_filename`: Genera la URL del DOF a partir del nombre de archivo (igual que en la versión básica)

### Generación de embeddings

Los embeddings se generan utilizando el modelo SentenceTransformer (nomic-ai/modernbert-embed-base). Para cada chunk, se construye un texto compuesto por el encabezado contextual y el contenido, y se codifica usando el modelo.

### Almacenamiento en base de datos

Los documentos y chunks procesados se almacenan en la base de datos SQLite, que ha sido extendida con capacidades vectoriales mediante sqlite-vec. Esto permite realizar búsquedas semánticas eficientes.

## Funcionamiento técnico

### Detección de encabezados

El sistema utiliza expresiones regulares para detectar encabezados en formato Markdown:
```python
HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.*)$')
```

Esta expresión identifica líneas que comienzan con entre 1 y 6 símbolos '#', seguidos de un espacio y texto, capturando tanto el nivel de encabezado como su contenido.

En el script `extract_embeddings_structured_headers.py`, el sistema implementa funciones adicionales para determinar con precisión la jerarquía de encabezados y su relación entre sí:

```python
def get_heading_level(line: str):
    """
    Returns the heading level and text,
    or (None, None) if the line is not a heading.
    """
    match = HEADING_PATTERN.match(line)
    if match:
        hashes = match.group(1)
        heading_text = match.group(2).strip()
        level = len(hashes)
        return level, heading_text
    return None, None
```

### División de texto por páginas

El algoritmo `split_text_by_page_break` es central en el sistema. Divide el texto en fragmentos basados en marcadores de página con el siguiente formato:

```
{número_página}-----------------------------------------------------
```

El sistema detecta estos marcadores y crea chunks separados para cada página, conservando el número de página para referencia. Esto permite procesar documentos del DOF manteniendo la estructura original de páginas, lo que facilita la referencia y citación.

### Construcción de encabezados contextuales

Hay dos enfoques implementados para la construcción de encabezados contextuales:

1. **Enfoque básico** (`extract_embeddings_1_page.py`):
   - Extrae todos los encabezados en el chunk actual
   - Hereda el último encabezado del chunk anterior
   - Construye un encabezado con formato "Document: título | Section: encabezado1 > encabezado2 | Page: número"
   - Ejemplo: "Document: 23012025-MAT | Section: Título Principal > Subtítulo | Page: 3"

2. **Enfoque alternativo** (`extract_embeddings_structured_headers.py`):
   - Mantiene un seguimiento de encabezados "abiertos" a lo largo del documento
   - Preserva la estructura jerárquica completa basada en los niveles de encabezado
   - Construye encabezados que mantienen el formato Markdown original
   - Implementa un tratamiento especial para el primer chunk vs. chunks subsecuentes
   - Ejemplo: 
     ```
     # Document: 23012025-MAT | page: 3
     ## Título Principal
     ### Subtítulo
     ```

Este segundo enfoque representa con mayor fidelidad la estructura jerárquica del documento, lo que mejora la calidad de los embeddings y la precisión de las búsquedas.

### Algoritmo de encabezados jerárquicos

El script `extract_embeddings_structured_headers.py` implementa un algoritmo para mantener una estructura jerárquica de encabezados "abiertos" a lo largo del documento:

```python
def update_open_headings(open_headings, line):
    """
    Updates the list of open headings according to the line.
    
    - If an H1 is found, the list is reset.
    - If the line is a heading of level >1:
        * If the list is empty, it is added.
        * If the last open heading has a lower or equal level,
          it is added without removing the previous one (to preserve siblings).
        * If the new heading is of a higher level (lower number)
          than the last one, those with a level lower than the new one
          are preserved and the heading is added.
    """
```

Este algoritmo sigue estas reglas:

1. Si se encuentra un encabezado H1, se reinicia la lista de encabezados abiertos
2. Si se encuentra un encabezado de nivel mayor a 1:
   - Si la lista está vacía, se agrega el encabezado
   - Si el último encabezado tiene un nivel menor o igual, se agrega el nuevo sin eliminar los anteriores
   - Si el nuevo encabezado es de un nivel superior, se conservan solo los encabezados de nivel superior y se agrega el nuevo

La implementación también diferencia el tratamiento para el primer chunk vs. los chunks subsecuentes:

- En el primer chunk, solo se incluye el primer encabezado detectado (si existe)
- En los demás chunks, se incluyen todos los encabezados abiertos en orden jerárquico

## Sistema de consulta con Gemini

El módulo `gemini_query.py` implementa un sistema de búsqueda semántica y consulta mediante Gemini 2.0 para documentos del Diario Oficial de la Federación (DOF).

### Búsqueda vectorial

El sistema utiliza embeddings vectoriales y la distancia euclidiana para encontrar los fragmentos más relevantes para una consulta:

```python
def find_relevant_chunks(query, all_chunks, top_k=10):
    # Generar embedding para la consulta
    query_embedding = model.encode(f"search_query: {query}")
    
    # Calcular distancias
    scored_results = []
    for chunk in all_chunks:
        chunk_embedding = deserialize_embedding(chunk["embedding_blob"])
        distance = np.linalg.norm(query_embedding - chunk_embedding)
        scored_results.append({
            # ... metadatos del chunk ...
            "distance": distance,
            "similarity": 1.0 / (1.0 + distance)
        })
    
    # Ordenar por menor distancia (mayor similitud)
    return sorted(scored_results, key=lambda x: x["distance"])[:top_k]
```

Esta función:
1. Convierte la consulta de texto a un vector de embeddings usando el mismo modelo que en el procesamiento
2. Calcula la distancia euclidiana entre la consulta y cada chunk de la base de datos
3. Ordena los resultados por relevancia (menor distancia)
4. Devuelve los `top_k` resultados más relevantes

### Contexto expandido

Para mejorar la calidad de las respuestas, el sistema obtiene un contexto expandido incluyendo chunks adyacentes al más relevante:

```python
def get_extended_context(best_chunk, all_chunks):
    # Filtrar chunks del mismo documento
    same_doc_chunks = [c for c in all_chunks if c["document_id"] == best_chunk["document_id"]]
    
    # ... encontrar posición del mejor chunk ...
    
    # Construir contexto extendido con chunk anterior + mejor chunk + chunk siguiente
    context = ""
    if best_index > 0:
        context += same_doc_chunks[best_index - 1]["chunk_text"] + "\n\n"
    context += best_chunk["chunk_text"] + "\n\n"
    if best_index < len(same_doc_chunks) - 1:
        context += same_doc_chunks[best_index + 1]["chunk_text"]
```

Esta estrategia:
1. Identifica todos los chunks del mismo documento que el chunk más relevante
2. Determina la posición del chunk más relevante en la secuencia original
3. Construye un contexto que incluye el chunk anterior, el chunk más relevante y el chunk siguiente

### Consulta a Gemini 2.0

El sistema utiliza el modelo Gemini 2.0 de Google para generar respuestas contextualizadas:

```python
# Construir prompt para Gemini
prompt = (
    f"Utilizando el siguiente contexto extraído de un documento del Diario Oficial de la Federación:\n\n"
    f"---\n{extended_context}\n---\n\n"
    f"Instrucciones:\n"
    # ... instrucciones específicas ...
    f"Pregunta:\n{query}"
)

# Generar respuesta con Gemini
model_gemini = genai.GenerativeModel('gemini-2.0-flash')
response = model_gemini.generate_content(prompt)
```

El prompt incluye:
1. El contexto expandido extraído de los documentos
2. Instrucciones específicas para el modelo sobre cómo debe responder
3. La consulta original del usuario

### Modos de operación

El sistema ofrece dos modos de operación:

1. **Consulta directa**: Realiza una única consulta y muestra el resultado
   ```bash
   python gemini_query.py --query "tu consulta aquí"
   ```

2. **Modo interactivo**: Permite realizar múltiples consultas en una sesión
   ```bash
   python gemini_query.py --interactive
   ```

En el modo interactivo, el sistema mostrará un prompt para ingresar consultas y continuará hasta que el usuario escriba 'salir', 'exit' o 'quit'.

## Flujo de trabajo

### Procesamiento de documentos

El flujo específico depende de la versión del script utilizado:

#### Versión básica (extract_embeddings_1_page.py):
1. Por cada archivo Markdown en el directorio especificado:
   - Se extraen los metadatos del documento
   - Se elimina cualquier versión anterior del documento en la base de datos
   - Se inserta el nuevo documento en la tabla 'documents'
   - Se verifica si el documento contiene marcadores de página
   - Si encuentra marcadores, divide el texto por páginas; sino, trata todo el contenido como una sola página
   - Por cada página:
     - Se extraen los encabezados presentes en el chunk actual
     - Se hereda el último encabezado del chunk anterior (si existe)
     - Se construye el encabezado contextual con formato "Document: título | Section: encabezado1 > encabezado2 | Page: número"
     - Se genera el embedding combinando el encabezado y el contenido
     - Se guarda en la base de datos y en un archivo de depuración

#### Versión alternativa (extract_embeddings_structured_headers.py):
1. Por cada archivo Markdown en el directorio especificado:
   - Se extraen los metadatos del documento
   - Se elimina cualquier versión anterior del documento en la base de datos
   - Se inserta el nuevo documento en la tabla 'documents'
   - Se verifica si el documento contiene marcadores de página
   - Si encuentra marcadores, divide el texto por páginas; sino, trata todo el contenido como una sola página
   - Se inicializa una lista vacía de encabezados "abiertos"
   - Por cada página:
     - Si es el primer chunk, se realiza una pre-lectura para encontrar el primer encabezado
     - Se construye el encabezado contextual preservando la estructura jerárquica de los encabezados abiertos
     - Se genera el embedding combinando el encabezado y el contenido
     - Se guarda en la base de datos y en un archivo de depuración
     - Se actualiza la lista de encabezados abiertos procesando cada línea del chunk

### Consulta de información

1. El usuario realiza una consulta en lenguaje natural
2. El sistema obtiene todos los chunks almacenados en la base de datos
3. La consulta se convierte en un vector de embeddings
4. Se calcula la similitud entre la consulta y todos los chunks
5. Se selecciona el chunk más relevante y se obtiene contexto expandido (chunks adyacentes)
6. Se construye un prompt para Gemini 2.0 con el contexto y la consulta
7. Gemini 2.0 genera una respuesta basada en el contexto
8. Se muestra la respuesta junto con metadatos del documento fuente

## Versiones del sistema

El sistema cuenta con dos versiones de scripts para el procesamiento de documentos, cada uno con un enfoque diferente para la gestión de encabezados y contexto:

### extract_embeddings_1_page.py

Este es el script original con las siguientes características:
- Usa un enfoque simple para los encabezados, extrayéndolos del chunk actual
- Implementa una herencia básica del último encabezado del chunk anterior
- Construye encabezados con formato "Document: título | Section: encabezado1 > encabezado2 | Page: número"
- Contiene más registros de depuración

#### Ejemplo de encabezado generado:
```
Header: Document: 23012025-MAT | Section: Título Principal > Subtítulo | Page: 3
```

### extract_embeddings_structured_headers.py

Este script implementa mejoras en el procesamiento de encabezados:
- Implementa un algoritmo de "encabezados abiertos"
- Mantiene un seguimiento de la estructura jerárquica completa de encabezados
- Implementa reglas específicas para la gestión de encabezados H1 (reinicia la jerarquía)
- Preserva el formato Markdown original en los encabezados
- Diferencia el tratamiento para el primer chunk vs. chunks subsecuentes

#### Ejemplo de encabezado generado:
```
# Document: 23012025-MAT | page: 3
## Título Principal
### Subtítulo
```

Esta versión alternativa representa con mayor fidelidad la estructura jerárquica del documento, mejorando la calidad de los embeddings y la precisión de las búsquedas semánticas.

## Limitaciones y consideraciones

- El sistema depende de la correcta identificación de marcadores de página en formato {número}-----
- Si no se encuentran marcadores de página, todo el documento se procesa como una sola página
- El nombre de archivo debe seguir un formato específico (DDMMYYYY-XXX.md) para generar correctamente las URLs
- La calidad de las respuestas depende tanto de la precisión de la búsqueda vectorial como del modelo Gemini
- Requiere una API key válida de Google para utilizar Gemini 2.0
- La visualización de resultados está optimizada para terminal con formato de texto
- El rendimiento puede verse afectado cuando la base de datos contiene muchos documentos