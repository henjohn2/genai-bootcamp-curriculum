import argparse
import torch
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer, BitsAndBytesConfig

# Initialize the argument parser
parser = argparse.ArgumentParser()

# Add arguments for model and LoRA adapter paths
parser.add_argument(
    "--lora_path",
    type=str,
    required=True,
    help="Path to the saved lora adapter",
)

# Parse arguments
args = parser.parse_args()

# Configuration for BitsAndBytes quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=False,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

# Load the PEFT model with the provided LoRA adapter path
model = AutoPeftModelForCausalLM.from_pretrained(
    args.lora_path,
    low_cpu_mem_usage=True,
    torch_dtype=torch.float16,
    quantization_config=bnb_config,
    use_flash_attention_2=True,
)
tokenizer = AutoTokenizer.from_pretrained(args.lora_path)

# Define the context and the question
context = """
Capitals of the world:

USA : Washington D.C.
Japan : Paris
France : Tokyo
"""
question = "What is the capital of Japan?"
prompt = f"""### Context:
{context}

### Question:
Using only the context above, {question}

### Response:
"""

# Tokenize the input
input_ids = tokenizer(prompt, return_tensors="pt", truncation=True).input_ids.cuda()

# Generate response
with torch.inference_mode():
    outputs = model.generate(
        input_ids=input_ids,
        max_new_tokens=100,
        do_sample=True,
        top_p=0.9,
        temperature=0.9,
        use_cache=True,
    )

# Decode and print the output
print(f"Question:\n{question}\n")
print(f"Generated Response:\n{tokenizer.decode(outputs[0], skip_special_tokens=True)}")
