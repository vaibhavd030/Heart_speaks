import os
import re
import glob
import hashlib
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
    embeddings = OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model="text-embedding-3-large"
    )
    return Chroma(
        collection_name="heart_speaks_collection",
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
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
    
    # Enrich metadata
    for doc in docs:
        source = doc.metadata.get("source", "Unknown")
        filename = os.path.basename(source)
        doc.metadata["date"] = extract_datetime_from_filename(filename)
        doc.metadata["source_file"] = filename
        
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
            hashlib.md5(f"{doc.metadata.get('source_file', 'unknown')}:{doc.page_content}".encode("utf-8")).hexdigest()
            for doc in batch
        ]
        vectorstore.add_documents(batch, ids=ids)
        logger.info(f"Added batch {int(i/batch_size) + 1} of {(len(splits) + batch_size - 1) // batch_size}")
        
    logger.info("Ingestion complete.")
    return vectorstore

if __name__ == "__main__":
    logger.add("logs/app.log", level=settings.log_level, rotation="10 MB")
    ingest_data()
