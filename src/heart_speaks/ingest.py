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


def extract_datetime_from_filename(filename: str) -> str:
    """Extracts date/time from common patterns in filename if possible.
    
    Args:
        filename (str): The name of the file to parse.
        
    Returns:
        str: The extracted date string (YYYY-MM-DD) or 'Unknown'.
    """
    # This is a naive implementation; depending on the exact format, you might want to adjust regex
    match = re.search(r'\d{4}-\d{2}-\d{2}', filename)
    if match:
        return match.group(0)
    return "Unknown"

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
        except (OSError, ValueError, pypdf.errors.PyPdfError) as e:
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
        filename = os.path.basename(source)
        date = extract_datetime_from_filename(filename)
        
        doc.metadata["date"] = date
        doc.metadata["source_file"] = filename
        
        if filename not in docs_by_file:
            docs_by_file[filename] = {"text": "", "pages": 0, "date": date}
        docs_by_file[filename]["text"] = str(docs_by_file[filename]["text"]) + str(doc.page_content) + "\n\n"
        docs_by_file[filename]["pages"] = int(docs_by_file[filename]["pages"]) + 1 # type: ignore
        
    # Insert full texts into repository
    logger.info("Upserting full messages into SQLite repository...")
    for filename, data in docs_by_file.items():
        full_text_str = str(data["text"])
        
        # Extract author signature from the last non-empty line
        author = "Spiritual Guide"
        lines = [line.strip() for line in full_text_str.split('\n') if line.strip()]
        if lines:
            extracted = lines[-1]
            if len(extracted) < 50:  # Safety check to avoid treating long paragraphs as a signature
                author = extracted

        # Extrapolate generic author hint based on filename as a fallback
        if author == "Spiritual Guide":
            if "babuji" in filename.lower(): 
                author = "Babuji"
            elif "chariji" in filename.lower(): 
                author = "Chariji"
            elif "daaji" in filename.lower(): 
                author = "Daaji"
            
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
