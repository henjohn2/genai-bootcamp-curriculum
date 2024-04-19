import argparse

import gradio as gr
from peft import AutoPeftModelForCausalLM
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread

from langchain.vectorstores.pgvector import PGVector
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from typing import List, Tuple


parser = argparse.ArgumentParser()
parser.add_argument(
    "--model_path_or_id",
    type=str,
    default="mistralai/Mistral-7B-v0.1",
    required=False,
    help="Model ID or path to saved model",
)

parser.add_argument(
    "--lora_path",
    type=str,
    default=None,
    required=False,
    help="Path to the saved lora adapter",
)

args = parser.parse_args()

if args.lora_path:
    # load base LLM model with PEFT Adapter
    model = AutoPeftModelForCausalLM.from_pretrained(
        args.lora_path,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float16,
        bnb_4bit_compute_dtype=torch.float16,
        use_flash_attention_2=True,
        load_in_4bit=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.lora_path)
else:
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path_or_id,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float16,
        bnb_4bit_compute_dtype=torch.float16,
        use_flash_attention_2=True,
        load_in_4bit=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model_path_or_id)

# The connection to the database
CONNECTION_STRING = PGVector.connection_string_from_db_params(
    driver="psycopg2",
    host="localhost",
    port="5432",
    database="postgres",
    user="username",
    password="password",
)

# The embedding function that will be used to store into the database
embedding_function = SentenceTransformerEmbeddings(
    model_name="BAAI/bge-large-en-v1.5",
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True},
)

# Creates the database connection to our existing DB
db = PGVector(
    connection_string=CONNECTION_STRING,
    collection_name="embeddings",
    embedding_function=embedding_function,
)


def preprocess_prompt(
    user_message: str, chat: List[List[str]]
) -> Tuple[str, List[List[str]]]:
    """Preprocess prompt and add the new question to the chat history

    Args:
        user_message (str): user question
        chat (List[List[str]]): full past chat history as a `List` of
            [past_message, past_response]

    Returns:
        Tuple[str, List[List[str]]]: tuple of message and updated chat
            history with new [user_message, None].
    """

    return "", [[user_message, None]]


def send_to_chatbot(
    chat: List[List[str]],
    prompt_format: str,
    max_new_tokens: int,
    temperature: float,
):
    """Send a conversation to the chatbot

    Args:
        chat (List[List[str]]): full chat history to format and
            send to the model
        prompt_format (str): formatting template to use
        max_new_tokens (int): max new tokens
        temperature (float): temperature

    Yields:
        List[List[str]]: updated chat history with bot response
    """
    # Format the instruction using the format string with keys
    # {question}, {context}
    docs_with_scores = db.similarity_search_with_score(chat[-1][0], k=1)
    context = docs_with_scores[0][0].page_content
    formatted_inst = prompt_format.format(context=context, question=chat[-1][0])

    # Tokenize the input
    input_ids = tokenizer(
        formatted_inst, return_tensors="pt", truncation=True
    ).input_ids.cuda()

    # Support for streaming of tokens within generate requires
    # generation to run in a separate thread
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True)
    generation_kwargs = dict(
        input_ids=input_ids,
        streamer=streamer,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        top_p=0.9,
        temperature=temperature,
        use_cache=True,
    )

    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()

    chat[-1][1] = ""
    for new_text in streamer:
        chat[-1][1] += new_text
        yield chat, context


with gr.Blocks() as demo:
    gr.HTML(
        f"""
        <h2> Instruction Chat Bot Demo </h2>
        <h3> Model ID : {args.model_path_or_id} </h3>
        <h3> Peft Adapter : {args.lora_path} </h3>
    """
    )

    chat = gr.Chatbot(label="QA Bot")
    context_state = gr.Textbox(label="Used Context", interactive=False)
    msg = gr.Textbox(label="Question")
    with gr.Accordion(label="Generation Parameters", open=False):
        prompt_format = gr.Textbox(
            label="Formatting prompt", value="{question}", lines=8
        )
        with gr.Row():
            max_new_tokens = gr.Number(
                minimum=25, maximum=500, value=100, label="Max New Tokens"
            )
            temperature = gr.Slider(
                minimum=0, maximum=1.0, value=0.7, label="Temperature"
            )

    clear = gr.ClearButton([msg, chat])

    # Add an event listener for when the user submits a message
    msg.submit(
        preprocess_prompt,
        inputs=[msg, chat],
        outputs=[msg, chat],
        queue=False,
    ).then(
        send_to_chatbot,
        inputs=[chat, prompt_format, max_new_tokens, temperature],
        outputs=[chat, context_state],
    )

demo.queue()
demo.launch()