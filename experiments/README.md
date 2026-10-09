# Notebooks de exploração

Notebooks de EDA usados para embasar decisões de design antes de virar código
em `src/`. Dependências ficam em um dependency-group separado do `pyproject.toml`.

Os DXFs vêm de `data/dxf/` e os gabaritos de `data/labels/`; nome e descrição de
cada arquivo estão no catálogo em [`data/README.md`](../data/README.md).

| Notebook                      | Propósito                                                                                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dxf_context_analysis.ipynb`  | Baseline de contexto: o que o `CadModel` preserva dos DXFs de `data/dxf/`, o que não é endereçável, e quanto contexto o acesso global consome      |
| `dxf_annotation_parser.ipynb` | Converte a planilha de itens por ambiente do `hospital_complete_floor` em `data/labels/hospital_complete_floor_items.csv`, para servir de gabarito |

Cada execução que chama o LLM grava suas saídas em `results/`, com timestamp no
nome. São registros da execução: os arquivos anteriores à renomeação dos DXFs
citam os nomes antigos (`001_room_only` = `hospital_room`,
`003_complete_floor` = `hospital_complete_floor`).
