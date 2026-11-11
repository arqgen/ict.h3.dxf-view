# Queries e resultados esperados

Gerado por `evals/benchmark/documento.py` a partir de `casos.json` e `casos_edicao.json`; não edite à mão. Cada resposta esperada foi calculada por script sobre o AQG, sem LLM. Como usar as tools e medir: [`README.md`](README.md).

## AQGs

37 AQGs nas queries de leitura. As de edição rodam em 29 deles: os arquivos em que a Arqgen reproduz a solução do AQG ao reprocessá-lo sem edição. Nesses, o estado inicial é o AQG reprocessado, que difere do original só em indicadores que o cálculo atual dá diferente.

| Código | Arquivo (`data/aqg/`) | Edição |
| --- | --- | --- |
| A01 | avaliadas/6ab3be2bc0fe97bead8562f5/bom_6ace404e4a7a894b01852f19.json | sim |
| A02 | avaliadas/6ab3be2bc0fe97bead8562f5/otimo_6ace4108cfe0941cdf9a9189.json | sim |
| A03 | avaliadas/6ab3be2bc0fe97bead8562f5/ruim_6ace40534a7a894b01852f1d.json | sim |
| A04 | avaliadas/6ace3b52f382582e76a9ade0/bom_6ace3c8be748be1a355e6769.json | sim |
| A05 | avaliadas/6ace3b52f382582e76a9ade0/otimo_6ace4079bf22db620be742d4.json | sim |
| A06 | avaliadas/6ace3b52f382582e76a9ade0/ruim_6ace3c16d8664cf36a13dbb9.json | sim |
| A07 | avaliadas/6ace446ac33cb2aadbc14a4e/bom_6ace4f3f9aee62f656aae2cc.json | sim |
| A08 | avaliadas/6ace446ac33cb2aadbc14a4e/otimo_6ace52a0bc31d7e3e85c9509.json | sim |
| A09 | avaliadas/6ace446ac33cb2aadbc14a4e/ruim_6ace4ea8ecd8aeaf968b312c.json | sim |
| A10 | avaliadas/6ace63aa90f3c13f46fb1b59/bom_6ace64863afd82bf6be93e16.json | sim |
| A11 | avaliadas/6ace63aa90f3c13f46fb1b59/otimo_6ace64da8d16ae86ca3419e5.json | sim |
| A12 | avaliadas/6ace63aa90f3c13f46fb1b59/ruim_6ace648d563a33090fea89d6.json | sim |
| A13 | avaliadas/6ace7adc2c4a60a1ac21c32d/bom_6ace7b93445b3a60fcb6162b.json | sim |
| A14 | avaliadas/6ace7adc2c4a60a1ac21c32d/otimo_6ace84f467fab4d8049d1394.json | sim |
| A15 | avaliadas/6ace7adc2c4a60a1ac21c32d/ruim_6ace7f0d246ca4a63fa193fd.json | sim |
| A16 | favoritadas/6842c89845e64a9f238fba3c_6842c996181cf815481d1967.json | — |
| A17 | favoritadas/694081cf9e15b2d9f935ad16_697c9bb91c2e52422d15e48f.json | — |
| A18 | favoritadas/696517ed8049fdc9f3b0f6ad_69651a149a57a850baccee44.json | — |
| A19 | favoritadas/69b1a6d4d985c5ddbecac196_69b1aab76d16be251b892e7b.json | — |
| A20 | favoritadas/6a4c017db840fc776e4443b0_6a4c0b25ded0ef35ff62c408.json | — |
| A21 | favoritadas/6a75cb2ec909fd8f7cd3e8d8_6a75e11668d34b45e508271f.json | — |
| A22 | favoritadas/6aa1c1fa5f7ffad5748a9e37_6aa1c48ce8e1d2a9eeb19d5e.json | — |
| A23 | favoritadas/6aaaa498cf7264229c24d353_6aaaa6467c85d637d8f6555a.json | — |
| A24 | favoritadas/6abab05295f499e81abeca64_6abd57caa4c6bcd7c7e56699.json | sim |
| A25 | solucoes-18x/6ac4005d0ee572fb8b3682a4_6ac7a6d22f5d64608d0d963f.json | sim |
| A26 | solucoes-18x/6ac54d9821b6952439b9de3c_6ac8f06a32f709e0b0d6c953.json | sim |
| A27 | solucoes-18x/6ac54d9821b6952439b9de3c_6ad8f29642ad5c782aadd00a.json | sim |
| A28 | solucoes-18x/6ac69a025e9b012676aa8f2c_6ac69c1ff14d8f2dd753116f.json | sim |
| A29 | solucoes-18x/6acfdf3acf9cad1f1236fc41_6acfe04e4295c85e1a106da7.json | sim |
| A30 | solucoes-18x/6ad0caf35d1b1c2a3ec62673_6ad0cc078ff111a2aa5eea2e.json | sim |
| A31 | solucoes-18x/6ad0e13953c4cf49afd41c14_6ad0e4522f99b87884ef930d.json | sim |
| A32 | solucoes-18x/6ad1250a0fb05d2c82541045_6ad126d1d20587f9e6443003.json | sim |
| A33 | solucoes-18x/6ad294efa4c7ae18390b4e27_6ad2976b402f900729d7a78b.json | sim |
| A34 | solucoes-18x/6ad5e108b4865d8d943e406d_6ad5e8c4ef1079329b7e9b0d.json | sim |
| A35 | solucoes-18x/6ad60779486e1091c195e188_6ad60861cf7933c2164b0fa5.json | sim |
| A36 | solucoes-18x/6ae0eaf96dd7809f17f6a2e3_6ae0ebe491b9dd2b0e000ea9.json | sim |
| A37 | solucoes-18x/6ae0eaf96dd7809f17f6a2e3_6ae22adef5c82d8e2a1c08af.json | sim |

## Leitura

Status `não se aplica`: a pergunta não faz sentido no arquivo, e o caso fica fora da medição.

### L1 — Quantas torres tem a solução?

**Conferência:** Instâncias de família de torre em `solution.placed_objects`; confere com `TotalDeTorres` dos `outputs`.

37 com resposta, 0 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | 4 |
| A02 | 12 |
| A03 | 3 |
| A04 | 3 |
| A05 | 2 |
| A06 | 2 |
| A07 | 2 |
| A08 | 3 |
| A09 | 1 |
| A10 | 4 |
| A11 | 10 |
| A12 | 1 |
| A13 | 1 |
| A14 | 3 |
| A15 | 1 |
| A16 | 4 |
| A17 | 2 |
| A18 | 6 |
| A19 | 2 |
| A20 | 3 |
| A21 | 3 |
| A22 | 3 |
| A23 | 2 |
| A24 | 1 |
| A25 | 12 |
| A26 | 5 |
| A27 | 5 |
| A28 | 6 |
| A29 | 10 |
| A30 | 7 |
| A31 | 2 |
| A32 | 6 |
| A33 | 2 |
| A34 | 3 |
| A35 | 6 |
| A36 | 9 |
| A37 | 9 |

### L2 — Qual o CA máximo exigido e o projetado?

**Conferência:** `CAMaximoExigido` dos inputs do terreno e `CAProjetado` dos `outputs`.

