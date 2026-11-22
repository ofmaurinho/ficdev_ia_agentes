"""Configuração local e caminhos do acervo do exercício."""
from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")
EXAMPLES_DIR = PROJECT_ROOT / "exemplos"
DATA_DIR = EXAMPLES_DIR / "dados"
GABARITO_PATH = EXAMPLES_DIR / "gabarito.json"  # importar somente em avaliacao.py
GERADOR_PATH = EXAMPLES_DIR / "gerar_dados.py"
NORMAS_PATH = DATA_DIR / "normas.md"
SERVIDORES_PATH = DATA_DIR / "servidores.csv"
HISTORICO_DIARIAS_PATH = DATA_DIR / "historico_diarias.csv"
TABELA_DIARIAS_PATH = DATA_DIR / "tabela_diarias.json"
UNIDADES_PATH = DATA_DIR / "unidades.json"
PEDIDOS_PATH = DATA_DIR / "pedidos.json"
COMPLEMENTACOES_PATH = DATA_DIR / "complementacoes.json"
DB_PATH = PROJECT_ROOT / "memoria_diarias.sqlite"
RETENCAO_DIAS = int(os.getenv("RETENCAO_MEMORIA_DIAS", "30"))  # decisão provisória de projeto
TOOL_CALL_LIMIT = 6
PRECO_ENTRADA_MILHAO = 0.20
PRECO_SAIDA_MILHAO = 1.20
MODELO = "gpt-5.6-luna"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
