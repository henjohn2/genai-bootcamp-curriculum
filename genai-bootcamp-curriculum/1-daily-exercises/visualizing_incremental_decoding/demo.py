import torch  # Import the PyTorch library for tensor operations and neural network models.
from transformers import AutoTokenizer, MistralForCausalLM  # Import necessary modules from the transformers library.
import argparse  # Import the argparse library to handle command-line arguments.

def parse_args():
    """Parse command line arguments for the script."""
    parser = argparse.ArgumentParser(description="Generate text with a language model.")  # Initialize an ArgumentParser object with a description.
    parser.add_argument("--initial_text", type=str, default="The quick brown fox",  # Define a command-line option for initial text.
                        help="Initial text to start text generation.")
    parser.add_argument("--max_length", type=int, default=50,  # Define a command-line option for the maximum length of the generated text.
                        help="Maximum sequence length of the generated text.")
    parser.add_argument("--strategy", type=str, default="manual",  # Define a command-line option to choose the generation strategy.
                        choices=["greedy", "sample", "manual"],
                        help="Strategy for text generation: greedy, sample, or manual select.")
    parser.add_argument("--num_choices", type=int, default=5, help="Number of choices for manual selection.")  # Define a command-line option for the number of choices in manual mode.
    parser.add_argument("--temperature", type=float, default=1.0,  # Define a command-line option for the temperature setting.
                        help="Temperature for sampling: higher values increase randomness.")
    return parser.parse_args()  # Return the parsed command-line arguments.

def initialize_model():
    """Initialize and return the tokenizer and language model."""
    tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")  # Load the tokenizer for encoding text.
    model = MistralForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1")  # Load the language model.
    model.eval()  # Put the model in evaluation mode, disabling dropout for consistent results.
    return tokenizer, model  # Return both the tokenizer and model.

def generate_text(tokenizer, model, args):
    """Generate text using the specified model and strategy."""
    input_ids = tokenizer.encode(args.initial_text, return_tensors='pt')  # Convert initial text to tensor of input IDs.
    output = input_ids  # Initialize the output tensor with the encoded initial text.
    past_key_values = None  # Initialize past key values for efficient text generation.

    for _ in range(args.max_length):  # Loop through the specified maximum length of text.
        outputs = model(input_ids, past_key_values=past_key_values, use_cache=True)  # Generate outputs using the model.
        logits = outputs.logits / args.temperature  # Apply temperature to logits to control randomness.
        past_key_values = outputs.past_key_values  # Update past key values with the outputs.
        
        #output[0] is a list of ids that it has generated so far aka tensor([    1,  2766,  1197, 16107,   349])
        generated_text = tokenizer.decode(output[0], skip_special_tokens=True)  # Decode generated text so far.
        print("\nCurrent generated text:", generated_text)  # Print the current generated text.

        next_token = choose_next_token(logits, args, tokenizer)  # Choose the next token based on strategy.
        if next_token is None:  # If no next token (e.g., manual exit), break the loop.
            break
        output = torch.cat((output, next_token), dim=-1)  # Append the next token to the output tensor.
        input_ids = next_token  # Update input_ids for the next iteration.

    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)  # Decode the complete generated text.
    print("\nFinal generated text:", generated_text)  # Print the final generated text.

def choose_next_token(logits, args, tokenizer):
    """Choose the next token based on the generation strategy defined in args."""
    if args.strategy == "greedy":  # If greedy strategy is selected,
        return logits[:, -1, :].argmax(dim=-1, keepdim=True)  # Return the token with the highest probability.
    elif args.strategy == "sample":  # If sample strategy is selected,
        probabilities = torch.nn.functional.softmax(logits[:, -1, :], dim=-1)  # Convert logits to probabilities.
        return torch.multinomial(probabilities, num_samples=1)  # Sample a token according to the probability distribution.
    elif args.strategy == "manual":  # If manual strategy is selected,
        softmax_scores = torch.nn.functional.softmax(logits[:, -1, :], dim=-1)  # Compute softmax scores for the logits.
        top_prob, top_indices = torch.topk(softmax_scores, args.num_choices, dim=-1)  # Get the top probabilities and their indices.
        decoded_options = [(tokenizer.decode([idx]), prob.item()) for idx, prob in zip(top_indices[0], top_prob[0])]  # Decode the top choices.
        
        print("\nEnter one of the following options or type 'exit' to finish:")  # Ask user for manual input.
        for i, (word, score) in enumerate(decoded_options, 1):  # Print each option with its score.
            print(f"{i}: {word} (score: {score:.5f})")

        while True:  # Loop until valid input is received.
            choice_input = input("Your choice (number or 'exit'): ")  # Get user input.
            if choice_input.lower() == 'exit':  # If input is 'exit',
                print("\nExiting generation loop.")  # Print exit message.
                return None  # Return None to indicate exit.
            elif choice_input.isdigit() and 1 <= int(choice_input) <= len(decoded_options):  # If input is a valid number,
                choice = int(choice_input) - 1  # Adjust index for 0-based indexing.
                return top_indices[:, choice].unsqueeze(-1)  # Return the selected token index.
            else:  # If input is invalid,
                print(f"Invalid input. Please enter a number between 1 and {len(decoded_options)} or 'exit'.")  # Print error message.

def main():
    """Main function to orchestrate the text generation process."""
    args = parse_args()  # Parse command line arguments.
    tokenizer, model = initialize_model()  # Initialize the model and tokenizer.
    generate_text(tokenizer, model, args)  # Start text generation process.

if __name__ == "__main__":
    main()  # Run the main function if this script is executed as the main program.