37 com resposta, 0 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | CAMaximoExigido: 5; CAProjetado: 2,08 |
| A02 | CAMaximoExigido: 5; CAProjetado: 4,99 |
| A03 | CAMaximoExigido: 5; CAProjetado: 0,15 |
| A04 | CAMaximoExigido: 3; CAProjetado: 2,56 |
| A05 | CAMaximoExigido: 4; CAProjetado: 3,98 |
| A06 | CAMaximoExigido: 3; CAProjetado: 1,09 |
| A07 | CAMaximoExigido: 3; CAProjetado: 0,79 |
| A08 | CAMaximoExigido: 3; CAProjetado: 1,11 |
| A09 | CAMaximoExigido: 3; CAProjetado: 0,37 |
| A10 | CAMaximoExigido: 2,25; CAProjetado: 0,5 |
| A11 | CAMaximoExigido: 2,25; CAProjetado: 1,27 |
| A12 | CAMaximoExigido: 2,25; CAProjetado: 0,11 |
| A13 | CAMaximoExigido: 2,9; CAProjetado: 0,97 |
| A14 | CAMaximoExigido: 2,9; CAProjetado: 1,78 |
| A15 | CAMaximoExigido: 2,9; CAProjetado: 0,23 |
| A16 | CAMaximoExigido: 6; CAProjetado: 3,12 |
| A17 | CAMaximoExigido: 5; CAProjetado: 4,6 |
| A18 | CAMaximoExigido: 5; CAProjetado: 1,67 |
| A19 | CAMaximoExigido: 5; CAProjetado: 0,89 |
| A20 | CAMaximoExigido: 4; CAProjetado: 1,42 |
| A21 | CAMaximoExigido: 4; CAProjetado: 1,68 |
| A22 | CAMaximoExigido: 8; CAProjetado: 3,88 |
| A23 | CAMaximoExigido: 8; CAProjetado: 4,58 |
| A24 | CAMaximoExigido: 4; CAProjetado: 1,1 |
| A25 | CAMaximoExigido: 2; CAProjetado: 0,46 |
| A26 | CAMaximoExigido: 2; CAProjetado: 0,72 |
| A27 | CAMaximoExigido: 2; CAProjetado: 0,72 |
| A28 | CAMaximoExigido: 2; CAProjetado: 1,22 |
| A29 | CAMaximoExigido: 2; CAProjetado: 0,4 |
| A30 | CAMaximoExigido: 2,5; CAProjetado: 0,68 |
| A31 | CAMaximoExigido: 4; CAProjetado: 1,86 |
| A32 | CAMaximoExigido: 2; CAProjetado: 1,94 |
| A33 | CAMaximoExigido: 2; CAProjetado: 0,88 |
| A34 | CAMaximoExigido: 3,5; CAProjetado: 1,1 |
| A35 | CAMaximoExigido: 2,5; CAProjetado: 0,71 |
| A36 | CAMaximoExigido: 5; CAProjetado: 1,51 |
| A37 | CAMaximoExigido: 5; CAProjetado: 1,51 |

### L3 — Quantas vagas foram desenhadas?

**Conferência:** Instâncias de família de vaga em `solution.placed_objects`.

37 com resposta, 0 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | 0 |
| A02 | 0 |
| A03 | 0 |
| A04 | 0 |
| A05 | 0 |
| A06 | 0 |
| A07 | 253 |
| A08 | 353 |
| A09 | 118 |
| A10 | 147 |
| A11 | 375 |
| A12 | 33 |
| A13 | 80 |
| A14 | 100 |
| A15 | 20 |
| A16 | 0 |
| A17 | 0 |
| A18 | 573 |
| A19 | 149 |
| A20 | 363 |
| A21 | 290 |
| A22 | 0 |
| A23 | 0 |
| A24 | 219 |
| A25 | 192 |
| A26 | 320 |
| A27 | 346 |
| A28 | 515 |
| A29 | 169 |
| A30 | 480 |
| A31 | 152 |
| A32 | 262 |
| A33 | 154 |
| A34 | 706 |
| A35 | 504 |
| A36 | 930 |
| A37 | 932 |

### L4 — Qual a família da torre mais próxima da frente e quantos pavimentos ela tem?

**Conferência:** A torre cujo pavimento-tipo desenhado fica mais perto da frente (layer `AQG_FRENTE`), borda a borda; o label da família e `total_pavimentos` das propriedades dela.

34 com resposta, 3 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | familia: U/24; total_pavimentos: 23 |
| A02 | familia: I/16; total_pavimentos: 18 |
| A03 | familia: I/27; total_pavimentos: 3 |
| A04 | familia: I/13; total_pavimentos: 10 |
| A05 | familia: I/10; total_pavimentos: 23 |
| A06 | familia: I/9; total_pavimentos: 8 |
| A07 | familia: Casamar 8PP; total_pavimentos: 15 |
| A08 | familia: Casamar 8PP; total_pavimentos: 14 |
| A09 | familia: Casamar 8PP; total_pavimentos: 14 |
| A10 | familia: I/15; total_pavimentos: 10 |
| A11 | familia: I/15; total_pavimentos: 10 |
| A12 | familia: I/13; total_pavimentos: 10 |
| A13 | familia: L/20; total_pavimentos: 4 |
| A14 | não se aplica: empate na distância à frente |
| A15 | familia: I/5; total_pavimentos: 4 |
| A16 | familia: I/12/16pav; total_pavimentos: 16 |
| A17 | familia: I/25; total_pavimentos: 28 |
| A18 | não se aplica: empate na distância à frente |
| A19 | familia: PR_V08_8x8; total_pavimentos: 12 |
| A20 | familia: B-2QSV-8PP; total_pavimentos: 14 |
| A21 | familia: ESPANHOL - ESCADA ENCLAUSURADA; total_pavimentos: 17 |
| A22 | familia: I/11; total_pavimentos: 10 |
| A23 | familia: L/11; total_pavimentos: 17 |
| A24 | familia: I/8; total_pavimentos: 31 |
| A25 | familia: Porto 4PP; total_pavimentos: 4 |
| A26 | familia: Casamar 8PP; total_pavimentos: 8 |
| A27 | familia: Casamar 8PP; total_pavimentos: 8 |
| A28 | não se aplica: empate na distância à frente |
| A29 | familia: Porto 4PP; total_pavimentos: 4 |
| A30 | familia: TORRE ESTÁTICA 12PP; total_pavimentos: 6 |
| A31 | familia: I/12; total_pavimentos: 14 |
| A32 | familia: TORRE ESTÁTICA 8PP; total_pavimentos: 14 |
| A33 | familia: I/25; total_pavimentos: 5 |
| A34 | familia: I/29; total_pavimentos: 11 |
| A35 | familia: TORRE ESTÁTICA 12PP; total_pavimentos: 6 |
| A36 | familia: TORRE ESTÁTICA 8PP; total_pavimentos: 16 |
| A37 | familia: TORRE ESTÁTICA 8PP; total_pavimentos: 16 |

### L5 — Quantas unidades há de cada tipologia?

**Conferência:** `UnidadesPorTipologia` dos `outputs`.

