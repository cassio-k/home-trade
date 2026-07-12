import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Calcula a raiz do projeto (um nível acima da pasta api/)
raiz_do_projeto = Path(__file__).resolve().parent.parent
env_path = raiz_do_projeto / ".env"

# Força o carregamento do .env apontando para o caminho correto na raiz
load_dotenv(dotenv_path=env_path)


# 1. Credenciais
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

print("\n=== [DEBUG] DIAGNÓSTICO DE CONEXÃO ===")
print(f"Buscando arquivo .env em: {env_path}")
print(f"Arquivo .env existe? {env_path.exists()}")
print(f"SUPABASE_URL carregada: {url}")
print(f"SUPABASE_KEY (primeiros 10 caracteres): {str(key)[:10]}...")
print("======================================\n")

if not url or not key:
    raise ValueError("CRÍTICO: SUPABASE_URL ou SUPABASE_KEY estão vazias ou não foram lidas.")

# Instância única do cliente
supabase: Client = create_client(url, key)