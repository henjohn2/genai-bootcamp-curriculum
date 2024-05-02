import glob
from typing import List

from langchain_core.documents import Document
from langchain.document_loaders import TextLoader, PyPDFLoader
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores.pgvector import PGVector


def chunk_document(doc_path: str) -> List[Document]:
    """Chunk a document into smaller Langchain Documents suitable for embedding.

    This function reads a PDF document from the specified path, loads it, and then chunks
    it into smaller pieces based on character count, maintaining a specified overlap between chunks.

    Args:
        doc_path (str): The path to the document file.

    Returns:
        List[Document]: A list of Document objects, each representing a chunk of the original document.
    """
    loader = PyPDFLoader(doc_path)
    documents = loader.load()

    # Split the document based on the character count with an overlap.
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_documents(documents)


def connection_string() -> str:
    """Generate a connection string for the PGVector database.

    Uses predefined database parameters to create a connection string for use with PGVector.

    Returns:
        str: A connection string for PGVector.
    """
    return PGVector.connection_string_from_db_params(
        driver="psycopg2",
        host="localhost",
        port="5432",
        database="postgres",
        user="username",
        password="password",
    )


def embed_documents(doc_dir: str, add_docs: bool = False):
    """Process and embed document chunks into a PGVector database.

    This function processes all PDF documents in a specified directory, chunks each document,
    and either creates a new collection of embeddings in the database or adds to an existing collection.

    Args:
        doc_dir (str): Directory containing PDF documents to process.
        add_docs (bool, optional): Flag to add to an existing collection instead of creating a new one. Defaults to False.
    """
    doc_chunks = []
    for doc in glob.glob(f"{doc_dir}/*.pdf"):
        doc_chunks += chunk_document(doc)

    # Configure the embedding function.
    embedding_function = SentenceTransformerEmbeddings(
        model_name="BAAI/bge-large-en-v1.5",
        model_kwargs={"device": "cuda"},
        encode_kwargs={"normalize_embeddings": True},
    )

    if not add_docs:
        # Create a new database collection and populate with embeddings.
        db = PGVector.from_documents(
            doc_chunks,
            connection_string=connection_string(),
            collection_name="embeddings",
            embedding=embedding_function,
            pre_delete_collection=True,
        )
        print(f"Created new database with {len(doc_chunks)} embeddings.")
    else:
        # Add new embeddings to an existing collection.
        db = PGVector(
            connection_string=connection_string(),
            collection_name="embeddings",
            embedding=embedding_function,
        )
        res = db.add_documents(doc_chunks)
        print(f"Added {len(res)} embeddings.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Embed PDF documents into a PGVector database."
    )
    parser.add_argument(
        "--doc_dir",
        type=str,
        required=True,
        help="Path to the directory containing PDF documents.",
    )
    parser.add_argument(
        "--add",
        action="store_true",
        help="Flag to add embeddings to an existing database collection.",
    )

    args = parser.parse_args()

    embed_documents(args.doc_dir, args.add)
