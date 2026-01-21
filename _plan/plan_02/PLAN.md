# Plano: Hymn OCR - Fase 6: Validação e Refinamento

**Projeto:** hymn-ocr
**Data:** 2026-01-17
**Objetivo:** Validar OCR contra YAML original e corrigir discrepâncias

---

## Diagnóstico Atual

### Comparação OCR vs Original (40 hinos)

| Campo | Status | Detalhes |
|-------|--------|----------|
| `title` | ✅ 40/40 | 100% match |
| `offered_to` | ✅ 40/40 | 100% match |
| `style` | ✅ 40/40 | 100% match |
| `text` | ⚠️ 32/40 | 8 hinos com artefatos OCR |
| `received_at` | ❌ 5/40 | 35 datas ausentes |
| `repetitions` | ❌ 0/40 | Valores corrompidos (ex: "1-1" em vez de "1-4") |
| `original_number` | ⚠️ 32/40 | 8 valores errados |
| `extra_instructions` | ⚠️ Parcial | "Em pé" extraído, faltou "sem instrumentos" |

---

## Fases de Implementação

### Fase 1: Script de Validação
- [ ] Criar `scripts/validate_ocr.py`
- [ ] Implementar comparação detalhada de campos
- [ ] Gerar relatório de discrepâncias

### Fase 2: Corrigir Extração de Datas
- [ ] Investigar por que datas não estão sendo extraídas
- [ ] Melhorar extração da zona footer
- [ ] Adicionar fallback para buscar data no texto completo

### Fase 3: Limpar Artefatos OCR
- [ ] Adicionar patterns para "Cl x", "Cx", "sds", "po"
- [ ] Corrigir problemas de capitalização
- [ ] Testar com os 8 hinos problemáticos

### Fase 4: Corrigir original_number
- [ ] Validar range do original_number (1-200)
- [ ] Corrigir casos como "607" → "67"

### Fase 5: Corrigir Repetições
- [ ] Revisar detector de barras verticais
- [ ] Implementar abordagem baseada em OCR do "|"
- [ ] Validar ranges extraídos

### Fase 6: Metadados da Capa (Opcional)
- [ ] Implementar OCR da capa
- [ ] Extrair intro_name e name do hinário

---

## Critérios de Sucesso

| Métrica | Meta | Atual |
|---------|------|-------|
| Títulos | 100% | 100% ✅ |
| Texto | 95%+ | 80% |
| Datas | 100% | 12.5% |
| Repetições | 90%+ | 0% |
| Original Number | 100% | 80% |

---

## Arquivos a Modificar

| Arquivo | Mudanças |
|---------|----------|
| `src/hymn_ocr/parser.py` | clean_body_text(), parse_header() |
| `src/hymn_ocr/pipeline.py` | Extração de datas |
| `src/hymn_ocr/repetition_detector.py` | Correção de ranges |
| `scripts/validate_ocr.py` | NOVO - script de validação |
