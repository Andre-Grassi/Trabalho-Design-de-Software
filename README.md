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
- **Interface Web de Testes (GUI):** [http://127.0.0.1:8000](http://127.0.0.1:8000) (permite testar interativamente todos os fluxos descritos abaixo com inspetor HTTP)
- **Documentação Swagger (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Documentação Redoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Exemplos de Uso da API

O banco de dados SQLite (`reservas_institucional.db`) é populado automaticamente ao iniciar a aplicação com os seguintes usuários e salas de exemplo:

- **Usuários:**
  - `u1`: Prof. Carlos (Perfil: `DOCENTE`, auto-aprovação de reservas)
  - `u2`: Ana (Perfil: `ALUNO`, reservas ficam como `PENDENTE`)
  - `u3`: Marcos (Perfil: `GESTOR`, pode aprovar/rejeitar reservas e ver auditoria)
- **Salas:**
  - `s1`: `PA-04` (Sala de aula comum)
  - `s2`: `LAB-REDES` (Laboratório de informática)
  - `s3`: `LAB-PESQUISA` (Laboratório restrito)

Abaixo estão exemplos práticos utilizando `curl` (ou via Swagger UI em `/docs`):

### 1. Consultar Salas Disponíveis

Lista salas que o usuário tem permissão para visualizar/reservar (suporta filtro opcional de intervalo de tempo para checar disponibilidade contra grade acadêmica e reservas ativas):

```bash
# Consultar todas as salas acessíveis pela aluna Ana (u2)
curl -X GET "http://127.0.0.1:8000/salas?usuario_id=u2"

# Consultar salas disponíveis em um horário específico (ex: 2026-11-25 das 14:00 às 16:00)
curl -X GET "http://127.0.0.1:8000/salas?usuario_id=u1&inicio=2026-11-25T14:00:00&fim=2026-11-25T16:00:00"
```

### 2. Solicitar uma Reserva

#### Exemplo A: Reserva por Docente (Aprovação Automática — `CONFIRMADA`)
```bash
curl -X POST "http://127.0.0.1:8000/reservas" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario_id": "u1",
    "sala_id": "s1",
    "inicio": "2026-11-25T10:00:00",
    "fim": "2026-11-25T12:00:00",
    "qtd_pessoas": 25
  }'
```
*Resposta esperada (`201 Created`):*
```json
{
  "id": "res-a1b2c3d4",
  "usuario_id": "u1",
  "sala_id": "s1",
  "inicio": "2026-11-25T10:00:00",
  "fim": "2026-11-25T12:00:00",
  "qtd_pessoas": 25,
  "status": "CONFIRMADA"
}
```

#### Exemplo B: Reserva por Estudante (Requer Avaliação — `PENDENTE`)
```bash
curl -X POST "http://127.0.0.1:8000/reservas" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario_id": "u2",
    "sala_id": "s2",
    "inicio": "2026-11-25T14:00:00",
    "fim": "2026-11-25T16:00:00",
    "qtd_pessoas": 10
  }'
```
*Resposta esperada (`201 Created`):* status inicial `"PENDENTE"`.

---

### 3. Avaliar Reserva Pendente (Ação de Gestor)

O técnico/gestor (`u3`) avalia a solicitação do aluno, aprovando ou rejeitando a reserva:

```bash
curl -X POST "http://127.0.0.1:8000/reservas/ID_DA_RESERVA_PENDENTE/avaliar?aprovador_id=u3&aprovada=true"
```

---

### 4. Substituição Atômica de Reserva (Troca em Caso de Conflito de Horário)

Se o usuário já possui um agendamento e tenta reservar outro espaço no mesmo horário, o sistema retorna `409 Conflict` com o ID da reserva conflitante. O usuário pode optar pela **troca atômica**:

```bash
curl -X POST "http://127.0.0.1:8000/reservas/ID_RESERVA_ANTIGA/troca" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario_id": "u1",
    "sala_id": "s2",
    "inicio": "2026-11-25T10:00:00",
    "fim": "2026-11-25T12:00:00",
    "qtd_pessoas": 15
  }'
```
*Em uma única transação ACID, a reserva antiga é cancelada e a nova é confirmada.*

---

### 5. Cancelar Reserva

Permite ao solicitante cancelar uma reserva antes do início agendado:

```bash
curl -X POST "http://127.0.0.1:8000/reservas/ID_DA_RESERVA/cancelar?usuario_id=u1"
```

---

### 6. Consultar Trilha de Auditoria (ASR 2)

Apenas usuários com perfil de `GESTOR` possuem permissão para auditar as transações do sistema:

```bash
# Listar todos os logs de auditoria
curl -X GET "http://127.0.0.1:8000/auditoria?gestor_id=u3"

# Filtrar o histórico de uma reserva específica
curl -X GET "http://127.0.0.1:8000/auditoria?gestor_id=u3&entidade_id=ID_DA_RESERVA"
```

---

## Executando os Testes Automatizados

O projeto possui uma suíte de testes unitários, de integração (concorrência ACID, triggers de integridade do SQLite e substituição de dependências externas via DIP) e de API HTTP em `tests/`:

```bash
python -m pytest -v
```



