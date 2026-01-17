# Plano: Hymn OCR - Solução Homemade (Sem LLM)

**Projeto:** hymn-ocr
**Data:** 2026-01-17
**Objetivo:** Converter PDFs de hinários em YAML usando OCR gratuito + visão computacional

---

## Filosofia: Layout-First

O PDF foi **gerado programaticamente** pelo `hymn_pdf_generator`, então tem layout **100% consistente**. Podemos explorar isso!

Em vez de usar LLM caro, vamos:
1. **Detectar zonas** com OpenCV
2. **OCR gratuito** com Tesseract
3. **Parsing estruturado** com regex
4. **Detectar barras de repetição** por análise de imagem

---

## Estrutura Visual Identificada

```
┌─────────────────────────────────────────────────┐
│           01. Disciplina (62)                   │  ← HEADER: "NN. Título (número)"
│  ─────────────────────────────────────────────  │  ← Linha horizontal
│           Ofertado a X - Valsa                  │  ← METADATA (opcional)
│                                                 │
│  │ Santa Maria                                  │  ← CORPO com barra de repetição
│  │ O caminho da disciplina                      │
│  │ Vem chegando noite e dia                     │
│  │ Como a luz de um clarão                      │
│                                                 │
│  │ Eu peço força                                │  ← Segunda estrofe com barra
│  │ Das estrelas que me guiam                    │
│  │ Que brilham no firmamento                    │
│  │ Com minha Santa Maria                        │
│                                                 │
│                   ✡                             │  ← SÍMBOLO (✡ ou ☀ ☾ ★)
│                                                 │
│                         (18/01/2020)            │  ← DATA
│                                            1    │  ← Número da página
└─────────────────────────────────────────────────┘
```

### Padrões Identificados:
- **Símbolo ✡** = hinos ímpares (1, 3, 5...)
- **Símbolo ☀ ☾ ★** = hinos pares (2, 4, 6...)
- **Continuação** = página sem header, sem símbolo/data
- **Barras** = linhas verticais x < 100px

---

## Stack Técnica (100% Gratuita)

```toml
[tool.poetry.dependencies]
python = "^3.11"
pdf2image = "^1.17.0"      # PDF → imagens (usa poppler)
opencv-python = "^4.9.0"   # Detecção de linhas e zonas
pytesseract = "^0.3.10"    # OCR gratuito
pillow = "^10.0.0"         # Manipulação de imagens
pydantic = "^2.5.0"        # Validação de dados
pyyaml = "^6.0"            # Geração YAML
typer = "^0.9.0"           # CLI
rich = "^13.0.0"           # Output formatado
numpy = "^1.26.0"          # Arrays para OpenCV

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"          # Testes
pytest-cov = "^4.1.0"      # Cobertura
pytest-xdist = "^3.5.0"    # Testes paralelos
```

**Dependências de sistema:**
```bash
# macOS
brew install poppler tesseract tesseract-lang

# Ubuntu
apt-get install poppler-utils tesseract-ocr tesseract-ocr-por
```

---

## Estrutura do Projeto

```
hymn-ocr/
├── pyproject.toml
├── src/
│   └── hymn_ocr/
│       ├── __init__.py
│       ├── cli.py              # Interface de linha de comando
│       ├── pdf_processor.py    # PDF → imagens
│       ├── zone_detector.py    # Detecção de zonas com OpenCV
│       ├── ocr_engine.py       # Tesseract OCR
│       ├── repetition_detector.py  # Detecção de barras verticais
│       ├── parser.py           # Regex parsing estruturado
│       ├── merger.py           # Merge de hinos multi-página
│       ├── models.py           # Pydantic models
│       └── yaml_generator.py   # Geração do YAML
├── tests/
│   ├── conftest.py             # Fixtures compartilhadas
│   ├── fixtures/
│   │   └── images/             # Imagens de teste extraídas do PDF
│   │       ├── page_01.png     # Capa
│   │       ├── page_02.png     # Primeiro hino
│   │       ├── page_03.png     # Segundo hino
│   │       ├── page_16.png     # Início de hino multi-página
│   │       ├── page_17.png     # Continuação
│   │       └── page_50.png     # Último hino
│   ├── test_models.py
│   ├── test_parser.py
│   ├── test_zone_detector.py
│   ├── test_ocr_engine.py
│   ├── test_repetition_detector.py
│   ├── test_merger.py
│   ├── test_pdf_processor.py
│   ├── test_yaml_generator.py
│   ├── test_pipeline.py        # Testes de integração
│   └── test_cli.py
├── _plan/
│   ├── PLAN.md                 # Este arquivo
│   ├── PROGRESS.md             # Log de progresso
│   └── CONTEXT.md              # Contexto técnico
└── README.md
```