37 com resposta, 0 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | /area/apartamento/1QV/31_45: 2112 |
| A02 | /area/apartamento/1QV/31_45: 5063 |
| A03 | /area/apartamento/1QV/31_45: 162 |
| A04 | /area/apartamento/UH PONTA 35,35m²-2Q-V/e3b281ea-f76f-4000-b298-277c1f1ae8b8: 116; /area/apartamento/UH MEIO-32,75m²-2Q-V/079adb84-21c2-4c62-ad40-6b1509c0cd46: 299 |
| A05 | /area/apartamento/UH PONTA 35,35m²-2Q-V/e3b281ea-f76f-4000-b298-277c1f1ae8b8: 184; /area/apartamento/UH MEIO-32,75m²-2Q-V/079adb84-21c2-4c62-ad40-6b1509c0cd46: 460 |
| A06 | /area/apartamento/UH PONTA 35,35m²-2Q-V/e3b281ea-f76f-4000-b298-277c1f1ae8b8: 64; /area/apartamento/UH MEIO-32,75m²-2Q-V/079adb84-21c2-4c62-ad40-6b1509c0cd46: 112 |
| A07 | /area/apartamento/Casamar 8PP: 240 |
| A08 | /area/apartamento/Casamar 8PP: 336 |
| A09 | /area/apartamento/Casamar 8PP: 112 |
| A10 | /area/apartamento/UH MEIO-32,75m²-2Q-V/079adb84-21c2-4c62-ad40-6b1509c0cd46: 440; /area/apartamento/UH PONTA 35,35m²-2Q-V/e3b281ea-f76f-4000-b298-277c1f1ae8b8: 160 |
| A11 | /area/apartamento/UH MEIO-32,75m²-2Q-V/079adb84-21c2-4c62-ad40-6b1509c0cd46: 1100; /area/apartamento/UH PONTA 35,35m²-2Q-V/e3b281ea-f76f-4000-b298-277c1f1ae8b8: 400 |
| A12 | /area/apartamento/UH MEIO-32,75m²-2Q-V/079adb84-21c2-4c62-ad40-6b1509c0cd46: 90; /area/apartamento/UH PONTA 35,35m²-2Q-V/e3b281ea-f76f-4000-b298-277c1f1ae8b8: 40 |
| A13 | /area/apartamento/2 Quartos com Sacada - Ponta/b11946a2-8f3f-4f6c-b3a4-9839e35e3522: 16; /area/apartamento/2 Quartos - Meio/026435de-2c8b-462b-ab97-87ae8acd974e: 64 |
| A14 | /area/apartamento/2 Quartos - Meio/026435de-2c8b-462b-ab97-87ae8acd974e: 85; /area/apartamento/2 Quartos com Sacada - Ponta/b11946a2-8f3f-4f6c-b3a4-9839e35e3522: 60 |
| A15 | /area/apartamento/2 Quartos com Sacada - Ponta/b11946a2-8f3f-4f6c-b3a4-9839e35e3522: 16; /area/apartamento/2 Quartos - Meio/026435de-2c8b-462b-ab97-87ae8acd974e: 4 |
| A16 | /area/apartamento/2qv/41: 240; /area/apartamento/2q/31: 690 |
| A17 | /area/apartamento/1q/27_97: 405; /area/apartamento/e/23_48: 972 |
| A18 | /area/apartamento/2qs/43_78: 288; /area/apartamento/1q/27_97: 288 |
| A19 | /area/apartamento/PR-V08-8x8: 176 |
| A20 | /area/apartamento/B-2QSV-8PP: 336 |
| A21 | /area/apartamento/ESPANHOL - ESCADA ENCLAUSURADA: 360 |
| A22 | /area/apartamento/Capital - 2 Dorms 33_46m² - Meio/75bfc12f-3560-41d5-b2b8-7b6475f63839: 90; /area/apartamento/Capital - 1 Dorm 28_33m² - Meio/13a8fa38-775d-44bd-bb84-e182c9377019: 240 |
| A23 | /area/apartamento/Capital - 1 Dorm 28_33m² - Meio/13a8fa38-775d-44bd-bb84-e182c9377019: 340; /area/apartamento/Capital - 2 Dorms 33_46m² - Meio/75bfc12f-3560-41d5-b2b8-7b6475f63839: 85 |
| A24 | /area/apartamento/1q/27_97: 240 |
| A25 | /area/apartamento/Porto 4PP: 192 |
| A26 | /area/apartamento/Casamar 8PP: 320 |
| A27 | /area/apartamento/Casamar 8PP: 320 |
| A28 | /area/apartamento/8pp_aqg: 624 |
| A29 | /area/apartamento/Porto 4PP: 160 |
| A30 | /area/apartamento/16pp_aqg: 240; /area/apartamento/10pp_aqg: 240 |
| A31 | /area/apartamento/2qs/43_78: 156; /area/apartamento/2q/40_71: 156 |
| A32 | /area/apartamento/8pp_aqg: 624 |
| A33 | /area/apartamento/2q/40_71: 70; /area/apartamento/1q/27_97: 100 |
| A34 | /area/apartamento/1QV/31_45: 870 |
| A35 | /area/apartamento/16pp_aqg: 288; /area/apartamento/10pp_aqg: 216 |
| A36 | /area/apartamento/8pp_aqg: 1080 |
| A37 | /area/apartamento/8pp_aqg: 1080 |

### L6 — Qual a área do terreno e a área útil?

**Conferência:** `AreaDoTerreno` e `AreaUtil` do `processed_info` do terreno.

37 com resposta, 0 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | AreaDoTerreno: 30.327,22; AreaUtil: 30.327,22 |
| A02 | AreaDoTerreno: 30.327,22; AreaUtil: 30.327,22 |
| A03 | AreaDoTerreno: 30.327,22; AreaUtil: 30.327,22 |
| A04 | AreaDoTerreno: 5.179,11; AreaUtil: 4805 |
| A05 | AreaDoTerreno: 5.179,11; AreaUtil: 4805 |
| A06 | AreaDoTerreno: 5.179,11; AreaUtil: 4805 |
| A07 | AreaDoTerreno: 13.182,03; AreaUtil: 13.182,03 |
| A08 | AreaDoTerreno: 13.182,03; AreaUtil: 13.182,03 |
| A09 | AreaDoTerreno: 13.182,03; AreaUtil: 13.182,03 |
| A10 | AreaDoTerreno: 26.904,52; AreaUtil: 34940 |
| A11 | AreaDoTerreno: 26.904,52; AreaUtil: 34940 |
| A12 | AreaDoTerreno: 26.904,52; AreaUtil: 34940 |
| A13 | AreaDoTerreno: 7.253,03; AreaUtil: 7.253,04 |
| A14 | AreaDoTerreno: 7.253,03; AreaUtil: 7.253,04 |
| A15 | AreaDoTerreno: 7.253,03; AreaUtil: 7.253,04 |
| A16 | AreaDoTerreno: 9.566,06; AreaUtil: 9.566,06 |
| A17 | AreaDoTerreno: 7.581,8; AreaUtil: 5.892,51 |
| A18 | AreaDoTerreno: 16.380,59; AreaUtil: 16.380,59 |
| A19 | AreaDoTerreno: 7.581,8; AreaUtil: 5.892,51 |
| A20 | AreaDoTerreno: 12.019,37; AreaUtil: 12.019,37 |
| A21 | AreaDoTerreno: 9.582,2; AreaUtil: 9.582,2 |
| A22 | AreaDoTerreno: 2.342,12; AreaUtil: 2.342,12 |
| A23 | AreaDoTerreno: 2.526,38; AreaUtil: 2.526,38 |
| A24 | AreaDoTerreno: 6.067,84; AreaUtil: 6.067,84 |
| A25 | AreaDoTerreno: 16.689,88; AreaUtil: 16.689,88 |
| A26 | AreaDoTerreno: 19.317,02; AreaUtil: 19.317,02 |
| A27 | AreaDoTerreno: 19.317,02; AreaUtil: 19.317,02 |
| A28 | AreaDoTerreno: 21.765,05; AreaUtil: 21.765,05 |
| A29 | AreaDoTerreno: 15.833,51; AreaUtil: 15.833,51 |
| A30 | AreaDoTerreno: 28.337,62; AreaUtil: 25.886,54 |
| A31 | AreaDoTerreno: 7.055,62; AreaUtil: 7.055,62 |
| A32 | AreaDoTerreno: 13.687,88; AreaUtil: 13.687,88 |
| A33 | AreaDoTerreno: 6.711,97; AreaUtil: 6.711,97 |
| A34 | AreaDoTerreno: 23.585,63; AreaUtil: 23.585,63 |
| A35 | AreaDoTerreno: 28.337,62; AreaUtil: 24.723,57 |
| A36 | AreaDoTerreno: 30.414,03; AreaUtil: 30.414,03 |
| A37 | AreaDoTerreno: 30.414,03; AreaUtil: 30.414,03 |

### L7 — Que elementos o terreno tem?

**Conferência:** Layers dos elementos do terreno (`site.elements`).

37 com resposta, 0 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A02 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A03 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A04 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A05 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A06 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A07 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A08 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A09 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A10 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A11 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A12 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A13 | AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A14 | AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A15 | AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A16 | AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A17 | AQG_ACESSO, AQG_APP, AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO, AQG_PORTARIA |
| A18 | AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A19 | AQG_ACESSO, AQG_APP, AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO, AQG_PORTARIA |
| A20 | AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A21 | AQG_ACESSO, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A22 | AQG_ACESSO, AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A23 | AQG_ACESSO, AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A24 | AQG_ACESSO, AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A25 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A26 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A27 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A28 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A29 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A30 | AQG_APP, AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A31 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_OFFSET, AQG_PERIMETRO |
| A32 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A33 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A34 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A35 | AQG_APP, AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A36 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |
| A37 | AQG_CURVA_DE_NIVEL_INTERMEDIARIA, AQG_CURVA_DE_NIVEL_MESTRA, AQG_FRENTE, AQG_FUNDOS, AQG_OFFSET, AQG_PERIMETRO |

