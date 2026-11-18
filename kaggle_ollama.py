import os, sys, time, re, subprocess, secrets, json, urllib.request

# ================= CONFIG =================
CHAT_MODEL = "hf.co/bartowski/WhiteRabbitNeo_WhiteRabbitNeo-V3-7B-GGUF:Q4_K_M"
AUTOCOMPLETE_MODEL = ""   # "" = skip
NGROK_DOMAIN       = ""    # e.g. "your-name.ngrok-free.app"; "" = cloudflared random URL
IDLE_MINUTES       = 20
MAX_RUNTIME_HOURS  = 4
NTFY_TOPIC         = ""    # optional, random secret string
# ==========================================

def secret(name):
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret(name)
    except Exception:
        return os.environ.get(name)

TOKEN = secret("API_TOKEN") or secrets.token_urlsafe(24)
NGROK_TOKEN = secret("NGROK_TOKEN") if NGROK_DOMAIN else None

def sh(cmd):
    subprocess.run(cmd, shell=True, check=True)

for f in ("/tmp/STOP", "/tmp/last_active"):
    if os.path.exists(f): os.remove(f)

# ---------- install ----------
sh("apt-get update -qq && apt-get install -y -qq zstd pciutils lshw >/dev/null")
sh("curl -fsSL https://ollama.com/install.sh | sh")
sh("pip install -q fastapi uvicorn httpx pyngrok")
if not NGROK_TOKEN:
    sh("curl -fsSL -o /usr/local/bin/cloudflared "
       "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 "
       "&& chmod +x /usr/local/bin/cloudflared")

# ---------- ollama ----------
env = {**os.environ,
       "OLLAMA_HOST": "127.0.0.1:11434",
       "OLLAMA_KEEP_ALIVE": "30m",
       "OLLAMA_MAX_LOADED_MODELS": "2",
       "OLLAMA_NUM_PARALLEL": "2",
       "OLLAMA_CONTEXT_LENGTH": "8192"}
ollama_p = subprocess.Popen(["ollama", "serve"], env=env,
                            stdout=open("/tmp/ollama.log", "w"), stderr=subprocess.STDOUT)
for _ in range(60):
    try:
        urllib.request.urlopen("http://127.0.0.1:11434", timeout=2); break
    except Exception:
        time.sleep(1)

for m in filter(None, [CHAT_MODEL, AUTOCOMPLETE_MODEL]):
    sh(f"ollama pull {m}")

# warm-up: model ko VRAM me pehle hi load kar do
for m in filter(None, [CHAT_MODEL, AUTOCOMPLETE_MODEL]):
    try:
        urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps({"model": m, "keep_alive": "30m"}).encode()), timeout=300)
    except Exception as e:
        print("warmup fail", m, e)

# ---------- auth + activity proxy ----------
PROXY = r'''
import os, time, httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse

TOKEN = os.environ["API_TOKEN"]
UP = "http://127.0.0.1:11434"
app = FastAPI()
client = httpx.AsyncClient(timeout=None)

def touch():
    open("/tmp/last_active", "w").write(str(time.time()))

@app.api_route("/{token}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD"])
async def proxy(token: str, path: str, request: Request):
    if token != TOKEN:
        return JSONResponse({"error": "not found"}, status_code=404)
    if path == "_admin/stop" and request.method == "POST":
        open("/tmp/STOP", "w").write("1")
        return {"stopping": True}
    if path == "_admin/status":
        last = float(open("/tmp/last_active").read())
        return {"idle_seconds": int(time.time() - last)}
    touch()
    drop = {"host", "content-length", "origin", "accept-encoding", "connection"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in drop}
    req = client.build_request(request.method, f"{UP}/{path}",
                               content=await request.body(),
                               headers=headers, params=request.query_params)
    r = await client.send(req, stream=True)
    async def gen():
        try:
            async for chunk in r.aiter_raw():
                touch()
                yield chunk
        finally:
            await r.aclose()
    return StreamingResponse(gen(), status_code=r.status_code,
                             media_type=r.headers.get("content-type"))
'''
open("/tmp/proxy.py", "w").write(PROXY)
open("/tmp/last_active", "w").write(str(time.time()))

proxy_p = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "proxy:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd="/tmp", env={**os.environ, "API_TOKEN": TOKEN},
    stdout=open("/tmp/proxy.log", "w"), stderr=subprocess.STDOUT)
time.sleep(3)

# ---------- public URL ----------
tun_p, BASE = None, None
if NGROK_TOKEN:
    from pyngrok import ngrok
    ngrok.set_auth_token(NGROK_TOKEN)
    BASE = ngrok.connect(8000, domain=NGROK_DOMAIN).public_url.replace("http://", "https://")
else:
    tun_p = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8000", "--no-autoupdate"],
        stdout=open("/tmp/tunnel.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        time.sleep(1)
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", open("/tmp/tunnel.log").read())
        if m: BASE = m.group(0); break
assert BASE, "Tunnel URL nahi mila (/tmp/tunnel.log dekh)"

API = f"{BASE}/{TOKEN}"
print("=" * 60)
print("READY")
print("API URL :", API)
print("STOP    :", f'curl -X POST "{API}/_admin/stop"')
print(f"""
# Continue config.yaml:
models:
  - name: WhiteRabbitNeo Kaggle
    provider: ollama
    model: {CHAT_MODEL}
    apiBase: {API}
    roles: [chat, edit, apply]
""")
print("=" * 60)

if NTFY_TOPIC:
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}", data=API.encode()), timeout=10)
    except Exception as e:
        print("ntfy fail:", e)

# ---------- watchdog ----------
t0, reason = time.time(), None
while reason is None:
    time.sleep(10)
    idle = time.time() - float(open("/tmp/last_active").read())
    if os.path.exists("/tmp/STOP"):                  reason = "OFF (curl stop)"
    elif idle > IDLE_MINUTES * 60:                   reason = f"{IDLE_MINUTES} min idle"
    elif time.time() - t0 > MAX_RUNTIME_HOURS*3600:  reason = "max runtime"
    elif tun_p and tun_p.poll() is not None:         reason = "tunnel crash"
    elif proxy_p.poll() is not None:                 reason = "proxy crash"
    elif ollama_p.poll() is not None:                reason = "ollama crash"

print("Shutting down:", reason)
for p in filter(None, (tun_p, proxy_p, ollama_p)):
    p.terminate()
print("Done. Stop the Kaggle session manually if it is still running.")
