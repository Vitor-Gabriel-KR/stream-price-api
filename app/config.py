import os
from pathlib import Path
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent

dotenv_path = APP_DIR / ".env"

if not dotenv_path.exists():
    print(f"❌ [AVISO] Arquivo .env não encontrado em: {dotenv_path}")

load_dotenv(dotenv_path=dotenv_path)

class Settings:
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY")
    POSTGRES_URI: str = os.environ.get("POSTGRES_URI", "postgresql://usuario:senha@localhost:5432/nome_do_seu_banco")
    
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    STREAMINGS: list[dict[str, str]] = [
        {"nome": "Netflix", "url": "https://help.netflix.com/pt/node/24926"},
        {"nome": "Spotify", "url": "https://www.spotify.com/br-pt/premium/#plans"},
        {"nome": "Crunchyroll", "url": "https://www.crunchyroll.com/pt-br/welcome"},
        {"nome": "Prime Video", "url": "https://www.primevideo.com/signup/ref=atv_nb_join_prime"},
        {"nome": "HBO Max", "url": "https://www.hbomax.com/br/pt"},
        {"nome": "Disney+", "url": "https://www.disneyplus.com/pt-br"},
        {"nome": "Apple TV", "url": "https://tv.apple.com/br"},
        {"nome": "YouTube Premium", "url": "https://www.youtube.com/premium?ybp=Sg0IBhIJdW5saW1pdGVk4AEB"}
    ]

settings = Settings()