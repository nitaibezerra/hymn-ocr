# Contexto - Detecção de Barras de Repetição v2

## Histórico

### Plan_02 (Fase 6 - Validação)
- **Baseline:** 58% overall score
- **Final:** 78% overall score
- **Datas:** 5% → 100%
- **Original Number:** 92.5% → 100%
- **Repetições:** 5% → Desabilitado (retorna None)

### Problema Original
O detector de repetições usando Hough Transform tinha apenas 5% de acurácia:
1. Hough detectava todas as linhas (horizontais, diagonais, bordas)
2. Mapeamento Y→linha via Tesseract era impreciso
3. Tesseract não captura caractere "|"

---

## Engenharia Reversa

### Fonte: hymn_pdf_generator

Analisamos como o PDF é gerado para entender as características exatas das barras:

**Arquivos analisados:**
- `hymn_pdf_generator/pdf_elements.py` - VerticalLine class
- `hymn_pdf_generator/repetition_bar_allocator.py` - X-axis allocation
- `hymn_pdf_generator/config.py` - Page configuration

**Descobertas:**
- Espessura: 0.7pt (~1px @ 300dpi)
- Cor: Preto
- Posição X: `-(level * 6pt)` da margem esquerda
- Sistema de níveis para barras sobrepostas

---

## Arquivos Relevantes

### hymn-ocr (projeto atual)
```
src/hymn_ocr/
├── repetition_detector.py     # Detector v1 (Hough - desabilitado)
├── repetition_detector_v2.py  # Detector v2 (a criar)
├── pipeline.py                # Integração
├── zone_detector.py           # Detecção de zonas
└── ocr_engine.py              # OCR Tesseract
```

### hymn_pdf_generator (referência)
```
hymn_pdf_generator/
├── pdf_elements.py            # VerticalLine, _build_vertical_lines
├── repetition_bar_allocator.py # X-axis level allocation
└── config.py                  # Page size, margins
```

---

## Dependências

- OpenCV (cv2) - Processamento de imagem
- NumPy - Arrays e operações matemáticas
- Tesseract/pytesseract - OCR (apenas para contagem de linhas)

---

## Dados de Teste

**PDF de teste:**
`../hymn_pdf_generator/example/selecao_aniversario_ingrid.pdf`

**YAML original (ground truth):**
`../hymn_pdf_generator/example/selecao_aniversario_ingrid.yaml`

**40 hinos com repetições variadas:**
- Simples: "1-4"
- Múltiplas: "1-2, 3-4"
- Sobrepostas: "1-4, 1-2, 3-4"
