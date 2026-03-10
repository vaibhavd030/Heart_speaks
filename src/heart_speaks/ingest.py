import glob
import hashlib
import os
import re

import pypdf
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from heart_speaks.config import settings


import datetime

def parse_whisper_filename(filename: str) -> tuple[str, str]:
    """Extracts Date and Author from the new structured dataset filenames.
    Format: Day_Month_Date_Year_Hour_Min_AMPM_Author.pdf
    Example: Friday_February_1_1991_7_16_AM_Babuji Maharaj.pdf
    
    Returns:
        tuple[str, str]: (Formatted Date YYYY-MM-DD, Author Name)
    """
    clean_name = os.path.basename(filename).replace(".pdf", "")
    parts = clean_name.split("_")
    
    if len(parts) < 8:
        return "Unknown", "Spiritual Guide"
        
    # parts Example: ['Friday', 'February', '1', '1991', '7', '16', 'AM', 'Babuji Maharaj']
    month_str = parts[1]
    day_str = parts[2]
    year_str = parts[3]
    author = parts[7]
    
    try:
        # Convert to strict YYYY-MM-DD
        date_obj = datetime.datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y")
        formatted_date = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        formatted_date = f"{year_str}-{month_str}-{day_str}"
        
    return formatted_date, author

def get_vector_store() -> Chroma:
    """Returns the initialized Chroma VectorStore interface.
    
    Returns:
        Chroma: The instantiated Chroma vector store.
    """
    from pydantic import SecretStr
    embeddings = OpenAIEmbeddings(
        api_key=SecretStr(settings.openai_api_key),
        model="text-embedding-3-large"
    )
    return Chroma(
        collection_name="heart_speaks_collection",
        embedding_function=embeddings,
        persist_directory=str(settings.chroma_persist_dir),
    )

def ingest_data(data_path: str = settings.data_dir) -> Chroma:
    """Load PDFs, split them into chunks, and ingest into ChromaDB.
    
    Args:
        data_path (str): The directory containing the source PDF documents.
        
    Returns:
        Chroma: The populated vector store.
    """
    logger.info(f"Starting ingestion process from {data_path}")
    
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        logger.warning(f"Data directory {data_path} created. Please add PDFs.")
        return get_vector_store()
    
    logger.info("Loading documents...")
    docs = []
    pdf_files = glob.glob(os.path.join(data_path, "**/*.pdf"), recursive=True)
    
    for pdf_file in pdf_files:
        try:
            loader = PyPDFLoader(pdf_file)
            docs.extend(loader.load())
        except Exception as e:
            logger.error(f"Failed to load {pdf_file}: {e}")
    
    if not docs:
        logger.warning("No documents found in the directory.")
        return get_vector_store()
        
    logger.info(f"Loaded {len(docs)} document pages.")
    
    # Enrich metadata and group full text for repository
    from heart_speaks.repository import init_db, upsert_message
    init_db()
    
    docs_by_file = {}
    for doc in docs:
        source = doc.metadata.get("source", "Unknown")
        # Store relative path so FastAPI StaticFiles can find files in nested directories
        filename = os.path.relpath(source, data_path) if source != "Unknown" else "Unknown"
        date, author = parse_whisper_filename(filename)
        
        doc.metadata["date"] = date
        doc.metadata["author"] = author
        doc.metadata["source_file"] = filename
        doc.metadata["personality"] = docs_by_file.get(filename, {}).get("author", "Unknown") if docs_by_file else author
        
        if filename not in docs_by_file:
            docs_by_file[filename] = {"text": "", "pages": 0, "date": date, "author": author}
        docs_by_file[filename]["text"] = str(docs_by_file[filename]["text"]) + str(doc.page_content) + "\n\n"
        docs_by_file[filename]["pages"] = int(docs_by_file[filename]["pages"]) + 1 # type: ignore
        
    # Insert full texts into repository
    logger.info("Upserting full messages into SQLite repository...")
    for filename, data in docs_by_file.items():
        full_text_str = str(data["text"]).strip()
        
        # Smart Author Extraction: Look at the last 500 characters for known author names
        # OCR might be messy, so we use a regex search
        author = str(data["author"])
        if author == "Spiritual Guide" or author == "Unknown":
            tail_text = full_text_str[-500:].lower()
            if re.search(r'babuji\s*maharaj|babuji', tail_text):
                author = "Babuji Maharaj"
            elif re.search(r'chariji|parthasarathi\s*rajagopalachari', tail_text):
                author = "Chariji"
            elif re.search(r'daaji|kamlesh\s*patel', tail_text):
                author = "Daaji"
            elif re.search(r'lalaji|ram\s*chandra\s*of\s*fatehgarh', tail_text):
                author = "Lalaji"
            else:
                author = "Spiritual Guide"
        
        upsert_message(
            source_file=filename,
            full_text=full_text_str,
            author=author,
            date=str(data["date"]),
            page_count=int(data["pages"]) # type: ignore
        )
        
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    
    logger.info("Splitting documents into chunks...")
    splits = text_splitter.split_documents(docs)
    logger.info(f"Created {len(splits)} chunks.")
    
    vectorstore = get_vector_store()
    
    logger.info("Adding chunks to ChromaDB...")
    # Add in batches to avoid overwhelming
    batch_size = 100
    for i in range(0, len(splits), batch_size):
        batch = splits[i:i + batch_size]
        ids = [
            hashlib.md5(f"{doc.metadata.get('source_file', 'unknown')}:{doc.page_content}".encode()).hexdigest()
            for doc in batch
        ]
        vectorstore.add_documents(batch, ids=ids)
        logger.info(f"Added batch {int(i/batch_size) + 1} of {(len(splits) + batch_size - 1) // batch_size}")
        
    logger.info("Ingestion complete.")
    return vectorstore

if __name__ == "__main__":
    logger.add("logs/app.log", level=settings.log_level, rotation="10 MB")
    ingest_data()
