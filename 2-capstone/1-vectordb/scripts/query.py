from typing import List, Tuple
from langchain.vectorstores.pgvector import PGVector
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings


def print_separator() -> None:
    """
    Prints a separator line to the console to visually separate content blocks.
    """
    print("-" * 80)


def print_doc(doc: str, score: float) -> None:
    """
    Formats and prints a document and its similarity score.

    Args:
        doc (str): The content of the document.
        score (float): The similarity score associated with the document.
    """
    print(f"Score: {score:.2f}\n{doc}\n")


def make_query(query: str, top_k: int) -> None:
    """
    Perform a similarity search in the database for the given query and prints the top_k similar entries.

    Args:
        query (str): The query string to search for similar content in the database.
        top_k (int): The number of similar entries to retrieve and display.
    """
    embedding_function = SentenceTransformerEmbeddings(
        model_name="BAAI/bge-large-en-v1.5",
        model_kwargs={"device": "cuda"},
        encode_kwargs={"normalize_embeddings": True},
    )

    CONNECTION_STRING = PGVector.connection_string_from_db_params(
        driver="psycopg2",
        host="localhost",
        port="5432",
        database="postgres",
        user="username",
        password="password",
    )

    db = PGVector(
        connection_string=CONNECTION_STRING,
        collection_name="embeddings",
        embedding_function=embedding_function,
    )

    docs_with_scores: List[Tuple[str, float]] = db.similarity_search_with_score(
        query, k=top_k
    )

    for doc, score in docs_with_scores:
        print_separator()
        print_doc(doc=doc.page_content, score=score)
        print_separator()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Search for similar text entries in a PostgreSQL database."
    )
    parser.add_argument(
        "--query", type=str, required=True, help="Query string to search for."
    )
    parser.add_argument(
        "--top_k", type=int, default=2, help="Number of top similar entries to return."
    )

    args = parser.parse_args()

    make_query(query=args.query, top_k=args.top_k)
