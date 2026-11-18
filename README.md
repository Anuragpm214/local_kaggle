# Kaggle GPU + Ollama for VS Code

Run an Ollama model on a Kaggle GPU and connect to it from VS Code using the **Continue** extension. The public tunnel is temporary; restarting the Kaggle session usually creates a new URL.

## 1. Prepare Kaggle

1. Create a new Kaggle notebook, enable **Internet**, and select a **GPU** accelerator in the notebook settings. GPU availability and session limits depend on Kaggle.
2. Copy the contents of [`kaggle_ollama.py`](kaggle_ollama.py) into a Python notebook cell. In the configuration at the top, set `CHAT_MODEL` to the exact name or GGUF reference supported by Ollama. For example:

   ```python
   CHAT_MODEL = "hf.co/bartowski/WhiteRabbitNeo_WhiteRabbitNeo-V3-7B-GGUF:Q4_K_M"
   AUTOCOMPLETE_MODEL = ""  # optional; use a small code-completion model
   IDLE_MINUTES = 20
   MAX_RUNTIME_HOURS = 4
   ```

   Choose a model that fits the GPU's memory. You can also adjust the timeout values. If you set `AUTOCOMPLETE_MODEL`, it will be downloaded and loaded too; add it to Continue separately if needed.
3. Optionally add a Kaggle secret called `API_TOKEN` with a long random value. Otherwise the script generates one for this session. Run the cell and wait for `READY`; the cell keeps running while the server is available. Copy the printed `API URL` and model name.

   By default the script uses a temporary Cloudflare tunnel. For a reserved ngrok domain, set `NGROK_DOMAIN` and add the `NGROK_TOKEN` Kaggle secret. An optional `NTFY_TOPIC` sends the full secret URL to ntfy.sh; leave it empty unless you trust that channel.

## 2. Connect VS Code

1. Install the **Continue** extension in VS Code. The configuration below is Continue's `config.yaml` format; it is not a CodeGPT configuration.
2. Open Continue's main configuration (`~/.continue/config.yaml`) and add a model. Use the **exact same model identifier** as `CHAT_MODEL`, and paste the printed API URL including the token:

   ```yaml
   name: Main Config
   version: 1.0.0
   schema: v1
   models:
     - name: Kaggle GPU model
       provider: ollama
       model: hf.co/bartowski/WhiteRabbitNeo_WhiteRabbitNeo-V3-7B-GGUF:Q4_K_M
       apiBase: https://YOUR-SUBDOMAIN.trycloudflare.com/YOUR_TOKEN
       defaultCompletionOptions:
         contextLength: 8192
       roles:
         - chat
         - edit
         - apply
   ```

3. Save the file, select **Kaggle GPU model** in Continue, and send a message. If you restart the notebook, update `apiBase` with the new printed URL. An `AUTODETECT` entry for a local Ollama server is optional and does not automatically point to Kaggle.

## Stop and security

Run the printed `curl -X POST .../_admin/stop` command, or stop the notebook session in Kaggle. The watchdog also stops the processes after the configured idle time or maximum runtime; this does not guarantee the Kaggle session itself has ended. Check Kaggle and stop the session manually when finished.

The URL contains a bearer secret: anyone who has it can use your model or stop the service. Keep notebook output private, do not commit the URL or token, and restart with a new token if it leaks. This script downloads and executes installers and exposes a model service through a third-party tunnel; review it before running. Kaggle usage limits and service availability apply.

GitHub repository visitors cannot edit the repository directly unless the owner grants them write access. They may still fork a public repository; repository visibility and collaborator permissions are managed in GitHub settings.
