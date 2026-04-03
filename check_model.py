from google import genai

# Use your key here
client = genai.Client(api_key='')

print(f"{'Model ID':<40} | {'Input Limit':<12} | {'Display Name'}")
print("-" * 80)

# List all models that support generating text/code
for model in client.models.list():
    if 'generateContent' in model.supported_actions:
        print(f"{model.name:<40} | {model.input_token_limit:<12} | {model.display_name}")