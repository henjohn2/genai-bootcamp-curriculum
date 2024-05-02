from typing import List, Dict
import torch
from transformers import AutoTokenizer, BitsAndBytesConfig
from langchain.vectorstores.pgvector import PGVector
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from peft import AutoPeftModelForCausalLM

# Model and tokenizer setup
model_path_or_id = "mistralai/Mistral-7B-v0.1"
tokenizer = AutoTokenizer.from_pretrained(model_path_or_id)

# Load the PEFT model trained for specific purposes
model = AutoPeftModelForCausalLM.from_pretrained(
    "mistral-7b-int4-dolly/checkpoint-12",
    low_cpu_mem_usage=True,
    torch_dtype=torch.float16,
    bnb_4bit_compute_dtype=torch.float16,
    use_flash_attention_2=True,
    load_in_4bit=True,
)

def generate(prompt: str, max_new_tokens: int = 100, temperature: float = 0.7) -> str:
    """
    Generate text from a provided prompt using the specified model, applying temperature-based sampling.

    Args:
        prompt (str): The text prompt to guide the generation.
        max_new_tokens (int): Maximum number of new tokens to generate.
        temperature (float): Temperature parameter influencing the randomness of the generation.

    Returns:
        str: The generated text, appended to the original prompt content.
    """
    # Prepare the input for the model
    input_ids = tokenizer(prompt, return_tensors="pt", truncation=True).input_ids.cuda()
    
    # Generate output tokens with specified parameters
    with torch.inference_mode():
        outputs = model.generate(
            input_ids=input_ids, 
            max_new_tokens=max_new_tokens,
            do_sample=True, 
            top_p=0.9, 
            temperature=temperature,
            use_cache=True
        )
    
    # Decode generated tokens to string, skipping special tokens
    generated_text = tokenizer.batch_decode(outputs.detach().cpu().numpy(), skip_special_tokens=True)
    return generated_text[0][len(prompt):]

# Database connection configuration
CONNECTION_STRING = PGVector.connection_string_from_db_params(
    driver="psycopg2",
    host="localhost",
    port="5432",
    database="postgres",
    user="username",
    password="password"
)

# Configure the embedding function and establish a database connection
embedding_function = SentenceTransformerEmbeddings(
    model_name="BAAI/bge-large-en-v1.5",
    model_kwargs={'device': 'cuda'},
    encode_kwargs={'normalize_embeddings': True}
)

db = PGVector(
    connection_string=CONNECTION_STRING,
    collection_name="embeddings",
    embedding_function=embedding_function
)

# Define the prompt template for generating responses based on contextual information
RAG_PROMPT_TEMPLATE = """### Context:
{context}

### Question:
Using only the context above, {question}

### Response:
"""

# Generating a response based on a context retrieved from the database
question = "What is the efficacy of NeuroGlyde?"
docs_with_scores = db.similarity_search_with_score(question, k=3)
docs_content = [doc.page_content for doc, _ in docs_with_scores]
context_string = '\n\n'.join(docs_content)

context_prompt = RAG_PROMPT_TEMPLATE.format(
    context=context_string,
    question=question
)

# Generate the response using the constructed prompt
response = generate(context_prompt, max_new_tokens=100, temperature=0.1)

print(f"Question:\n{question}\n")
print(f"Generated Response:\n{response}")
