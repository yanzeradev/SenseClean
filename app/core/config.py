from pathlib import Path

# Pega o diretório raiz do projeto de forma dinâmica baseada onde o config.py está
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Paths Estáticos
#MODEL_PATH = BASE_DIR / "model_gender.pt"
MODEL_PATH = "yolo26n-seg.pt"

# Outras configurações que não mudam...
MAX_VIDEO_SIZE_MB = 50