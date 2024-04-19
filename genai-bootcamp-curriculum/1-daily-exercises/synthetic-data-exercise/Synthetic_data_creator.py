import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# Load the dataset
input_file = 'data/fake_data_systems_tables.csv'
data = pd.read_csv(input_file)

# Original columns from the dataset
original_columns = data.columns.tolist()

# New columns for the generated table structure
generated_columns = ['ColumnNames', 'ColumnAcronyms', 'DataTypes', 'Nullability', 'ColumnDescriptions']

# Initialize an empty dataframe to store the results
# Note: We adjust the DataFrame initialization to better accommodate list storage for generated columns
results_df = pd.DataFrame()

# THE FIRST TIME YOU RUN THIS, IT MIGHT TAKE A WHILE
model_path_or_id = "mistralai/Mistral-7B-Instruct-v0.1"
tokenizer = AutoTokenizer.from_pretrained(model_path_or_id)
model = AutoModelForCausalLM.from_pretrained(
    model_path_or_id,
    low_cpu_mem_usage=True,
    torch_dtype=torch.float16,
    bnb_4bit_compute_dtype=torch.float16,
    #use_flash_attention_2=True,
    attn_implementation="flash_attention_2",
    load_in_4bit=True
)

def generate_table_structure(info):
    prompt = f"Please generate a table of 20 column names, column acronym, data type, nullability, and column descriptions for the given information: {info}. In CSV format."
    """Convenience function for generating model output"""
    # Tokenize the input
    input_ids = tokenizer(
        prompt, 
        return_tensors="pt", 
        truncation=True).input_ids.cuda()
    
    # Generate new tokens based on the prompt, up to max_new_tokens
    # Sample aacording to the parameter
    with torch.inference_mode():
        outputs = model.generate(
            input_ids=input_ids, 
            max_new_tokens=500, 
            do_sample=True, 
            top_p=0.9,
            temperature=0.1,
            use_cache=True
        )
    return tokenizer.batch_decode(outputs.detach().cpu().numpy(), skip_special_tokens=True)[0][len(prompt):]

def parse_table_structure(table_text):
    lines = table_text.split('\n')
    table_data = []
    for line in lines:
        fields = line.split(',')
        # Adjust parsing to correctly create lists of lists for each generated row
        if len(fields) >= len(generated_columns):  # Ensure we have the expected number of fields
            table_data.append(fields[:len(generated_columns)])  # Append a list for each row
    return table_data

count = 0

# Iterate through each row in the dataset and call the OpenAI API
for index, row in data.iterrows():
    count += 1 
    progress = count / len(data)*100
    print(f'{progress:.2f}%')
    generated_table_text = generate_table_structure(row.to_json())
    generated_table_data = parse_table_structure(generated_table_text)

    # Each generated row is added to the results DataFrame
    for generated_row in generated_table_data:
        # Combine original row data with generated data
        combined_row_data = row.tolist() + generated_row
        # Dynamically adjust column names to accommodate both original and generated data
        dynamic_columns = original_columns + [f'Generated_{col}' for col in generated_columns]
        result_row = pd.DataFrame([combined_row_data], columns=dynamic_columns)
        results_df = pd.concat([results_df, result_row], ignore_index=True)

# Save the final dataframe to a CSV file
output_file = 'data/generated_table_structures_with_original_data.csv'
results_df.to_csv(output_file, index=False)

print(f"Data saved to {output_file}")
