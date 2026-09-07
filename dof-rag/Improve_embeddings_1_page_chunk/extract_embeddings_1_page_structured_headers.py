import os
import re
from datetime import datetime
import logging

import typer
from fastlite import database
from sqlite_vec import load
from sentence_transformers import SentenceTransformer
from tokenizers import Tokenizer
from dotenv import load_dotenv

# -----------------------------------------------------
# Logging system configuration
# -----------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dof_processing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dof_embeddings")

# -----------------------------------------------------
# Models and tokenizers
# -----------------------------------------------------
tokenizer = Tokenizer.from_pretrained("nomic-ai/modernbert-embed-base")
model = SentenceTransformer("nomic-ai/modernbert-embed-base", trust_remote_code=True)

# -----------------------------------------------------
# Initialize DB with fastlite + sqlite_vec
# -----------------------------------------------------
db = database("dof_db/db.sqlite")
db.conn.enable_load_extension(True)
load(db.conn)
db.conn.enable_load_extension(False)

# -----------------------------------------------------
# Table definitions (schema)
# -----------------------------------------------------
db.t.documents.create(
    id=int,
    title=str,
    url=str,
    file_path=str,
    created_at=datetime,
    pk="id",
    ignore=True
)
db.t.documents.create_index(["url"], unique=True, if_not_exists=True)

db.t.chunks.create(
    id=int,
    document_id=int,
    text=str,
    header=str,
    embedding=bytes,
    created_at=datetime,
    pk="id",
    foreign_keys=[("document_id", "documents")],
    ignore=True,
)

# -----------------------------------------------------
# Header pattern (Markdown)
# -----------------------------------------------------
HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.*)$')

# -----------------------------------------------------
# Helper functions
# -----------------------------------------------------
def split_text_by_page_break(text: str):
    """
    Splits the text into chunks based on the page pattern:
    {number} followed by at least 5 hyphens.
    """
    page_pattern = re.compile(r'\{(\d+)\}\s*-{5,}')
    chunks = []
    last_index = 0
    last_page = None

    for match in page_pattern.finditer(text):
        page_num = match.group(1)
        chunk_text = text[last_index:match.start()].strip()
        if chunk_text:
            chunks.append({"text": chunk_text, "page": page_num})
        last_index = match.end()
        last_page = page_num

    # Last fragment after the last page mark
    remaining = text[last_index:].strip()
    if remaining:
        final_page = last_page if last_page else "1"
        chunks.append({"text": remaining, "page": final_page})

    return chunks

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
    lvl, txt = get_heading_level(line)
    if lvl is None:
        # Line without heading, state is not modified
        return open_headings

    if lvl == 1:
        # An H1 closes all previous context.
        return [(1, txt)]
    else:
        if not open_headings:
            return [(lvl, txt)]
        else:
            # If the last heading has a lower or equal level, the current one is added.
            if open_headings[-1][0] <= lvl:
                open_headings.append((lvl, txt))
            else:
                # If the new heading is of a higher level (more important)
                # only headings that are of a lower level (higher) than the new one are preserved.
                new_chain = [item for item in open_headings if item[0] < lvl]
                new_chain.append((lvl, txt))
                open_headings = new_chain
        return open_headings

def build_header(doc_title: str, page: str, open_headings: list, chunk_number: int):
    """
    Builds the chunk header with the format:
    
    # Document: <Document Name> | page: <Page Number>
    
    Additionally, in chunk #1 the first detected heading is added (if it exists),
    while in other chunks all open headings are listed in order.
    """
    header_lines = [f"# Document: {doc_title} | page: {page}"]

    if chunk_number == 1:
        if open_headings:
            # For the first chunk, only the first detected heading is included.
            top_level, top_text = open_headings[0]
            hashes = "#" * top_level
            header_lines.append(f"{hashes} {top_text}")
    else:
        for (lvl, txt) in open_headings:
            hashes = "#" * lvl
            header_lines.append(f"{hashes} {txt}")

    return "\n".join(header_lines)