### L8 — Qual o afastamento exigido entre as torres?

**Conferência:** `AfastamentoProjetado.entre_blocos` dos `outputs`.

37 com resposta, 0 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | 6 |
| A02 | 6 |
| A03 | 6 |
| A04 | 6 |
| A05 | 11,36 |
| A06 | 6 |
| A07 | 9 |
| A08 | 8,4 |
| A09 | 9 |
| A10 | 6 |
| A11 | 6 |
| A12 | 6 |
| A13 | 6 |
| A14 | 6 |
| A15 | 6 |
| A16 | 7,39 |
| A17 | 8 |
| A18 | 5,16 |
| A19 | 6 |
| A20 | 16 |
| A21 | 0,5 |
| A22 | 4,11 |
| A23 | 7,78 |
| A24 | 6 |
| A25 | 6 |
| A26 | 0,2 |
| A27 | 0,2 |
| A28 | 6 |
| A29 | 0,2 |
| A30 | 6 |
| A31 | 7,2 |
| A32 | 9,71 |
| A33 | 6 |
| A34 | 6 |
| A35 | 6 |
| A36 | 10 |
| A37 | 10 |

### A1 — Quantas unidades este terreno comporta pelo CA, mantido o mix desta solução?

**Conferência:** piso(`AreaDoTerreno` × `CAMaximoExigido` ÷ área computável por unidade), com a área por unidade da própria solução: `AreaTotalConstruidaComputavel` ÷ `TotalDeUnidades`. A base é `AreaDeMatricula` quando `AreaBaseDeCalculo` manda.

37 com resposta, 0 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | 5072 |
| A02 | 5072 |
| A03 | 5072 |
| A04 | 485 |
| A05 | 646 |
| A06 | 482 |
| A07 | 901 |
| A08 | 901 |
| A09 | 901 |
| A10 | 2649 |
| A11 | 2649 |
| A12 | 2640 |
| A13 | 238 |
| A14 | 235 |
| A15 | 244 |
| A16 | 1783 |
| A17 | 1494 |
| A18 | 1714 |
| A19 | 988 |
| A20 | 944 |
| A21 | 855 |
| A22 | 679 |
| A23 | 741 |
| A24 | 867 |
| A25 | 832 |
| A26 | 880 |
| A27 | 880 |
| A28 | 1021 |
| A29 | 789 |
| A30 | 1758 |
| A31 | 668 |
| A32 | 642 |
| A33 | 384 |
| A34 | 2761 |
| A35 | 1767 |
| A36 | 3566 |
| A37 | 3566 |

### B2 — Quanto do terreno vai para o carro?

**Conferência:** `EstacionamentoProjetado` (= `ViarioProjetado` + `VagasProjetadas`) e `ProjecaoTorres` dos `outputs`: área (m²) e percentual do terreno.

27 com resposta, 10 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | não se aplica: sem vagas |
| A02 | não se aplica: sem vagas |
| A03 | não se aplica: sem vagas |
| A04 | não se aplica: sem vagas |
| A05 | não se aplica: sem vagas |
| A06 | não se aplica: sem vagas |
| A07 | EstacionamentoProjetado: (area: 5.374,6; percentual: 40,76); ViarioProjetado: (area: 2.232,78; percentual: 16,93); VagasProjetadas: (area: 3.141,82; percentual: 23,83); ProjecaoTorres: (area: 994,4; percentual: 7,54) |
| A08 | EstacionamentoProjetado: (area: 7.585,34; percentual: 57,53); ViarioProjetado: (area: 3.204,29; percentual: 24,3); VagasProjetadas: (area: 4.381,05; percentual: 33,23); ProjecaoTorres: (area: 1.491,6; percentual: 11,31) |
| A09 | EstacionamentoProjetado: (area: 2.502,68; percentual: 18,97); ViarioProjetado: (area: 1.035,84; percentual: 7,85); VagasProjetadas: (area: 1.466,85; percentual: 11,12); ProjecaoTorres: (area: 497,2; percentual: 3,77) |
| A10 | EstacionamentoProjetado: (area: 2.653,52; percentual: 7,58); ViarioProjetado: (area: 816,02; percentual: 2,33); VagasProjetadas: (area: 1.837,5; percentual: 5,25); ProjecaoTorres: (area: 2.480,31; percentual: 7,09) |
| A11 | EstacionamentoProjetado: (area: 7.344,52; percentual: 21,01); ViarioProjetado: (area: 2.657,02; percentual: 7,6); VagasProjetadas: (area: 4.687,5; percentual: 13,41); ProjecaoTorres: (area: 6.200,79; percentual: 17,74) |
| A12 | EstacionamentoProjetado: (area: 809,61; percentual: 2,3); ViarioProjetado: (area: 397,11; percentual: 1,13); VagasProjetadas: (area: 412,5; percentual: 1,18); ProjecaoTorres: (area: 537,49; percentual: 1,53) |
| A13 | EstacionamentoProjetado: (area: 1.615,51; percentual: 22,26); ViarioProjetado: (area: 607,51; percentual: 8,37); VagasProjetadas: (area: 1008; percentual: 13,89); ProjecaoTorres: (area: 1.787,31; percentual: 24,64) |
| A14 | EstacionamentoProjetado: (area: 2.203,05; percentual: 30,36); ViarioProjetado: (area: 931,05; percentual: 12,83); VagasProjetadas: (area: 1272; percentual: 17,53); ProjecaoTorres: (area: 2.630,84; percentual: 36,27) |
| A15 | EstacionamentoProjetado: (area: 765,88; percentual: 10,55); ViarioProjetado: (area: 513,88; percentual: 7,08); VagasProjetadas: (area: 252; percentual: 3,47); ProjecaoTorres: (area: 438,95; percentual: 6,05) |
| A16 | não se aplica: sem vagas |
| A17 | não se aplica: sem vagas |
| A18 | EstacionamentoProjetado: (area: 10.588,76; percentual: 64,63); ViarioProjetado: (area: 3.426,26; percentual: 20,91); VagasProjetadas: (area: 7.162,5; percentual: 43,72); ProjecaoTorres: (area: 2.292,83; percentual: 13,99) |
| A19 | EstacionamentoProjetado: (area: 2.821,71; percentual: 37,21); ViarioProjetado: (area: 1.279,57; percentual: 16,87); VagasProjetadas: (area: 1.542,14; percentual: 20,34); ProjecaoTorres: (area: 848,52; percentual: 11,19) |
| A20 | EstacionamentoProjetado: (area: 7.915,68; percentual: 65,84); ViarioProjetado: (area: 3.741,18; percentual: 31,12); VagasProjetadas: (area: 4.174,5; percentual: 34,73); ProjecaoTorres: (area: 1.237,77; percentual: 10,29) |
| A21 | EstacionamentoProjetado: (area: 6.023,84; percentual: 62,86); ViarioProjetado: (area: 2.683,05; percentual: 28); VagasProjetadas: (area: 3.340,79; percentual: 34,86); ProjecaoTorres: (area: 1.312,8; percentual: 13,7) |
| A22 | não se aplica: sem vagas |
| A23 | não se aplica: sem vagas |
| A24 | EstacionamentoProjetado: (area: 4.507,39; percentual: 74,27); ViarioProjetado: (area: 1.769,89; percentual: 29,16); VagasProjetadas: (area: 2.737,5; percentual: 45,11); ProjecaoTorres: (area: 334,66; percentual: 5,51) |
| A25 | EstacionamentoProjetado: (area: 5.363,81; percentual: 32,11); ViarioProjetado: (area: 2.963,81; percentual: 17,75); VagasProjetadas: (area: 2400; percentual: 14,37); ProjecaoTorres: (area: 2.214,83; percentual: 13,27) |
| A26 | EstacionamentoProjetado: (area: 6.995,73; percentual: 36,2); ViarioProjetado: (area: 2.979,73; percentual: 15,42); VagasProjetadas: (area: 4016; percentual: 20,78); ProjecaoTorres: (area: 2486; percentual: 12,86) |
| A27 | EstacionamentoProjetado: (area: 7.861,38; percentual: 40,68); ViarioProjetado: (area: 3.536,38; percentual: 18,3); VagasProjetadas: (area: 4325; percentual: 22,38); ProjecaoTorres: (area: 2486; percentual: 12,86) |
| A28 | EstacionamentoProjetado: (area: 13.464,92; percentual: 61,84); ViarioProjetado: (area: 7.799,92; percentual: 35,83); VagasProjetadas: (area: 5665; percentual: 26,02); ProjecaoTorres: (area: 2.659,38; percentual: 12,21) |
| A29 | EstacionamentoProjetado: (area: 3.844,6; percentual: 24,27); ViarioProjetado: (area: 1.732,1; percentual: 10,93); VagasProjetadas: (area: 2.112,5; percentual: 13,34); ProjecaoTorres: (area: 1.845,69; percentual: 11,65) |
| A30 | EstacionamentoProjetado: (area: 8.552,27; percentual: 30,17); ViarioProjetado: (area: 3.886,67; percentual: 13,71); VagasProjetadas: (area: 4.665,6; percentual: 16,46); ProjecaoTorres: (area: 4.325,3; percentual: 15,26) |
| A31 | EstacionamentoProjetado: (area: 3.087,89; percentual: 43,75); ViarioProjetado: (area: 1.362,91; percentual: 19,31); VagasProjetadas: (area: 1.724,98; percentual: 24,44); ProjecaoTorres: (area: 1.314,68; percentual: 18,63) |
| A32 | EstacionamentoProjetado: (area: 5.224,21; percentual: 38,15); ViarioProjetado: (area: 2.342,21; percentual: 17,11); VagasProjetadas: (area: 2882; percentual: 21,05); ProjecaoTorres: (area: 2.659,38; percentual: 19,42) |
| A33 | EstacionamentoProjetado: (area: 3.084,52; percentual: 45,95); ViarioProjetado: (area: 1.159,52; percentual: 17,27); VagasProjetadas: (area: 1925; percentual: 28,68); ProjecaoTorres: (area: 1.355,44; percentual: 20,19) |
| A34 | EstacionamentoProjetado: (area: 13.042,35; percentual: 55,28); ViarioProjetado: (area: 4.217,35; percentual: 17,88); VagasProjetadas: (area: 8825; percentual: 37,41); ProjecaoTorres: (area: 3.304,32; percentual: 14) |
| A35 | EstacionamentoProjetado: (area: 8.450,68; percentual: 29,81); ViarioProjetado: (area: 3.552,89; percentual: 12,53); VagasProjetadas: (area: 4.897,79; percentual: 17,28); ProjecaoTorres: (area: 3.759,99; percentual: 13,26) |
| A36 | EstacionamentoProjetado: (area: 19.499,61; percentual: 64,11); ViarioProjetado: (area: 7.874,61; percentual: 25,89); VagasProjetadas: (area: 11625; percentual: 38,22); ProjecaoTorres: (area: 3.989,07; percentual: 13,11) |
| A37 | EstacionamentoProjetado: (area: 19.157,05; percentual: 62,98); ViarioProjetado: (area: 7.507,05; percentual: 24,68); VagasProjetadas: (area: 11650; percentual: 38,3); ProjecaoTorres: (area: 3.989,07; percentual: 13,11) |

