# Kaggle GPU + Ollama

Use your Kaggle GPU to run your chat model in VS Code with **Continue**.

## 1. Run on Kaggle

Create a notebook, enable **GPU + Internet**, and paste [`kaggle_ollama.py`](kaggle_ollama.py) into a cell. Set:

```python
CHAT_MODEL = "YOUR_CHAT_MODEL"
AUTOCOMPLETE_MODEL = ""  # optional: your autocomplete model
IDLE_MINUTES = 20
MAX_RUNTIME_HOURS = 4
```

Replace `YOUR_CHAT_MODEL` with your exact Ollama model name or supported GGUF reference. Run the cell and copy the printed **API URL** when `READY` appears. Keep the cell running.

## 2. Connect VS Code

Install **Continue**, open its `config.yaml`, and use:

```yaml
name: Main Config
version: 1.0.0
schema: v1
models:
  - name: Your Chat Model
    provider: ollama
    model: YOUR_CHAT_MODEL
    apiBase: YOUR_PRINTED_API_URL
    defaultCompletionOptions:
      contextLength: 8192
    roles: [chat, edit, apply]
```

Use the same model name as `CHAT_MODEL`. Replace `YOUR_PRINTED_API_URL` with the full URL, including its token. Save and select **Your Chat Model** in Continue.

Optional autocomplete: set `AUTOCOMPLETE_MODEL` in the script and add another model entry with its exact name, the same `apiBase`, and `roles: [autocomplete]`.

Keep the API URL private. Update it after restarting Kaggle. Use the printed stop command when finished, then stop the Kaggle session manually. The default limits are 20 minutes idle or 4 hours runtime.
