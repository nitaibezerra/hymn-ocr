# Progresso de Execução - Plan 05

**Início:** 2026-01-20
**Status:** ✅ Concluído
**Objetivo:** Mapeamento Tesseract para Line Mapping Preciso

---

## Fase 1: Implementar Tesseract Line Positions

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Adicionar get_line_boundaries_tesseract() | ✅ Completo | 2026-01-20 | Usa pytesseract.image_to_data() |
| Adicionar map_y_to_line_tesseract() | ✅ Completo | 2026-01-20 | Mapeia Y usando posições reais |
| Integrar no detect_repetition_bars_v2() | ✅ Completo | 2026-01-20 | Fallback para v3 se Tesseract falhar |

---

## Fase 2: Filtros de Instruções

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Identificar padrão "sem instrumentos" | ✅ Completo | 2026-01-20 | Hymn #7 com extra_instructions |
| Adicionar INSTRUCTION_PATTERNS filter | ✅ Completo | 2026-01-20 | "Em pé", "sem instrumentos", etc. |

---

## Fase 3: Validação

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Testar Hymn #1 (Disciplina) | ✅ Correto | 2026-01-20 | "1-4, 5-8" ✅ (antes: "1-2, 3-4") |
| Testar Hymn #6 (Cuidado) | ✅ Correto | 2026-01-20 | "1-2" ✅ (antes: "1-4") |
| Testar Hymn #7 (Estrela) | ✅ Correto | 2026-01-20 | "1-4" ✅ (antes: "2-5") |
| Testar Hymn #18 (Amigo) | ✅ Correto | 2026-01-20 | |
| Testar Hymn #35 (A calma) | ✅ Correto | 2026-01-20 | |
| Testar Hymn #29 (Confiar) | ⚠️ Parcial | 2026-01-20 | "1-4" vs "3-4, 1-4" - padrão assimétrico |
| Validação completa | ✅ Completo | 2026-01-20 | 183 testes passaram |

---

## Métricas Finais

| Métrica | Antes (Plan 04) | Depois (Plan 05) | Meta | Status |
|---------|-----------------|------------------|------|--------|
| Repetições | 77.5% (31/40) | **97.5%** (39/40) | 90%+ | ✅ Superado (+20%) |
| Overall Score | 93.5% | **97.5%** | 95%+ | ✅ Superado (+4%) |

---

## Erros Restantes (1/40 Repetições)

1. **Hymn #29 (Confiar)**: '1-4' vs '3-4, 1-4' - Padrão assimétrico não suportado

---

## Outros Issues (Text Similarity)

1. **Hymn #16 (Felicidade)**: text similarity 30.4% - Body zone detection issue
2. **Hymn #27 (Sempre viva)**: text similarity 26.5% - Body zone detection issue

---

## Log de Execução

### 2026-01-20

**Implementação Tesseract Line Mapping**
- Adicionado `get_line_boundaries_tesseract()`:
  - Usa `pytesseract.image_to_data()` para obter posições Y exatas
  - Agrupa palavras por linha usando block_num, par_num, line_num
  - Filtra artefatos OCR
- Adicionado `map_y_to_line_tesseract()`:
  - Mapeia Y para linha usando posições reais, não estimadas
  - Considera centro da linha para decisões de boundary
- Integrado em `detect_repetition_bars_v2()`:
  - Usa Tesseract quando >= 2 linhas detectadas
  - Fallback para map_y_to_line_v3() caso contrário

**Primeira Validação**
- Repetitions: 95.0% (38/40) - melhora de +17.5%
- Hymn #7 ainda com erro: "2-5" vs "1-4"
- Causa: "sem instrumentos" (extra_instructions) detectado como linha 1

**Filtro de Instruções**
- Adicionado INSTRUCTION_PATTERNS em get_line_boundaries_tesseract()
- Padrões: "sem instrumentos", "em pé", "sentados", "de pé", "instrumental"
- Hymn #7 agora detecta "1-4" corretamente

**Validação Final**
- Repetitions: **97.5%** (39/40) - melhora de +20%
- Overall Score: **97.5%** - melhora de +4%
- 183 testes passaram

---

## Limitações Identificadas

1. **Padrões assimétricos** não suportados (ex: "3-4, 1-4" onde apenas parte tem barra interna)
2. **Body zone detection** impreciso para alguns hinos (Hymns #16, #27)

## Próximos Passos (se continuar)

1. Implementar detecção de **intensidade diferencial** para padrões assimétricos
2. Melhorar body zone detection para resolver issues de text similarity
