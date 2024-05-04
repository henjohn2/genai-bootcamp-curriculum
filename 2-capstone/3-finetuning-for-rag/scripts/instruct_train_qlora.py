import time
from datasets import load_dataset, Dataset
from transformers import (
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
    AutoModelForCausalLM,
)
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from trl import SFTTrainer
import torch


def load_modified_dataset() -> Dataset:
    """
    Load a dataset from Hugging Face Hub, filter by specified categories, and prepare for training.

    Returns:
        Dataset: A filtered Hugging Face `Dataset` object containing only the needed columns.
    """
    # Load dataset and convert to pandas DataFrame for processing
    dataset = load_dataset("databricks/databricks-dolly-15k", split="train").to_pandas()
    # Filter dataset based on category inclusion
    dataset["keep"] = dataset["category"].isin(
        ["closed_qa", "information_extraction", "open_qa"]
    )
    # Create a new dataset from filtered data preserving only relevant columns
    return Dataset.from_pandas(
        dataset[dataset["keep"]][["instruction", "context", "response"]],
        preserve_index=False,
    )


def format_instruction(sample: dict) -> str:
    """
    Format each dataset sample into a string structured specifically for the language model.

    Args:
        sample (dict): A dictionary containing keys 'context', 'instruction', and 'response'.

    Returns:
        str: A formatted string that structures context, instruction, and response for training.
    """
    return f"""### Context:\n{sample['context']}\n\n### Question:\nUsing only the context above, {sample['instruction']}\n\n### Response:\n{sample['response']}\n"""


# Load and prepare dataset
dataset = load_modified_dataset()

# Setup the base model and tokenizer
model_id = "mistralai/Mistral-7B-v0.1"
tokenizer = AutoTokenizer.from_pretrained(model_id)
tokenizer.pad_token = tokenizer.eos_token  # Use end of sequence token as padding
tokenizer.padding_side = "right"  # Pad sequences on the right side by default

# Configure PEFT and BnB for the model
peft_config = LoraConfig(
    lora_alpha=16,
    lora_dropout=0.1,
    r=8,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "v_proj",
        "down_proj",
        "up_proj",
        "o_proj",
        "q_proj",
        "gate_proj",
        "k_proj",
    ],
)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=False,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    low_cpu_mem_usage=True,
    torch_dtype=torch.float16,
    quantization_config=bnb_config,
    attn_implementation="flash_attention_2",
)
model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, peft_config)

# Setup training arguments
args = TrainingArguments(
    output_dir="./mistral-7b-int4-dolly",
    num_train_epochs=1,  # number of training epochs
    per_device_train_batch_size=7,  # batch size per device
    gradient_accumulation_steps=4,  # effective batch size is 7 * 4 = 28
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": True},
    optim="paged_adamw_32bit",
    logging_steps=1,  # log the training error every step
    save_strategy="epoch",  # save checkpoints at the end of each epoch
    save_total_limit=1,  # retain only the most recent checkpoint
    ignore_data_skip=True,
    learning_rate=1e-5,
    bf16=True,
    tf32=True,
    max_grad_norm=1.0,
    warmup_steps=100,
    lr_scheduler_type="constant",
    disable_tqdm=True,
)

# Configure and run the trainer
max_seq_length = 2048
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    tokenizer=tokenizer,
    max_seq_length=max_seq_length,
    packing=True,
    formatting_func=format_instruction,
    args=args,
)

# Time the training process
start = time.time()
trainer.train(resume_from_checkpoint=False)
trainer.save_model()
end = time.time()

print(f"Training completed in {end - start:.2f}s")