def get_url_from_filename(filename: str) -> str:
    """
    Generates the URL based on the pattern: DDMMYYYY-XXX.md
    """
    base_filename = os.path.basename(filename).replace(".md", "")
    if len(base_filename) >= 8:
        year = base_filename[4:8]
        pdf_filename = f"{base_filename}.pdf"
        url = f"https://diariooficial.gob.mx/abrirPDF.php?archivo={pdf_filename}&anio={year}&repo=repositorio/"
        return url
    else:
        raise ValueError(f"Expected filename like 23012025-MAT.md but got {filename}")

def process_file(file_path: str):
    """
    Processes a Markdown file:
      1. Divides the content into chunks based on page breaks.
      2. Establishes and updates the state of "open" headings.
      3. Generates the embedding and saves the information in the database.
      4. Writes a _chunks.txt file with the details of each chunk.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    title = os.path.splitext(os.path.basename(file_path))[0]
    url = get_url_from_filename(file_path)
    logger.debug(f"Processing file '{file_path}' with title '{title}'")

    db.t.documents.delete_where("url = ?", [url])
    doc = db.t.documents.insert(
        title=title,
        url=url,
        file_path=file_path,
        created_at=datetime.now()
    )

    # Divide the content into chunks based on page breaks
    if re.search(r'\{\d+\}\s*-{5,}', content):
        page_chunks = split_text_by_page_break(content)
    else:
        page_chunks = [{"text": content, "page": "1"}]

    chunks_file_path = os.path.splitext(file_path)[0] + "_chunks.txt"
    open_headings = []  # List of (level, text) that are "open"
    chunk_counter = 0

    with open(chunks_file_path, "w", encoding="utf-8") as chunks_file:
        for chunk in page_chunks:
            chunk_counter += 1
            chunk_text = chunk["text"]
            page_number = chunk["page"]

            # For the first chunk, pre-read the lines until the first heading is obtained.
            if chunk_counter == 1:
                lines = chunk_text.splitlines()
                initial_headings = []
                for line in lines:
                    lvl, txt = get_heading_level(line)
                    if lvl is not None:
                        initial_headings.append((lvl, txt))
                        # If the first heading is H1, we stop the pre-reading.
                        if lvl == 1:
                            break
                    else:
                        # Stop if the first line that is not a heading is found.
                        break
                if initial_headings:
                    open_headings = initial_headings.copy()

            # Build the header using the "open" headings at the beginning of the chunk.
            header = build_header(title, page_number, open_headings, chunk_counter)

            # Prepare text to generate the embedding.
            text_for_embedding = f"{header}\n\n{chunk_text}"
            embedding = model.encode(f"search_document: {text_for_embedding}")

            # Write the chunk details to the _chunks.txt file.
            chunks_file.write(f"--- CHUNK #{chunk_counter} ---\n")
            chunks_file.write(f"Header:\n{header}\n\n")
            chunks_file.write(f"Text:\n{chunk_text}\n")
            chunks_file.write("\n" + "-"*50 + "\n\n")

            # Save the chunk in the database.
            db.t.chunks.insert(
                document_id=doc["id"],
                text=chunk_text,
                header=header,
                embedding=embedding,
                created_at=datetime.now(),
            )

            # Update the state of open headings for the following chunks.
            lines = chunk_text.splitlines()
            for line in lines:
                open_headings = update_open_headings(open_headings, line)

    logger.info(f"Processing completed for: {file_path}")
    logger.info(f"Chunks file generated at: {chunks_file_path}")

def main(directory: str):
    """
    Processes all .md files in a directory applying the open headings logic
    and saving the information in SQLite.
    """
    md_files = [f for f in os.listdir(directory) if f.endswith(".md")]
    for f in md_files:
        file_path = os.path.join(directory, f)
        process_file(file_path)

if __name__ == "__main__":
    typer.run(main)