### B5 — Qual a distância de carro da portaria a cada torre?

**Conferência:** O AQG não guarda a rede viária: a Arqgen a regerou para cada arquivo, e a resposta é o menor caminho nela, do acesso da portaria ao de cada torre (m). A tool `caminho` faz esse cálculo.

18 com resposta, 19 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | não se aplica: sem estacionamento |
| A02 | não se aplica: sem estacionamento |
| A03 | não se aplica: sem estacionamento |
| A04 | não se aplica: sem estacionamento |
| A05 | não se aplica: sem estacionamento |
| A06 | não se aplica: sem estacionamento |
| A07 | p255: 37,65; p256: 37,65 |
| A08 | p355: 0; p356: 59,63; p357: 0 |
| A09 | p120: 82,8 |
| A10 | p149: 0; p150: 53,69; p151: 53,69; p152: 53,69 |
| A11 | não se aplica: sem portaria |
| A12 | p35: 92,61 |
| A13 | p1: 2,9 |
| A14 | p1: 9,09; p2: 0; p3: inalcançável |
| A15 | p1: 32,3 |
| A16 | não se aplica: arquivo fora das edições |
| A17 | não se aplica: arquivo fora das edições |
| A18 | não se aplica: arquivo fora das edições |
| A19 | não se aplica: arquivo fora das edições |
| A20 | não se aplica: arquivo fora das edições |
| A21 | não se aplica: arquivo fora das edições |
| A22 | não se aplica: arquivo fora das edições |
| A23 | não se aplica: arquivo fora das edições |
| A24 | p221: 2,47 |
| A25 | p194: 22,29; p195: 22,29; p196: 46,42; p197: 72,44; p198: 96,46; p199: 121,48; p200: 145,49; p201: 12,85; p202: 70,92; p203: 46,91; p204: 95,92; p205: 135,28 |
| A26 | p322: 160,67; p323: 93,48; p324: 160,67; p325: 93,48; p326: 26,3 |
| A27 | p348: 172,89; p349: 105,7; p350: 38,51; p351: 105,7; p352: 38,51 |
| A28 | não se aplica: sem portaria |
| A29 | p171: 165,52; p172: 138,22; p173: 138,22; p174: 165,52; p175: 96,02; p176: 96,02; p177: 53,82; p178: 53,82; p179: 53,82; p180: 11,62 |
| A30 | p484: 184,45; p485: 184,45; p486: 227,13; p487: 127,38; p488: 234,14; p489: 170,07; p490: 66,2 |
| A31 | não se aplica: sem portaria |
| A32 | p266: 81,8; p267: 134,72; p268: 110,64; p269: 6,1; p270: 21,15; p271: 51,24 |
| A33 | não se aplica: sem portaria |
| A34 | não se aplica: sem portaria |
| A35 | p507: 68,24; p508: 105,73; p509: 98,05; p510: 61,22; p511: 37,93; p512: 107,55 |
| A36 | p932: 120,81; p933: 86,76; p934: 86,76; p935: 8,49; p936: 52,69; p937: 8,49; p938: 52,69; p939: 86,8; p940: 120,91 |
| A37 | p934: 155,36; p935: 121,31; p936: 87,25; p937: 87,25; p938: 8,02; p939: 53,15; p940: 8,02; p941: 53,15; p942: 87,26 |

### B8 — Que estratégia gerou esta solução?

**Conferência:** `solution.strategy`: as etapas que geraram a solução, na ordem.

33 com resposta, 4 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | /tower/positioning/default/b, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A02 | /tower/positioning/default/b, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A03 | /tower/positioning/default/b, /entrance/entrance/default/a, /earthmoving/trama/default |
| A04 | /tower/positioning/default/b, /entrance/entrance/default/a, /earthmoving/trama/default |
| A05 | /tower/positioning/default/b, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A06 | /tower/positioning/default/a, /entrance/entrance/default/a, /earthmoving/trama/default |
| A07 | /tower/filling/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/trama/default |
| A08 | /tower/filling/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/trama/default |
| A09 | /tower/filling/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/trama/default |
| A10 | /tower/filling/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A11 | /tower/positioning/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A12 | /tower/positioning/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A13 | /tower/positioning/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a |
| A14 | /tower/positioning/default/a, /parking_lot/optimal_selection/default, /entrance/entrance/default/a |
| A15 | /tower/filling/default/a, /parking_lot/optimal_selection/default, /entrance/entrance/default/a |
| A16 | não se aplica: versão antiga, sem `solution.strategy` |
| A17 | não se aplica: versão antiga, sem `solution.strategy` |
| A18 | não se aplica: versão antiga, sem `solution.strategy` |
| A19 | não se aplica: versão antiga, sem `solution.strategy` |
| A20 | /entrance/entrance/default/a, /tower/filling/default/b, /parking_lot/optimal_selection/default, /leisure/distributed_family/default |
| A21 | /tower/filling/default/b, /entrance/entrance/default/a, /parking_lot/quarters/default |
| A22 | /tower/positioning/default/b, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A23 | /tower/positioning/default/a, /entrance/entrance/default/a, /earthmoving/trama/default |
| A24 | /tower/positioning/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/trama/default |
| A25 | /tower/positioning/default/a, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A26 | /tower/filling/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A27 | /tower/filling/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A28 | /tower/filling/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A29 | /tower/filling/default/a, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A30 | /tower/positioning/default/d, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /leisure/blob/default, /earthmoving/ibitira/default |
| A31 | /tower/positioning/default/a, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A32 | /tower/positioning/default/a, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /leisure/blob/default, /earthmoving/ibitira/default |
| A33 | /tower/positioning/default/a, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /leisure/blob/default, /earthmoving/ibitira/default |
| A34 | /tower/positioning/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A35 | /tower/positioning/default/d, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /leisure/blob/default, /earthmoving/ibitira/default |
| A36 | /tower/filling/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |
| A37 | /tower/filling/default/b, /parking_lot/optimal_selection/default, /entrance/entrance/default/a, /earthmoving/ibitira/default |

