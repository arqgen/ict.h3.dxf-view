# Notebooks de exploração

Notebooks de EDA usados para embasar decisões de design antes de virar código
em `src/`, não fazendo parte do código final. Dependências ficam em um
dependency-group separado do `pyproject.toml`.

| Notebook                      | Propósito                                                                                                                                     |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `dxf_context_analysis.ipynb`  | Baseline de contexto: o que o `CadModel` preserva dos DXFs de `data/dxf/`, o que não é endereçável, e quanto contexto o acesso global consome |
