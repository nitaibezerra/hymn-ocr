# Contexto do Projeto - Hymn OCR

## Visão Geral

**hymn-ocr** é uma ferramenta de OCR gratuita para converter PDFs de hinários em YAML, usando Tesseract + OpenCV.

## Arquitetura

```
PDF → pdf2image → OpenCV (zonas) → Tesseract (OCR) → Regex (parsing) → YAML
```

## Estrutura do Código

```
hymn-ocr/
├── src/hymn_ocr/
│   ├── cli.py              # CLI com Typer
│   ├── pdf_processor.py    # PDF → imagens (300 DPI)
│   ├── zone_detector.py    # Detecção de zonas (header, body, footer)
│   ├── ocr_engine.py       # Tesseract OCR
│   ├── repetition_detector.py  # Barras verticais (Hough Transform)
│   ├── parser.py           # Regex parsing
│   ├── merger.py           # Merge multi-página
│   ├── pipeline.py         # Pipeline completo
│   ├── models.py           # Pydantic models
│   └── yaml_generator.py   # Geração YAML
├── tests/                  # 183 testes
└── scripts/                # Scripts auxiliares
```

## Estado Atual (Pré-Fase 6)

### Funcionando Bem
- Extração de 40/40 hinos
- Títulos: 100% match
- offered_to: 100% match
- style: 100% match

### Problemas Identificados
1. **received_at**: 35/40 datas ausentes
2. **repetitions**: Valores incorretos ("1-1" em vez de "1-4")
3. **text**: 8 hinos com artefatos OCR
4. **original_number**: 8 valores errados

## Arquivos de Referência

- **PDF de teste:** `../hymn_pdf_generator/example/selecao_aniversario_ingrid.pdf`
- **YAML original:** `../hymn_pdf_generator/example/selecao_aniversario_ingrid.yaml`
- **Output OCR:** `/tmp/hymn_ocr_output4.yaml`

## Comandos Úteis

```bash
# Rodar OCR
poetry run hymn-ocr convert input.pdf -o output.yaml

# Rodar testes
poetry run pytest -v

# Debug de uma página
poetry run hymn-ocr debug-page input.pdf 5
```

## Dependências Externas

- **poppler**: `brew install poppler`
- **tesseract**: `brew install tesseract tesseract-lang`
