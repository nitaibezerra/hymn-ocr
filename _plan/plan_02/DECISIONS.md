# Decisões Técnicas - Fase 6

## Decisões Tomadas

### 1. Estrutura YAML de Saída
**Data:** 2026-01-17
**Decisão:** Manter estrutura flat (atual)
**Alternativa rejeitada:** Estrutura nested (hymn_book.hymns[])
**Motivo:** Estrutura flat é mais limpa e moderna

### 2. Prioridade de Correções
**Data:** 2026-01-17
**Decisão:** Ordem de prioridade:
1. Datas (impacto em 35 hinos)
2. Artefatos OCR (impacto em 8 hinos)
3. Repetições (todos incorretos)
4. Original number (8 valores errados)
5. Metadados da capa (opcional)

### 3. Extração de Datas - Full Page OCR
**Data:** 2026-01-17
**Decisão:** Usar OCR full page em vez de OCR por zona para extração de datas
**Problema:** OCR por zona corrompia datas (ex: "(NOINAIININN" em vez de "(09/04/2020)")
**Solução:** `full_page_text = ocr_image(cv2_image)` em pipeline.py
**Arquivos modificados:** `src/hymn_ocr/pipeline.py`

### 4. Correção de original_number
**Data:** 2026-01-17
**Decisão:** Adicionar validação de range e correção automática
**Problema:** OCR lia ")" como "0)" causando números errados (603, 607, 608)
**Solução:** Se original_number > 200, remover segundo-último dígito
**Arquivos modificados:** `src/hymn_ocr/parser.py` - parse_header()

### 5. Desabilitar Detecção de Repetições
**Data:** 2026-01-17
**Decisão:** Desabilitar detecção de repetições, retornando None
**Motivo:** Acurácia de apenas 5% (2/40 corretos)
**Problemas identificados:**
1. Hough Transform detectando linhas horizontais incorretas
2. get_text_line_positions() retornando ranges y incorretos
3. Tesseract não captura caractere "|" de forma confiável
**Alternativas futuras:**
- ML-based line detection (YOLO, detectron2)
- Detecção de bordas específica para barras de repetição
- Abordagem híbrida com múltiplas técnicas
**Arquivos modificados:** `src/hymn_ocr/pipeline.py` - process_page()

---

## Decisões Adiadas

### Metadados da Capa
**Questão:** Implementar OCR da capa para extrair intro_name?
**Status:** Adiado - baixa prioridade, não impacta score principal
**Motivo:** Metadados da capa podem ser preenchidos manualmente

### Capitalização de Texto
**Questão:** Corrigir maiúsculas/minúsculas em nomes próprios?
**Status:** Adiado - complexidade alta para ganho marginal