### B9 — Alguma torre fica sem vaga num raio de 50 m?

**Conferência:** Distância borda a borda entre o pavimento-tipo de cada torre e a vaga mais próxima; a torre fica sem vaga se ela passa de 50 m.

27 com resposta, 10 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | não se aplica: sem vagas |
| A02 | não se aplica: sem vagas |
| A03 | não se aplica: sem vagas |
| A04 | não se aplica: sem vagas |
| A05 | não se aplica: sem vagas |
| A06 | não se aplica: sem vagas |
| A07 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A08 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A09 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A10 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A11 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A12 | torres_sem_vaga_em_50m: p35; existe: sim |
| A13 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A14 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A15 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A16 | não se aplica: sem vagas |
| A17 | não se aplica: sem vagas |
| A18 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A19 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A20 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A21 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A22 | não se aplica: sem vagas |
| A23 | não se aplica: sem vagas |
| A24 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A25 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A26 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A27 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A28 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A29 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A30 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A31 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A32 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A33 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A34 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A35 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A36 | torres_sem_vaga_em_50m: nenhuma; existe: não |
| A37 | torres_sem_vaga_em_50m: nenhuma; existe: não |

### B11 — Quantas unidades eu perderia se a torre mais próxima da portaria tivesse 5 pavimentos a menos?

**Conferência:** A torre mais próxima da portaria (borda a borda); unidades por pavimento × min(5, pavimentos com unidades).

32 com resposta, 5 não se aplica.

| AQG | Resposta esperada |
| --- | --- |
| A01 | 120 |
| A02 | 80 |
| A03 | 54 |
| A04 | 65 |
| A05 | 90 |
| A06 | 45 |
| A07 | 40 |
| A08 | 40 |
| A09 | 40 |
| A10 | 75 |
| A11 | não se aplica: sem portaria |
| A12 | 65 |
| A13 | 80 |
| A14 | 35 |
| A15 | 20 |
| A16 | 60 |
| A17 | 130 |
| A18 | 40 |
| A19 | 40 |
| A20 | 40 |
| A21 | 40 |
| A22 | 55 |
| A23 | 55 |
| A24 | 40 |
| A25 | 16 |
| A26 | 40 |
| A27 | 40 |
| A28 | não se aplica: sem portaria |
| A29 | 16 |
| A30 | 60 |
| A31 | não se aplica: sem portaria |
| A32 | 40 |
| A33 | não se aplica: sem portaria |
| A34 | não se aplica: sem portaria |
| A35 | 80 |
| A36 | 40 |
| A37 | 40 |

## Edição e histórico

O modelo resolve a referência ("a torre mais próxima da frente") e chama a tool com os argumentos da tabela; a torre é o id `p<i>`, o índice em `solution.placed_objects`. A tool devolve o veredito e passa o estado para o AQG da coluna Estado (em `data/benchmark/gravacoes/`):

- **válido:** a edição passou nas regras do terreno e do programa, e o que depende dela foi refeito;
- **inválido:** a edição viola uma regra (coluna Violações), e o estado é o AQG com a edição, sem refazer o resto;
- **erro:** a Arqgen não conseguiu refazer a solução, e o estado não muda.

### D1 — Mova a torre mais próxima da frente 5 m em direção aos fundos.

**Chamada:** `mover_torre`. **Conferência:** A torre mais próxima da frente sobe 5 m na perpendicular à frente, para dentro do terreno; depois, vagas, viário, terraplenagem e indicadores são refeitos.

27 casos: invalido: 11; valido: 15; erro: 1.

| AQG | Argumentos | Veredito | Violações | Resposta | Estado |
| --- | --- | --- | --- | --- | --- |
| A01 | distancia: 5; sentido: fundos; torre: p1 | invalido | InsideGeometry | — | 0aa470fdb8340341 |
| A02 | distancia: 5; sentido: fundos; torre: p9 | valido | — | — | 996e6ae89881cd3a |
| A03 | distancia: 5; sentido: fundos; torre: p1 | invalido | InsideGeometry | — | dd747c138ac722f8 |
| A04 | distancia: 5; sentido: fundos; torre: p1 | invalido | DistanceFromLinesGreaterThanThreshold | — | 51ac22e699bb9cf3 |
| A05 | distancia: 5; sentido: fundos; torre: p2 | invalido | NoOverlapping | — | 34146cf2edb8c7f9 |
| A06 | distancia: 5; sentido: fundos; torre: p1 | invalido | NoOverlapping | — | e04bc18165886e8d |
| A07 | distancia: 5; sentido: fundos; torre: p255 | valido | — | — | 31100608f54a03b6 |
| A08 | distancia: 5; sentido: fundos; torre: p357 | valido | — | — | b90c4bca6dda0b90 |
| A09 | distancia: 5; sentido: fundos; torre: p120 | invalido | DistanceFromLinesGreaterThanThreshold | — | 9788ef0210081412 |
| A10 | distancia: 5; sentido: fundos; torre: p149 | valido | — | — | e83526a91ee68aed |
| A11 | distancia: 5; sentido: fundos; torre: p376 | invalido | NoOverlapping | — | cd44dffe4da1ea60 |
| A12 | distancia: 5; sentido: fundos; torre: p35 | valido | — | — | 8de4ca6168b8957c |
| A13 | distancia: 5; sentido: fundos; torre: p0 | valido | — | — | 827e49b1b58d5e80 |
| A15 | distancia: 5; sentido: fundos; torre: p0 | valido | — | — | 2ca3acf57454cac0 |
| A24 | distancia: 5; sentido: fundos; torre: p221 | valido | — | — | 051531f02b5b3532 |
| A25 | distancia: 5; sentido: fundos; torre: p195 | invalido | DistanceFromLinesGreaterThanThreshold | — | 8c715f063b365dbd |
| A26 | distancia: 5; sentido: fundos; torre: p326 | valido | — | — | 374ba667ce110d63 |
| A27 | distancia: 5; sentido: fundos; torre: p350 | valido | — | — | 349c2ed562f73006 |
| A29 | distancia: 5; sentido: fundos; torre: p180 | valido | — | — | 4f1238bbc2b12336 |
| A30 | distancia: 5; sentido: fundos; torre: p489 | invalido | NoOverlapping | — | c9adc47b1f40e4ee |
| A31 | distancia: 5; sentido: fundos; torre: p153 | erro | — | — | 38c80c06534b057b |
| A32 | distancia: 5; sentido: fundos; torre: p271 | invalido | NoOverlapping | — | eba7b484b01bb2f8 |
| A33 | distancia: 5; sentido: fundos; torre: p157 | valido | — | — | 0d31cc70394673a7 |
| A34 | distancia: 5; sentido: fundos; torre: p709 | valido | — | — | 78e3e4bfb3b19450 |
| A35 | distancia: 5; sentido: fundos; torre: p507 | invalido | DistanceFromLinesGreaterThanThreshold | — | ec3dd6600d37f8d1 |
| A36 | distancia: 5; sentido: fundos; torre: p937 | valido | — | — | 1aa6790ed4a281c3 |
| A37 | distancia: 5; sentido: fundos; torre: p940 | valido | — | — | 24f896cb8cb2f03a |

