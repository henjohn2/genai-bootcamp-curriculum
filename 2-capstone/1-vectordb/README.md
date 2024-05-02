

# README for Document Embeddings and Vector DB Pipeline

This README provides an overview of the document embedding and vector database pipeline as implemented in the Jupyter notebook `Document Embeddings and Vector DB.ipynb`. The pipeline is designed to process PDF documents, extract and chunk text, embed the text into a high-dimensional vector space, and store these embeddings in a PGVector database for similarity searching. Below are the key components and steps involved in the pipeline.

## Pipeline Overview

The pipeline consists of the following main steps:

1. **Document Loading**: PDF documents are loaded from a specified directory.
2. **Document Chunking**: Each document is split into manageable chunks based on character count, with an overlap to maintain context.
3. **Embedding Generation**: Text chunks are converted into vector embeddings using a pre-trained language model.
4. **Database Setup**: A PGVector database is set up to store and index these embeddings.
5. **Embedding Storage**: Embeddings are stored in the database, either by creating a new collection or adding to an existing one.
6. **Similarity Searching**: The pipeline includes functionality to query the database to find documents similar to a given text query.

## Detailed Steps

### Step 1: Document Loading

Documents are loaded using the `PyPDFLoader` class, which reads PDF files and extracts text content.

### Step 2: Document Chunking

The `CharacterTextSplitter` class is used to divide the document text into smaller chunks. Each chunk is approximately 1000 characters long with a 100-character overlap between consecutive chunks.

### Step 3: Embedding Generation

The `SentenceTransformerEmbeddings` class utilizes a pre-trained transformer model (BAAI/bge-large-en-v1.5) to generate embeddings. The model is run on a CUDA-enabled device, ensuring that embeddings are normalized.

### Step 4: Database Setup

Connection parameters for the PGVector database are set, including the host, port, database name, user, and password.

### Step 5: Embedding Storage

Embeddings can be stored in two ways:
- **Creating a New Collection**: A new database collection is created, and embeddings are populated from scratch.
- **Adding to an Existing Collection**: New embeddings are added to an existing collection.

### Step 6: Similarity Searching

For querying, the database performs a similarity search to find and rank documents based on their cosine similarity to the query embedding.

## Usage

To use this pipeline, follow these steps:
1. Ensure all dependencies are installed, including `langchain`, `pgvector`, and other required libraries.
2. Place your PDF documents in the specified directory.
3. Run the notebook `Document Embeddings and Vector DB.ipynb` to process and embed the documents.
4. Use the querying functionality to search for documents similar to a given text input.

## Conclusion

This pipeline provides a robust framework for working with large volumes of text data by leveraging modern NLP techniques and vector databases. It is designed to be modular and scalable, suitable for educational purposes as well as real-world applications.

# Document Embeddings and Vector DB

In addition to the notebook, there are 2 scripts that can be used:

For Embedding Documents

```bash
usage: scripts/embed_documents.py [-h] --doc_dir DOC_DIR [--add]

options:
  -h, --help         show this help message and exit
  --doc_dir DOC_DIR  path to document to embed
  --add              add to existing collection
```

For Querying an established Vector DB
```bash
usage: scripts/query_documents.py [-h] --query QUERY [--top_k TOP_K]

options:
  -h, --help     show this help message and exit
  --query QUERY  query
  --top_k TOP_K  how many similar entries to return
```