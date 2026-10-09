# Dados de teste

| Pasta     | Conteúdo                                                        | Versionado |
| --------- | --------------------------------------------------------------- | ---------- |
| `dxf/`    | Desenhos `.dxf` usados nos testes manuais e nos notebooks       | Não        |
| `labels/` | Gabaritos anotados à mão, para avaliar o que o agente reconhece | Não        |

Nenhuma das duas pastas é versionada (ver `.gitignore`): os `.dxf` por peso e os gabaritos por serem mantidos só localmente. Um clone novo traz este catálogo, mas não os arquivos. Eles estão neste [link](https://drive.google.com/drive/folders/1fP2gHbHQoLeuTxt2OU6oxBB_ECDhL0qN), ainda com os nomes antigos em português; ao baixar, renomeie para o nome da coluna **nome** abaixo.

## Catálogo de DXFs (`dxf/`)

| Nome                       | Contexto                                     | Observações                                                                             |
| -------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------- |
| `hospital_room`            | Layouts                                      | Recorte de uma sala do centro cirúrgico                                                 |
| `hospital_floor`           | Layouts                                      | Recorte de um pavimento do centro cirúrgico                                             |
| `hospital_complete_floor`  | Layouts                                      | Pavimento completo: demolição à esquerda, layout à direita; gabarito em `labels/`       |
| `hospital_surgical_center` | Layouts                                      | Paredes, portas, janelas, mobiliários, ambientes                                        |
| `retail_store_1`           | Zoneamento de ambiente                       | Ambientes são hachuras em `PDF2_Solid Fills`, nomeados por textos em `A-AREA-____-IDEN` |
| `retail_store_2`           | Zoneamento de ambiente                       | Como o `retail_store_1`, com dois pavimentos no mesmo desenho                           |
| `retail_store_3`           | Layout de ambiente                           | Paredes, mobiliários, legenda                                                           |
| `apartment_typical_floor`  | Conversor dwg-rvt / Quantitativos / Terrenos | Um bloco por apartamento, com paredes, portas, janelas e mobiliários dentro             |
| `site_ground_floor_1`      | Conversor dwg-rvt / Quantitativos / Terrenos | Térreo com ruas, terreno, torres e apartamentos                                         |
| `site_ground_floor_2`      | Conversor dwg-rvt / Quantitativos / Terrenos | Térreo com ruas, terreno, topografia, torres e apartamentos                             |
| `multi_floor_towers_1`     | Conversor dwg-rvt / Quantitativos            | Múltiplos pavimentos no mesmo desenho                                                   |
| `multi_floor_towers_2`     | Conversor dwg-rvt / Quantitativos            | Múltiplos pavimentos no mesmo desenho                                                   |
| `pile_layout_1`            | Roteiro de estacas                           | Dados dos blocos de estacas em textos próximos a eles e numa legenda lateral            |
| `pile_layout_2`            | Roteiro de estacas                           | Dados dos blocos de estacas em textos próximos a eles e numa legenda lateral            |
| `land_subdivision`         | Loteamento                                   | Curvas de nível, traçado urbano, vias, lotes                                            |
| `land_subdivision_mesh`    | Loteamento                                   | Curvas de nível, mesh de topografia, traçado urbano, vias, lotes                        |

## Gabaritos (`labels/`)

Cada gabarito leva o nome do DXF que anota, mais um sufixo do que contém.

| Arquivo                              | Conteúdo                                                                                                                   |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `hospital_complete_floor_items.xlsx` | Planilha original, com uma aba por ambiente                                                                                |
| `hospital_complete_floor_items.csv`  | A mesma planilha numa tabela única (uma linha por item x block name), gerada por `experiments/dxf_annotation_parser.ipynb` |