### D3 — Remova a torre mais próxima da APP e diga quantas unidades perdi.

**Chamada:** `remover_torre`. **Conferência:** Só nos arquivos com APP (layer `AQG_APP`). Unidades perdidas = `TotalDeUnidades` antes − depois.

2 casos: valido: 2.

| AQG | Argumentos | Veredito | Violações | Resposta | Estado |
| --- | --- | --- | --- | --- | --- |
| A30 | torre: p490 | valido | — | unidades_perdidas: 60 | 9d2080bbfd09c5d7 |
| A35 | torre: p508 | valido | — | unidades_perdidas: 72 | 0c3e3d5767141a89 |

### D6 — Suba a torre mais próxima da portaria para 20 pavimentos.

**Chamada:** `definir_pavimentos`. **Conferência:** A torre mais próxima da portaria passa a ter 20 pavimentos. É inválido quando sai da faixa de pavimentos que o terreno e o programa permitem.

24 casos: valido: 3; invalido: 21.

| AQG | Argumentos | Veredito | Violações | Resposta | Estado |
| --- | --- | --- | --- | --- | --- |
| A01 | torre: p2; total: 20 | valido | — | — | 50518fd0713fbbaf |
| A02 | torre: p9; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 18; minimo: 1; pedido: 19) | 68c086b1f2d128d1 |
| A03 | torre: p3; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 2; minimo: 1; pedido: 19) | c3ee59836db3c935 |
| A04 | torre: p1; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 10; minimo: 8; pedido: 20) | b5b56f982232dddd |
| A05 | torre: p1; total: 20 | valido | — | — | bf4b6d97625dbd2c |
| A06 | torre: p1; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 8; minimo: 8; pedido: 20) | 3c3b789749db2822 |
| A07 | torre: p255; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 15; minimo: 14; pedido: 20) | 2a0ac2fbcb589bec |
| A08 | torre: p355; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 15; minimo: 14; pedido: 20) | f78c55e28343853e |
| A09 | torre: p120; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 15; minimo: 14; pedido: 20) | 73f5d3032e9d94f4 |
| A10 | torre: p150; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 10; minimo: 10; pedido: 20) | 24b3f4a8e368d5b3 |
| A12 | torre: p35; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 10; minimo: 10; pedido: 20) | d65e76f5d23f4ce1 |
| A13 | torre: p0; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 4; minimo: 4; pedido: 20) | a4d1bfbe15533388 |
| A14 | torre: p1; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 5; minimo: 5; pedido: 20) | 65a9514537fb17ea |
| A15 | torre: p0; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 4; minimo: 4; pedido: 20) | 32c8b115ea93caca |
| A24 | torre: p221; total: 20 | valido | — | — | 4c8af4e12ff3b7fd |
| A25 | torre: p201; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 4; minimo: 4; pedido: 20) | 54299b59d1e45f55 |
| A26 | torre: p326; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 8; minimo: 8; pedido: 20) | d00f50cf5ed6a9a1 |
| A27 | torre: p352; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 8; minimo: 8; pedido: 20) | 2fad9869ac788e54 |
| A29 | torre: p180; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 4; minimo: 4; pedido: 20) | b1dfbf01518686a1 |
| A30 | torre: p490; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 5; minimo: 1; pedido: 19) | cfc3521c59860425 |
| A32 | torre: p269; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 13; minimo: 1; pedido: 19) | 78b5635efb4d9922 |
| A35 | torre: p511; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 6; minimo: 4; pedido: 20) | c04090d01d8b2462 |
| A36 | torre: p937; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 15; minimo: 1; pedido: 19) | a82a51494d8800f5 |
| A37 | torre: p940; total: 20 | invalido | MaxPavimentos | pavimentos_com_unidades: (maximo: 15; minimo: 1; pedido: 19) | 19097e163252a5b8 |

### E1 — Aumente para 1,5 vaga por unidade e refaça só o estacionamento.

**Chamada:** `alterar_programa`. **Conferência:** `ParkingLotPerUnit` = 1,5 no `archprog`. Vagas necessárias = teto(unidades × 1,5); o déficit é necessárias − projetadas.

23 casos: valido: 8; invalido: 13; erro: 2.

| AQG | Argumentos | Veredito | Violações | Resposta | Estado |
| --- | --- | --- | --- | --- | --- |
| A07 | chave: ParkingLotPerUnit; valor: 1,5 | valido | — | vagas: (necessarias: 360; projetadas: 356; deficit: 4; na_base: 253) | 4b476868734fc663 |
| A08 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | ce9acdc9b6dcb671 |
| A09 | chave: ParkingLotPerUnit; valor: 1,5 | valido | — | vagas: (necessarias: 168; projetadas: 168; deficit: 0; na_base: 118) | 577b38580f185228 |
| A10 | chave: ParkingLotPerUnit; valor: 1,5 | valido | — | vagas: (necessarias: 900; projetadas: 808; deficit: 92; na_base: 147) | f15fe7627e172bbe |
| A11 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | c250bc7f9cd098dc |
| A12 | chave: ParkingLotPerUnit; valor: 1,5 | valido | — | vagas: (necessarias: 195; projetadas: 195; deficit: 0; na_base: 33) | 48b61ccf903738b7 |
| A13 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | ParkingNetworkInsufficientRatio | vagas: (encontradas: 85; necessarias: 120) | 56cdf101108af456 |
| A14 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | 412a51a30a29cf41 |
| A15 | chave: ParkingLotPerUnit; valor: 1,5 | valido | — | vagas: (necessarias: 30; projetadas: 30; deficit: 0; na_base: 20) | ad9e2a937ec2f681 |
| A24 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | 6b8ec129a4a7de02 |
| A25 | chave: ParkingLotPerUnit; valor: 1,5 | valido | — | vagas: (necessarias: 288; projetadas: 233; deficit: 55; na_base: 192) | aaf83bb3cfd40881 |
| A26 | chave: ParkingLotPerUnit; valor: 1,5 | erro | — | — | 567950f0b1139752 |
| A27 | chave: ParkingLotPerUnit; valor: 1,5 | erro | — | — | c861ad7797dc2b3a |
| A28 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | aad1aeae55557800 |
| A29 | chave: ParkingLotPerUnit; valor: 1,5 | valido | — | vagas: (necessarias: 240; projetadas: 240; deficit: 0; na_base: 169) | 00361ab156e70d89 |
| A30 | chave: ParkingLotPerUnit; valor: 1,5 | valido | — | vagas: (necessarias: 720; projetadas: 640; deficit: 80; na_base: 480) | b439b9bf93fc1127 |
| A31 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | c765a11dd96eb22c |
| A32 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | d0de07c33486bdad |
| A33 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | 1e8b51f9984b42cc |
| A34 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | 6ffaff4fe10f63e9 |
| A35 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | ParkingNetworkInsufficientRatio | vagas: (encontradas: 563; necessarias: 756) | a26df3263e88937f |
| A36 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | 4484f07b218692c6 |
| A37 | chave: ParkingLotPerUnit; valor: 1,5 | invalido | PermeabilidadeExigida | — | 59c8355c47590a44 |

### E3 — Mude o mix para 60% 2Q / 40% 1Q mantendo a implantação.

**Chamada:** `alterar_programa`. **Conferência:** Mix de 60% `2q/40_71` e 40% `1q/27_97`. Cada torre troca para a família equivalente com o programa novo; a que deixar de caber é reposicionada ou removida.

29 casos: valido: 23; erro: 5; invalido: 1.