---

## Especificação de Testes

### Cobertura Mínima: 90%

### 1. test_models.py

| Teste | Descrição | Dados de Entrada |
|-------|-----------|------------------|
| `test_hymn_valid` | Hino válido com todos os campos | Dados completos |
| `test_hymn_minimal` | Hino com campos opcionais None | Apenas campos obrigatórios |
| `test_hymn_invalid_number` | Rejeita número <= 0 | number=0 |
| `test_hymn_empty_title` | Rejeita título vazio | title="" |
| `test_hymn_empty_text` | Rejeita texto vazio | text="" |
| `test_hymn_invalid_date` | Rejeita data inválida | received_at="invalid" |
| `test_hymnbook_valid` | HymnBook válido | Lista de hinos |
| `test_hymnbook_empty` | Rejeita HymnBook vazio | hymns=[] |
| `test_page_type_enum` | Testa enum PageType | Todos os valores |

### 2. test_parser.py

| Teste | Descrição | Input | Expected |
|-------|-----------|-------|----------|
| `test_parse_header_full` | Header completo | "01. Disciplina (62)" | {number: 1, title: "Disciplina", original: 62} |
| `test_parse_header_no_original` | Header sem original | "05. Luz Divina" | {number: 5, title: "Luz Divina", original: None} |
| `test_parse_header_multiword` | Título com múltiplas palavras | "10. Santa Maria dos Céus (123)" | {number: 10, title: "Santa Maria dos Céus", original: 123} |
| `test_parse_header_invalid` | Header inválido | "texto qualquer" | None |
| `test_parse_date_valid` | Data válida | "(18/01/2020)" | "2020-01-18" |
| `test_parse_date_in_text` | Data em meio ao texto | "Final (25/12/2021) aqui" | "2021-12-25" |
| `test_parse_date_invalid` | Data inválida | "texto sem data" | None |
| `test_parse_offered_to_simple` | Oferecimento simples | "Ofertado a João" | "João" |
| `test_parse_offered_to_with_style` | Oferecimento com estilo | "Ofertado a Maria - Valsa" | "Maria" |
| `test_parse_offered_to_ao` | "Ofertado ao" | "Ofertado ao Pedro" | "Pedro" |
| `test_parse_offered_to_a` | "Ofertado à" | "Ofertado à Ana" | "Ana" |
| `test_parse_style_valsa` | Detecta Valsa | "Texto - Valsa" | "Valsa" |
| `test_parse_style_marcha` | Detecta Marcha | "Texto - Marcha" | "Marcha" |
| `test_parse_style_mazurca` | Detecta Mazurca | "Texto - Mazurca" | "Mazurca" |
| `test_parse_style_bolero` | Detecta Bolero | "Texto - Bolero" | "Bolero" |
| `test_parse_style_none` | Sem estilo | "Texto sem estilo" | None |
| `test_parse_instructions_em_pe` | Detecta "Em pé" | "Em pé, sem instrumentos" | "Em pé, sem instrumentos" |
| `test_parse_instructions_sentados` | Detecta "Sentados" | "Sentados" | "Sentados" |
| `test_parse_metadata_complete` | Metadata completa | "Ofertado a X - Valsa, Em pé" | {offered_to: "X", style: "Valsa", extra: "Em pé"} |

