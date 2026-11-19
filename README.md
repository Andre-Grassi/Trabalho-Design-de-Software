# Trabalho-Design-de-Software
Trabalho Design de Software 2026/2 UFPR BCC

[Docs](https://docs.google.com/document/d/1fIW6S_3Eb2B6-Ao0B9CDNS30-7XZx9l1nHf-TMDJQnI/edit?tab=t.0)

---

## Como Executar a Aplicação

Este projeto utiliza **FastAPI** e deve ser executado utilizando o servidor ASGI **Uvicorn**.

### 1. Pré-requisitos e Instalação

Certifique-se de ter o Python 3.10+ instalado. Em seguida, crie um ambiente virtual (opcional, porém recomendado) e instale as dependências:

```bash
# Criar e ativar o ambiente virtual (Linux/macOS)
python -m venv .venv
source .venv/bin/activate

# No Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt
```

### 2. Executando com Uvicorn

A partir da raiz do projeto, execute o seguinte comando:

```bash
uvicorn src.main:app --reload
```

Ou, caso prefira executar pelo módulo do Python:

```bash
python -m uvicorn src.main:app --reload
```

**Parâmetros utilizados:**
- `src.main:app`: Aponta para o módulo `main.py` dentro da pasta `src/` e a instância `app` do FastAPI.
- `--reload`: Habilita o recarregamento automático do servidor a cada alteração salva no código (ideal para desenvolvimento).

### 3. Acessando a Aplicação e Documentação Interativa

Após iniciar o servidor, a API estará acessível em:
- **Aplicação:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Documentação Swagger (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Documentação Redoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

