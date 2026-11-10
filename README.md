# Driftor ASC · pmining

Microsserviço 1 do **Driftor ASC**, entrega 3 de Arquitetura e Soluções Cloud (PUCPR). Recebe event logs de manufatura, liga cada operação do log a uma atividade, monta o grafo do processo com o PM4Py e guarda tudo no **MongoDB Atlas**. A série de duração por trace que ele expõe alimenta a análise de desvios IPDD/ADWIN do [driftor-asc-ipdd](https://github.com/aland3r/driftor-asc-ipdd).

## Na nuvem

| | URL |
|---|---|
| API | https://driftor-asc-pmining.fly.dev |
| Swagger | https://driftor-asc-pmining.fly.dev/docs |
| Imagem | [aland3r/driftor-asc-pmining](https://hub.docker.com/r/aland3r/driftor-asc-pmining) |

O front não chama este serviço direto: o caminho é front → API Management → [BFF](https://github.com/aland3r/driftor-asc-bff) → pmining.

## Rotas

| Método | Rota | Para quê |
|---|---|---|
| `POST` | `/processes` | Cria o processo a partir de um `.xes` ou `.csv` (multipart: `name`, `file`). Volta com status `mapeando` e a atividade sugerida para cada operação. |
| `PUT` | `/processes/{id}/operations` | Grava o mapeamento operação → atividade, gera grafo e variantes. Status `pronto`. |
| `GET` | `/processes` | Lista os processos. |
| `GET` | `/processes/{id}` | Detalhe com operações, grafo (nós com frequência e desempenho) e variantes. |
| `PATCH` | `/processes/{id}` | Renomeia. |
| `DELETE` | `/processes/{id}` | Exclui o processo e os traces e publica `process-deleted` no Service Bus. |
| `GET` | `/processes/{id}/traces?variantId=` | Traces, de todas as variantes ou de uma. |
| `GET` | `/processes/{id}/series?activity=` | Uma observação por trace, em ordem de tempo: duração do trace ou, com `activity`, o tempo de permanência dessa atividade. |
| `GET` / `POST` | `/activities` | Catálogo de atividades usado no mapeamento. |

## Arquitetura

Clean Architecture com fatias verticais:

```
app/
  domain/          entidades e regras puras (variantes, métricas, série); sem bibliotecas externas
  application/     uma pasta por caso de uso, cada uma com seu handler
    upload_process/  map_operations/  list_processes/  get_process/
    rename_process/  delete_process/   get_series/      list_traces/  activities/
    ports.py         interfaces que a infraestrutura implementa
  infrastructure/  MongoDB (pymongo), leitura XES/CSV (pandas + PM4Py), grafo DFG (PM4Py), Service Bus
  api/             FastAPI, contratos HTTP e composição das dependências
```

Os testes de arquitetura (`tests/architecture`) rodam os contratos do [import-linter](.importlinter):

- as camadas só dependem para dentro (api → infrastructure → application → domain);
- o domínio não importa FastAPI, pymongo, pandas, PM4Py nem Azure;
- as fatias de `application/` não importam umas às outras.

Coleções no Mongo (banco `pmining`): `processes` (resumo, operações, grafo, variantes), `traces` (um documento por trace, para não passar do limite de 16 MB por documento) e `activities`.

## Tecnologias

Python 3.12, FastAPI, PM4Py, pandas, pymongo, Azure Service Bus SDK, pytest, mongomock, import-linter, Docker, GitHub Actions, Fly.io.

## Rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                                   # testes unitários e de arquitetura
cp .env.example .env                        # preencha MONGODB_URI
export $(grep -v '^#' .env | xargs)
uvicorn app.api.main:app --reload --port 8080
```

Ou com Docker:

```bash
docker run -p 8080:8080 -e MONGODB_URI="mongodb+srv://..." aland3r/driftor-asc-pmining:v1
```

Sem `SERVICEBUS_CONNECTION`, os eventos só vão para o log.

## Pipeline

A cada push na `main`, o GitHub Actions roda os testes, publica a imagem no Docker Hub (`v1` e o hash do commit) e implanta essa imagem no Fly.io. Secrets usados: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `FLY_API_TOKEN`, `MONGODB_URI`, `SERVICEBUS_CONNECTION`.

## Dados de teste

Os quatro logs sintéticos do artigo do IPDD/ADWIN (`ST_20`, `DR_20`, `DR_MS_20`, `DR_MS_ST_20`), com a série de `Machine_Operating`, δ = 0,002 e tratamento bruto, dão 0, 4, 7 e 9 desvios, como na Tabela 1 do artigo.

## Grupo

- Alander Menezes Arantes de Ávila
- Bernardo Creplive Vieira
- Emanuelle Skolut Jose
- Murilo Regnier Stange