### 3. test_zone_detector.py

| Teste | Descrição | Imagem | Verificação |
|-------|-----------|--------|-------------|
| `test_detect_zones_hymn_page` | Detecta zonas em página de hino | page_02.png | header, metadata, body, footer |
| `test_detect_zones_cover` | Detecta que é capa | page_01.png | is_cover=True |
| `test_detect_zones_continuation` | Detecta página de continuação | page_17.png | header=None |
| `test_detect_horizontal_line` | Detecta linha horizontal | page_02.png | y_position > 0 |
| `test_zone_boundaries` | Zonas não se sobrepõem | page_02.png | zones disjuntas |

### 4. test_ocr_engine.py

| Teste | Descrição | Imagem/Zona | Verificação |
|-------|-----------|-------------|-------------|
| `test_ocr_header_zone` | OCR no header | page_02.png header | Contém "01. Disciplina" |
| `test_ocr_body_zone` | OCR no corpo | page_02.png body | Texto extraído não vazio |
| `test_ocr_portuguese` | Acentuação preservada | page_02.png | Contém "ã", "é", "í" |
| `test_ocr_footer_date` | OCR no rodapé | page_02.png footer | Contém "(DD/MM/YYYY)" |
| `test_ocr_empty_zone` | Zona vazia | Imagem branca | Retorna "" |

### 5. test_repetition_detector.py

| Teste | Descrição | Imagem | Expected |
|-------|-----------|--------|----------|
| `test_detect_single_bar` | Uma barra de repetição | page_02.png | "1-4" ou similar |
| `test_detect_multiple_bars` | Múltiplas barras | page com 2+ barras | "1-4, 5-8" |
| `test_detect_no_bars` | Sem barras | page_17.png (continuação) | None |
| `test_bar_coordinates` | Coordenadas da barra | page_02.png | x < 15% width |
| `test_merge_broken_segments` | Segmentos quebrados | Imagem com linha fragmentada | Uma barra unificada |

### 6. test_merger.py

| Teste | Descrição | Input | Expected |
|-------|-----------|-------|----------|
| `test_merge_single_page` | Hino de uma página | [NEW_HYMN] | 1 hino |
| `test_merge_two_pages` | Hino de duas páginas | [NEW_HYMN, CONTINUATION] | 1 hino com texto concatenado |
| `test_merge_multiple_hymns` | Vários hinos | [NEW_HYMN, NEW_HYMN, NEW_HYMN] | 3 hinos |
| `test_merge_mixed` | Mix de 1 e multi-página | [NEW_HYMN, CONT, NEW_HYMN] | 2 hinos |
| `test_merge_preserves_date` | Data da última página | [NEW_HYMN, CONT com data] | Hino com data |
| `test_merge_adjusts_repetitions` | Ajusta linhas de repetição | [NEW_HYMN, CONT com reps] | Repetições ajustadas |
| `test_merge_empty_input` | Lista vazia | [] | [] |

### 7. test_pdf_processor.py

| Teste | Descrição | Input | Expected |
|-------|-----------|-------|----------|
| `test_convert_pdf_to_images` | Converte PDF | PDF válido | Lista de PIL Images |
| `test_convert_specific_pages` | Páginas específicas | pages=[1,2,3] | 3 imagens |
| `test_convert_dpi` | Resolução correta | dpi=300 | Tamanho proporcional |
| `test_invalid_pdf` | PDF inválido | Arquivo corrompido | Raise exception |
| `test_nonexistent_file` | Arquivo não existe | "nao_existe.pdf" | Raise FileNotFoundError |

### 8. test_yaml_generator.py