| AQG | Argumentos | Veredito | Violações | Resposta | Estado |
| --- | --- | --- | --- | --- | --- |
| A01 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | reposicionadas: 2 | de0e5ad3ea37c3fd |
| A02 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | removidas: 5 | ab34a73368fe8a72 |
| A03 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | — | 94e780142a772872 |
| A04 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | removidas: 2 | f97b41ee6c389fcf |
| A05 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | removidas: 1 | 170644efa6e65060 |
| A06 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | reposicionadas: 2 | f743c49bf581ccd1 |
| A07 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | — | 381ba58d92462665 |
| A08 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | removidas: 1 | 39e99f7386aa4eab |
| A09 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | erro | — | removidas: 1 | bf31942fc2cd024d |
| A10 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | — | 709c82f2b1242ef4 |
| A11 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | reposicionadas: 1 | 3694b2b4102f38ff |
| A12 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | — | 97453c627cd41dba |
| A13 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | reposicionadas: 1 | 8987d1ea72704953 |
| A14 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | invalido | ParkingNetworkInsufficientRatio | vagas: (encontradas: 75; necessarias: 120); reposicionadas: 1 | e14a8f0c0d09a54e |
| A15 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | — | d273cb62a79d4d3b |
| A24 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | — | 2bad3e506408fa98 |
| A25 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | reposicionadas: 5; removidas: 1 | b21c575e4087d8c1 |
| A26 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | erro | — | removidas: 3 | 567950f0b1139752 |
| A27 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | erro | — | removidas: 2 | c861ad7797dc2b3a |
| A28 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | removidas: 2 | c819cb44848603aa |
| A29 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | erro | — | — | aaf73e4583674808 |
| A30 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | reposicionadas: 2; removidas: 2 | 7ac15fd10f137df5 |
| A31 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | erro | — | reposicionadas: 1 | 38c80c06534b057b |
| A32 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | reposicionadas: 4 | 03ba8ff127b417fc |
| A33 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | — | 7bcf40fd6657d193 |
| A34 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | — | 13e415b55033edc4 |
| A35 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | reposicionadas: 2; removidas: 1 | d30fe26ed7f2a652 |
| A36 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | removidas: 5 | 6795954d6f50d211 |
| A37 | mix: (/building/apartamento/1q/27_97: 40; /building/apartamento/2q/40_71: 60) | valido | — | removidas: 4 | 38b0c44ef3c4f7e6 |

### E7 — Refaça só a terraplenagem com talude mais suave e sem muro.

**Chamada:** `resolver_terraplenagem`. **Conferência:** Talude de aterro 1:2, de corte 1:1,5, sem muro. Só a terraplenagem e os indicadores mudam; torres e vagas ficam iguais.

26 casos: valido: 26.

| AQG | Argumentos | Veredito | Violações | Resposta | Estado |
| --- | --- | --- | --- | --- | --- |
| A01 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 38e5131dc867ab45 |
| A02 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 73a4a2f6c36b444e |
| A03 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 2b4a7e3d3c27beb3 |
| A04 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 9ac7b7d39a5c3944 |
| A05 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 1f7d24af8851aea1 |
| A06 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 60b7e67ff591b61f |
| A07 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | afc4b0c326c294ae |
| A08 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | a132fdd1133cac7b |
| A09 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 08abc7b93f60a051 |
| A10 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 040a73310d9d66a3 |
| A11 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 4e86048c446be667 |
| A12 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 7acd2359b453be2b |
| A24 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 856f4583770580f4 |
| A25 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | a4172c4138ac6cd4 |
| A26 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | de3a5b7c83112813 |
| A27 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 167b7b80d8b42c4b |
| A28 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 7933275dd528682e |
| A29 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 910d02ad0177815e |
| A30 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | df26e4586abf65b7 |
| A31 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | aaee2d7e10edf5d7 |
| A32 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 76692c8893187ef7 |
| A33 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | c0a2bf9e82db6ccd |
| A34 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 394a6639f55e200a |
| A35 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 93cd4399ddc75422 |
| A36 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 7b6c517291be138b |
| A37 | aterro: 1:2; corte: 1:1,5; muro: sem limite | valido | — | — | 0b91a10050c8b73c |

### G4 — O que mudou entre a solução mãe e a filha?

**Chamada:** `diff_versoes`. **Conferência:** A mãe é o estado inicial e a filha, o resultado da D1. A resposta é a diferença: torre movida e vetor, vagas, corte, aterro e indicadores.

15 casos.

| AQG | Torre movida | Vagas | Terraplenagem | Indicadores alterados |
| --- | --- | --- | --- | --- |
| A02 | p9, vetor (1,85, -4,65) m | mãe: 0; filha: 0 | corte: 8.914,39 → 8.963,94; aterro: 8.862,29 → 8.851,82 | 2 |
| A07 | p255, vetor (-3,54, -3,53) m | mãe: 253; filha: 253 | corte: 1.069,53 → 1.015,83; aterro: 396,39 → 303,28 | 10 |
| A08 | p357, vetor (-3,54, -3,53) m | mãe: 353; filha: 353 | corte: 819,92 → 793,02; aterro: 1.439,67 → 1.435,85 | 10 |
| A10 | p149, vetor (-4,59, 1,98) m | mãe: 147; filha: 147 | corte: 3.502,5 → 3.488,17; aterro: 3.253,73 → 3.266,42; muro_comprimento: 320,87 → 319,43; muro_altura: 1,82 → 1,8 | 2 |
| A12 | p35, vetor (-4,59, 1,98) m | mãe: 33; filha: 33 | corte: 162,26 → 221,62; aterro: 5.332,8 → 5.412,15; muro_comprimento: 10,85 → 22,18; muro_altura: 0,1 → 0,43 | 2 |
| A13 | p0, vetor (4,93, -0,82) m | mãe: 80; filha: 66 | — | 12 |
| A15 | p0, vetor (-5, 0,06) m | mãe: 20; filha: 20 | — | 4 |
| A24 | p221, vetor (4,26, -2,61) m | mãe: 219; filha: 216 | corte: 870,96 → 825,37; aterro: 1.014,01 → 1.142,05 | 14 |
| A26 | p326, vetor (-4,09, -2,88) m | mãe: 320; filha: 320 | corte: 6.282,81 → 6.213,92; aterro: 13.062,96 → 13.039,21; muro_comprimento: 167,03 → 158,02; muro_altura: 1,36 → 1,23 | 2 |
| A27 | p350, vetor (-4,91, 0,95) m | mãe: 346; filha: 346 | corte: 6.374,61 → 6.606,22; aterro: 15.055,95 → 12.976,05; muro_comprimento: 161,86 → 151,23; muro_altura: 1,63 → 1,51 | 10 |
| A29 | p180, vetor (-4,8, 1,4) m | mãe: 169; filha: 169 | corte: 795,57 → 1.043,51; aterro: 879,89 → 604,91 | 10 |
| A33 | p157, vetor (-4,99, -0,28) m | mãe: 154; filha: 152 | corte: 1.629,7 → 1.646,51; aterro: 1.306,17 → 1.294,63; muro_comprimento: 0 → 14,43; muro_altura: 0 → 0,11 | 14 |
| A34 | p709, vetor (-2,78, 4,16) m | mãe: 706; filha: 702 | corte: 905,18 → 1.057,71; aterro: 1.336,23 → 969,89 | 14 |
| A36 | p937, vetor (-1,9, 4,62) m | mãe: 930; filha: 910 | corte: 5.364,38 → 5.501,96; aterro: 2.661,27 → 2.509,67; muro_comprimento: 25,65 → 25,31; muro_altura: 0,25 → 0,19 | 15 |
| A37 | p940, vetor (-1,9, 4,62) m | mãe: 932; filha: 888 | corte: 6.569,61 → 6.549,47; aterro: 3.012,71 → 2.725,25 | 15 |

### G5 — Desfaça as duas últimas mudanças.

**Chamada:** `desfazer`. **Conferência:** Sequência D1 → E7 sobre o estado inicial. Desfazer as duas volta ao estado inicial.

13 casos.

| AQG | Estado esperado |
| --- | --- |
| A02 | f1e1bf266a50c980 |
| A07 | b9d8a76034f5b7d8 |
| A08 | 9e780ba833bdbabd |
| A10 | eb6ed72593681f3b |
| A12 | 230a101a0499cf7f |
| A24 | 0a32aad47fdf66ec |
| A26 | 567950f0b1139752 |
| A27 | c861ad7797dc2b3a |
| A29 | aaf73e4583674808 |
| A33 | c5913d1686413871 |
| A34 | 0bffb80da2064f10 |
| A36 | ffcaf8869b41a8bf |
| A37 | 0429d3d9cb7e91b6 |
