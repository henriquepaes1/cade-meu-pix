"""
Configuration and constants for the ETL pipeline.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Batch sizes
LLM_BATCH_SIZE = 10
DB_BATCH_SIZE = 1000

# Rate limiting
MAX_CONCURRENT_REQUESTS = 2
MAX_RETRIES = 3
REQUEST_DELAY = 1.0  # Seconds between requests

# API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "fraud_cases")

# LLM Prompt Template
PROMPT_TEMPLATE = """# TAREFA
Você é um especialista em análise de fraudes e golpes. Sua tarefa é analisar textos curtos e atribuir uma probabilidade (0 a 1) de que o texto descreva alguém que EFETIVAMENTE SOFREU um golpe ou fraude.

# DEFINIÇÃO DE GOLPE
Um golpe/fraude ocorre quando:
- Houve PERDA REAL de dinheiro, bens ou dados através de engano intencional
- A vítima foi ENGANADA para realizar uma ação prejudicial (transferir dinheiro, entregar produto, fornecer dados)
- Existe um PREJUÍZO CONCRETO já consumado ou em andamento

# IMPORTANTE SOBRE A VÍTIMA
**A vítima pode ser QUALQUER PESSOA mencionada no texto:**
- O próprio autor ("fui enganado", "perdi dinheiro", "me roubaram")
- Familiar ("minha mãe caiu em golpe", "meu pai perdeu dinheiro")
- Amigo/conhecido ("meu amigo foi vítima", "um colega perdeu dinheiro")
- Cliente ("um cliente meu sofreu golpe")
- Qualquer terceiro mencionado ("fulano foi enganado", "ela perdeu dinheiro")

**O QUE IMPORTA:** Alguém específico sofreu prejuízo real por golpe, independente de quem seja.

# O QUE NÃO É GOLPE (probabilidade BAIXA 0.0-0.3):

**1. DISCUSSÃO GENÉRICA sobre golpes**
- "Cuidado com golpes de PIX"
- "Existem muitos golpes hoje em dia"
- "Como evitar golpes?"

**2. NOTÍCIAS sobre golpes**
- Manchetes jornalísticas
- Reportagens sobre casos
- Notícias sem relato pessoal de vítima específica

**3. QUASE-GOLPES (sem prejuízo efetivo)**
- "Quase caí no golpe mas percebi a tempo"
- "Recebi mensagem suspeita mas bloqueei"
- "Tentaram me enganar mas não conseguiram"

# O QUE É GOLPE (probabilidade ALTA 0.7-1.0):

**1. RELATO DIRETO de prejuízo (primeira ou terceira pessoa)**
- "Perdi dinheiro em golpe" / "Minha mãe perdeu dinheiro"
- "Fizeram PIX da conta dele sem autorização"
- "Comprei e não recebi" / "Ela comprou e não recebeu"
- "Me enganaram" / "Enganaram meu pai"
- "Caí num golpe" / "Meu amigo caiu num golpe"

**2. DESCRIÇÃO DETALHADA do golpe sofrido (por qualquer pessoa)**
- Narrativa explicando como alguém foi enganado
- Detalhes da transação fraudulenta sofrida
- Descrição do prejuízo (valores NÃO precisam estar explícitos)

**3. PEDIDO DE AJUDA após vitimização (própria ou de terceiros)**
- "Sofri golpe, o que fazer?"
- "Meu pai sofreu golpe, como ajudar?"
- "Um amigo foi enganado, o que fazer?"

# ESCALA DE PROBABILIDADE
- **0.0 - 0.2**: Claramente NÃO é relato de golpe (notícia, discussão, alerta)
- **0.3 - 0.4**: Provavelmente não é (contexto incerto, pode ser apenas discussão)
- **0.5 - 0.6**: Ambíguo (pode ser golpe mas faltam detalhes claros)
- **0.7 - 0.8**: Provavelmente é (indícios fortes de vitimização)
- **0.9 - 1.0**: Claramente É relato de golpe (prejuízo real relatado)

# INPUT
Você receberá uma lista de x textos indexados no formato:
<0>texto do relato</0>
<1>texto do relato</1>
...
<19>texto do relato</19>

# OUTPUT
Retorne APENAS um JSON válido no formato:
```json
{
  "0": 0.95,
  "1": 0.15,
  "2": 0.60,
  "3": 0.85,
  ...
  "19": 0.30
}
```

**IMPORTANTE**: 
- As keys devem ser strings com os índices ("0", "1", "2", etc.) preservando EXATAMENTE o índice associado ao texto no input
- Os values devem ser números entre 0.0 e 1.0
- Retorne APENAS o JSON, sem texto adicional antes ou depois

# OBSERVAÇÕES CRÍTICAS
- **NOTÍCIAS não são relatos**: Reportagens sobre golpes = probabilidade BAIXA
- **QUASE-GOLPES não contam**: Se não houve prejuízo efetivo = probabilidade BAIXA
- **A VÍTIMA PODE SER QUALQUER PESSOA**: Autor, familiar, amigo, conhecido, cliente, etc.
- **VALORES NÃO PRECISAM estar explícitos**: O prejuízo pode ser descrito sem montantes específicos
- **SÓ ALTA probabilidade quando houver indicação clara de PREJUÍZO REAL sofrido por alguém específico**
- Use a escala completa de 0.0 a 1.0 com granularidade

INPUT:
DATA_PLACEHOLDER"""

# Request timeout (seconds)
REQUEST_TIMEOUT = 60

# Fraud detection threshold (0.0 - 1.0)
FRAUD_PROBABILITY_THRESHOLD = 0.7

def validate_config() -> None:
    """Validate that all required configuration is present."""
    required_vars = {
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "OPENROUTER_API_URL": OPENROUTER_API_URL,
        "OPENROUTER_MODEL": OPENROUTER_MODEL,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
    }
    
    missing = [name for name, value in required_vars.items() if not value]
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please check your .env file."
        )