| Teste | Descrição | Input | Expected |
|-------|-----------|-------|----------|
| `test_generate_yaml_valid` | YAML válido | HymnBook completo | String YAML válida |
| `test_yaml_structure` | Estrutura correta | HymnBook | Keys: name, owner_name, hymns |
| `test_yaml_unicode` | Unicode preservado | Texto com acentos | Acentos no YAML |
| `test_yaml_multiline` | Texto multilinha | Hino com estrofes | Block scalar |
| `test_yaml_optional_fields` | Campos opcionais None | Hino minimal | Campos ausentes |
| `test_save_to_file` | Salva em arquivo | HymnBook | Arquivo criado |

### 9. test_pipeline.py (Integração)

| Teste | Descrição | Input | Expected |
|-------|-----------|-------|----------|
| `test_full_pipeline_single_hymn` | Pipeline completo 1 hino | page_02.png | Hymn válido |
| `test_full_pipeline_multipage` | Pipeline multi-página | page_16.png, page_17.png | 1 hino completo |
| `test_pipeline_all_pages` | PDF completo | PDF de exemplo | 40 hinos |
| `test_pipeline_output_matches_original` | Comparação com original | PDF | Diferenças mínimas |

### 10. test_cli.py

| Teste | Descrição | Comando | Expected |
|-------|-----------|---------|----------|
| `test_cli_convert_basic` | Conversão básica | `convert input.pdf -o out.yaml` | Arquivo criado |
| `test_cli_preview` | Preview sem salvar | `convert input.pdf --preview` | Output no terminal |
| `test_cli_debug` | Modo debug | `convert input.pdf --debug` | Imagens intermediárias |
| `test_cli_pages_range` | Range de páginas | `convert input.pdf --pages 2-10` | 9 páginas processadas |
| `test_cli_help` | Comando help | `--help` | Help text |
| `test_cli_invalid_file` | Arquivo inválido | `convert naoexiste.pdf` | Erro apropriado |

---

## Fases de Implementação

### Fase 1: Infraestrutura
- [x] Criar estrutura de diretórios
- [x] Extrair imagens de teste
- [ ] Criar pyproject.toml com Poetry
- [ ] Criar modelos Pydantic (models.py)
- [ ] Implementar PDF → imagens (pdf_processor.py)
- [ ] Escrever testes: test_models.py, test_pdf_processor.py

### Fase 2: Detecção e OCR
- [ ] Implementar zone_detector.py
- [ ] Implementar ocr_engine.py
- [ ] Escrever testes: test_zone_detector.py, test_ocr_engine.py

### Fase 3: Parsing e Barras
- [ ] Implementar parser.py com todos os regex
- [ ] Implementar repetition_detector.py
- [ ] Escrever testes: test_parser.py, test_repetition_detector.py

### Fase 4: Integração
- [ ] Implementar merger.py
- [ ] Implementar yaml_generator.py
- [ ] Implementar pipeline completo
- [ ] Criar CLI (cli.py)
- [ ] Escrever testes: test_merger.py, test_yaml_generator.py, test_pipeline.py, test_cli.py

### Fase 5: Refinamento
- [ ] Testar com PDF de exemplo completo
- [ ] Ajustar thresholds do OpenCV
- [ ] Tratar edge cases
- [ ] Documentar

---

## Checklist de Sucesso

- [ ] PDF convertido para imagens
- [ ] Capa detectada e info extraída
- [ ] Headers parseados corretamente
- [ ] Metadata (offered_to, style) extraída
- [ ] Barras de repetição detectadas
- [ ] Datas extraídas
- [ ] Hinos multi-página combinados
- [ ] YAML gerado corretamente
- [ ] CLI funcionando
- [ ] Cobertura de testes >= 90%

---

## Localização do Projeto

```
/Users/nitai/Dropbox/dev-mgi/hyms-platform/
├── hymn_pdf_generator/    # YAML → PDF
├── hyms-plat/             # Portal de Hinários
└── hymn-ocr/              # PDF → YAML (ESTE)
```
