# Banco Ágil IA

## Índice
- [Objetivo](#objetivo)
- [Stack](#stack)
	- [Tecnologias Principais](#tecnologias-principais)
	- [Dependências e Versões](#dependências-e-versões)
- [Decisão arquitetural](#decisão-arquitetural)
	- [Fluxo base da arquitetura](#fluxo-base-da-arquitetura)

### Objetivo
Criar um agente de de IA para operações bancárias, ele deverá operar com operações de triagem, crédito, entrevistá para atualizar score de crédito, e um agente de câmbio.

## Stack

### Tecnologias Principais

| Camada | Tecnologia |
| --- | --- |
| Linguagem | Python 3.12.3 |
| LLM / Infraestrutura | Amazon Bedrock e Docker |
| Modelo de embeddings utilizado | Titan Embeddings v2 |
| Modelo de raciocínio utilizado | AWS Nova Micro |

### Dependências e Versões

As principais bibliotecas e frameworks de apoio do projeto são controlados e pinados nas seguintes versões:

| Biblioteca | Versão | Descrição |
| --- | --- | --- |
| **mcp** | `1.28.1` | Protocolo para comunicação externa de recursos e ferramentas |
| **langchain** | `1.3.11` | Framework principal de orquestração do LLM |
| **langgraph** | `1.2.7` | Orquestração de grafos de estados e fluxos de conversa (handovers) |
| **boto3** | `1.43.40` | SDK oficial da AWS para conexão e comunicação com o Bedrock |
| **pydantic** | `2.13.4` | Validação de dados de entrada e conversão de schemas de dados |
| **pydantic-settings** | `2.14.2` | Carregamento automático e validação de configurações via variáveis de ambiente |
| **streamlit** | `1.58.0` | Interface web interativa simples para simulação de atendimentos |
| **pandas** | `3.0.3` | Manipulação e leitura estruturada de arquivos CSV (banco de dados) |
| **pytest** | `9.1.1` | Framework de testes unitários e de integração |
| **python-dotenv** | `1.2.2` | Carregamento de variáveis de ambiente do arquivo `.env` |



## Decisão arquitetural

### Fluxo base da arquitetura

```
Usuário
  -> Agent de Triagem
	  -> Tool de Autenticação
		  -> Service de Validação
			  -> Repository CSV
	  -> Tool de Crédito
		  -> Service de Score
			  -> Repository CSV
```

O sistema vai seguir a estrutura MCP para a comunicação dos agentes de IA com as operações a serem realizadas e gravadas nos arquivos CSV. Esse padrão vai ser seguido para desacoplar a lógica dos agentes de IA com as operações de fontes de dados, fazendo com que haja um fluxo mais previsível de repasse da informação entre o services para o agente, facilitando a manutenção e o rastreamento dos logs.

dentro do diretório src teremos os seguintes estrutura de pastas:

```
src/
├── agents/
│   ├── triage.py
│   ├── credit.py
│   ├── interview.py
│   └── exchange.py
├── tools/
│   ├── auth.py
│   ├── credit.py
│   ├── interview.py
│   └── cambio.py
├── services/
│   ├── routing.py
│   └── score.py
├── repositories/
│   └── csv_repository.py
├── models/
│   └── schemas.py
└── config/
	└── settings.py
```
agents: começará com a *triagem*, onde, após a autenticação, ele vai classificar a intenção do usuário por meio de tags pré-definidas.

tools: conforme a recomendação da estrutura MCP, iremos estabelecer as ferramentas que cada agent poderá ter acesso, limitando a atuação de cada uma ao que for necessário para chamar os services específicos e repassar a resposta para o agent geral, evitando alucinação e garantindo uma busca melhor da informação que, de fato, o cliente está buscando.

config: guardará as configurações centrais do projeto, como caminhos dos arquivos CSV, constantes de domínio, parâmetros de execução e eventuais chaves ou variáveis de ambiente necessárias para o funcionamento da aplicação. A ideia é centralizar tudo que for configuração para evitar valores espalhados pelo código e facilitar ajustes futuros.

models: vai funcionar como a camada de contratos da aplicação, definindo os dados e o tipo de cada informação a ser inserida, separada por domínio (score, cliente, etc).

repositories: estabelece a conexão com o CSV diretamente, garantindo uma camada desacoplada da fonte de dados e facilitando a troca para um banco de dados como SQLite, MySQL, Postgree ou outros.

services: aqui vai ficar a regra de negócio, os cálculos, as validações e também as operações mais gerais, separadas por domínio.

tests: camada de testes, aqui irei colocar somente alguns básicos para validar as integrações entre os serviços e para validar se as tratativas contra prompt injection estão bem definidas. Vou tratar uma cobertura de 80% dos cenários principais como resultado positivo, por se tratar somente de um teste.