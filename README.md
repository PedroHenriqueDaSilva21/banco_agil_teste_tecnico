# Banco Ágil IA

Sistema de atendimento ao cliente para o banco digital fictício **Banco Ágil**, operado por agentes de IA especializados. O cliente interage com um único assistente (**Lican**), enquanto internamente um supervisor roteia a conversa para o agente adequado de forma transparente.

## Índice

- [Visão geral](#visão-geral)
- [Funcionalidades implementadas](#funcionalidades-implementadas)
- [Stack](#stack)
- [Arquitetura](#arquitetura)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Escolhas técnicas](#escolhas-técnicas)
- [Tutorial de execução](#tutorial-de-execução)
- [Testes](#testes)
- [Próximos passos](#próximos-passos)

---

## Visão geral

O projeto implementa um fluxo de atendimento bancário conversacional com:

- **Autenticação** de clientes via CPF e data de nascimento contra `data/clientes.csv`
- **Triagem inteligente** com classificação de intenção e roteamento implícito
- **Operações de crédito** — consulta de limite e solicitação de aumento com validação de score
- **Consulta de câmbio** — cotação de moedas em tempo real via API externa
- **Interface Streamlit** para simulação do atendimento completo
- **Servidor MCP** (Model Context Protocol) desacoplando agentes de IA das operações de dados

Todos os agentes definidos em `requisitos.md` estão implementados.

---

## Funcionalidades implementadas

### Agente de Triagem
- Saudação e coleta de CPF + data de nascimento
- Autenticação via MCP → `AuthService` → `CustomerRepository`
- Controle de **3 tentativas** de autenticação (enforcement no grafo, não só no prompt)
- Classificação de intenção por tags: `CREDIT_LIMIT`, `CREDIT_INCREASE`, `EXCHANGE`, `UNKNOWN`
- Encerramento de sessão via tool `end_conversation`
- Sanitização de entrada contra prompt injection

### Agente de Crédito
- Consulta de limite disponível (`get_credit_limit`)
- Solicitação de aumento de limite (`request_credit_increase`)
- Registro formal em `data/solicitacoes_aumento_limite.csv`
- Validação do score contra `data/score_limite.csv` → status `aprovado` ou `rejeitado`
- Atualização do limite em `data/clientes.csv` quando aprovado
- Oferta de redirecionamento para entrevista de crédito após rejeição (`redirect_to_interview`)

### Agente de Entrevista de Crédito
- Entrevista conversacional estruturada (renda, emprego, despesas, dependentes, dívidas)
- Cálculo de score ponderado (0–1000) conforme fórmula do desafio
- Atualização do score em `data/clientes.csv`
- Redirecionamento de volta ao crédito para nova análise (`redirect_to_credit`)
- Loop completo: crédito → entrevista → crédito

### Agente de Câmbio
- Consulta de cotação em tempo real via [AwesomeAPI](https://docs.awesomeapi.com.br/) (`get_currency_quote`)
- Suporte a USD, EUR, GBP, ARS, CAD, JPY e CHF
- Apresentação de compra, venda, variação do dia e horário da cotação
- Encerramento amigável do atendimento via `end_conversation`

### Infraestrutura transversal
- **Supervisor LangGraph** — handover implícito entre agentes via `target_agent` no state
- **State compartilhado** (`AgentState`) — autenticação, dados do cliente, intenção, status de pedidos
- **Logging estruturado** com mascaramento de PII (CPF, data) em `data/logs/flow.log`
- **91 testes unitários e de integração** cobrindo services, sanitizer, roteamento e fluxos E2E mockados

---

## Stack

### Tecnologias principais

| Camada | Tecnologia |
| --- | --- |
| Linguagem | Python 3.12+ |
| LLM | Amazon Bedrock (Nova Micro) |
| Orquestração | LangChain + LangGraph |
| Protocolo de tools | MCP (stdio) |
| Validação | Pydantic / pydantic-settings |
| Interface | Streamlit |
| Persistência | CSV |
| Testes | pytest |

### Dependências principais

| Biblioteca | Descrição |
| --- | --- |
| `mcp` | Servidor MCP para exposição de ferramentas |
| `langchain` / `langgraph` | Orquestração de agentes e grafos de estado |
| `langchain-aws` | Integração com Amazon Bedrock |
| `boto3` | SDK AWS |
| `pydantic` | Schemas e validação de dados |
| `streamlit` | UI de chat |
| `pytest` | Testes unitários |

Versões pinadas em `requirements.txt`.

---

## Arquitetura

### Fluxo de comunicação

```
Usuário (Streamlit)
  └─► Supervisor (LangGraph)
        ├─► Agente de Triagem
        │     └─► Tools LangChain ──► MCP Server (stdio) ──► Services ──► Repositories (CSV)
        ├─► Agente de Crédito
        │     └─► Tools LangChain ──► MCP Server (stdio) ──► Services ──► Repositories (CSV)
        ├─► Entrevista de Crédito
        │     └─► Tools LangChain ──► MCP Server (stdio) ──► Services ──► Repositories (CSV)
        └─► Agente de Câmbio
              └─► Tools LangChain ──► MCP Server (stdio) ──► ExchangeService ──► AwesomeAPI
```

### Camadas e responsabilidades

| Camada | Responsabilidade |
| --- | --- |
| `agents/` | Grafos LangGraph, prompts e orquestração conversacional |
| `tools/` | Wrappers LangChain que invocam o servidor MCP |
| `mcp_server/` | Exposição das operações como tools MCP |
| `services/` | Regras de negócio, validações e cálculos |
| `repositories/` | Persistência em arquivos CSV |
| `models/` | Contratos Pydantic por domínio |
| `utils/` | Sanitizer, logging, carregamento de prompts |

### Tools MCP disponíveis

| Tool | Service | Descrição |
| --- | --- | --- |
| `authenticate_customer` | `AuthService` | Valida CPF e data de nascimento |
| `classify_intent` | `RoutingService` | Classifica intenção e define agente destino |
| `end_conversation` | `SessionService` | Encerra o atendimento |
| `get_credit_limit` | `CreditService` | Consulta limite e teto permitido |
| `request_credit_increase` | `CreditService` | Solicita aumento com validação de score |
| `redirect_to_interview` | — | Sinaliza redirecionamento para entrevista |
| `submit_credit_interview` | `InterviewService` | Registra entrevista e recalcula score |
| `redirect_to_credit` | — | Sinaliza retorno ao agente de crédito |
| `get_currency_quote` | `ExchangeService` | Consulta cotação via API externa |

### Fluxo de atendimento

```
1. Triagem: saudação → CPF → nascimento → autenticação
2. Triagem: identificação do serviço → classify_intent → target_agent
3. Supervisor: roteia para agente especializado (handover implícito)
4. Crédito: consulta ou solicitação de aumento via tools
5. Se rejeitado: oferta de entrevista → redirect_to_interview
6. Entrevista: coleta dados → submit_credit_interview → redirect_to_credit
7. Crédito: nova análise de aumento com score atualizado
8. Câmbio: consulta de cotação via API → encerramento
9. Encerramento: end_conversation a qualquer momento
```

---

## Estrutura do projeto

```
banco_agil/
├── data/
│   ├── clientes.csv                      # Base de clientes
│   ├── score_limite.csv                  # Tabela score → limite máximo
│   ├── solicitacoes_aumento_limite.csv   # Pedidos de aumento
│   └── logs/flow.log                     # Logs de execução
├── mcp_server/
│   ├── server.py                         # Entry point do servidor MCP
│   └── tools/
│       ├── auth.py
│       ├── credit.py
│       ├── routing.py
│       └── session.py
├── src/
│   ├── agents/
│   │   ├── prompts/                      # Prompts dos agentes e descrições de tools
│   │   ├── state.py                      # AgentState compartilhado
│   │   ├── supervisor.py                 # Roteamento entre agentes
│   │   ├── triage.py                     # Agente de triagem
│   │   ├── credit.py                     # Agente de crédito
│   │   ├── interview.py                  # Agente de entrevista de crédito
│   │   └── exchange.py                   # Agente de câmbio
│   ├── config/
│   │   └── settings.py                   # Variáveis de ambiente (Bedrock)
│   ├── models/                           # Schemas Pydantic
│   ├── repositories/                     # Acesso aos CSVs
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── credit_service.py
│   │   ├── interview_service.py
│   │   ├── exchange_service.py
│   │   ├── routing.py
│   │   └── session_service.py
│   ├── tools/                            # Wrappers LangChain → MCP
│   │   ├── mcp_client.py
│   │   ├── auth.py
│   │   ├── credit.py
│   │   ├── interview.py
│   │   ├── exchange.py
│   │   ├── routing.py
│   │   └── session.py
│   └── utils/                            # Sanitizer, logging, prompt loader
├── tests/
│   ├── conftest.py                       # Fixtures e helpers para testes E2E
│   ├── test_auth_service.py
│   ├── test_credit_service.py
│   ├── test_credit_state.py
│   ├── test_interview_service.py
│   ├── test_interview_state.py
│   ├── test_exchange_service.py
│   ├── test_exchange_state.py
│   ├── test_graph_integration.py
│   ├── test_routing_service.py
│   ├── test_sanitizer.py
│   ├── test_session_service.py
│   └── test_triage_state.py
├── ui/
│   └── streamlit_app.py                  # Interface de chat
├── .env.example
├── requirements.txt
└── requisitos.md                         # Especificação do desafio
```

---

## Escolhas técnicas

- **MCP como fronteira** — agentes não acessam CSV diretamente; tools passam pelo servidor MCP, facilitando manutenção, logs e substituição de fontes de dados.
- **LangGraph com state tipado** — controle determinístico de tentativas de auth, roteamento e status de pedidos, complementando as instruções do LLM.
- **Supervisor pattern** — o cliente fala sempre com o Lican; o supervisor delega internamente sem expor a troca de agente.
- **Classificação de intenção determinística** — `RoutingService` usa regex/keywords testáveis, reduzindo dependência de alucinação do LLM para roteamento.
- **Prompts externos** — arquivos `.md` e `.txt` em `src/agents/prompts/`, carregados via `load_prompt()`.
- **Amazon Bedrock (Nova Micro)** — modelo leve e rápido para fluxos conversacionais com tool calling.

---

## Tutorial de execução

### Pré-requisitos

- Python 3.12+
- Credenciais AWS com acesso ao Amazon Bedrock

### Configuração

```bash
# Clone e entre no diretório do projeto
cd banco_agil

# Crie e ative o ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais AWS e modelo Bedrock
```

### Executar a interface

```bash
streamlit run ui/streamlit_app.py
```

### Dados de teste

| CPF | Nome | Nascimento | Score | Limite |
| --- | --- | --- | --- | --- |
| 12345678901 | Ana Silva | 1990-01-15 | ~630 | R$ 2.500 |
| 98765432100 | Bruno Santos | 1985-11-20 | 250 | R$ 500 |
| 11122233344 | Carlos Oliveira | 1995-07-30 | 850 | R$ 5.000 |

### Exemplo de fluxo

1. Informe CPF e data de nascimento
2. Diga *"qual meu limite?"* → consulta de crédito
3. Diga *"quero aumentar para 3000"* → solicitação (aprovada para Ana Silva)
4. Diga *"qual a cotação do dólar?"* → consulta de câmbio

---

## Testes

```bash
pytest tests/ -v
```

| Arquivo | Cobertura |
| --- | --- |
| `test_auth_service.py` | Autenticação, formatação de CPF/data |
| `test_routing_service.py` | Classificação de intenções |
| `test_session_service.py` | Encerramento de sessão |
| `test_triage_state.py` | Side effects do grafo de triagem |
| `test_credit_service.py` | Consulta, aprovação e rejeição de limite |
| `test_credit_state.py` | Side effects do grafo de crédito |
| `test_interview_service.py` | Cálculo de score e persistência da entrevista |
| `test_interview_state.py` | Side effects do grafo de entrevista |
| `test_exchange_service.py` | Consulta de cotação e normalização de moedas |
| `test_exchange_state.py` | Side effects do grafo de câmbio |
| `test_sanitizer.py` | Proteção contra prompt injection |
| `test_graph_integration.py` | Fluxos E2E com LLM e MCP mockados |

---

## Próximos passos

- [ ] Testes end-to-end com Bedrock real (ambiente de staging)
- [ ] CI/CD com execução automática dos testes
