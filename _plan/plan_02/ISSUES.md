# Issues e Soluções - Fase 6

## Issues Identificadas

### ISSUE-001: Datas não extraídas (received_at)
**Severidade:** Alta
**Impacto:** 35/40 hinos (87.5%)
**Sintoma:** Campo received_at ausente na maioria dos hinos
**Causa provável:** OCR do footer não está funcionando corretamente
**Status:** Pendente

---

### ISSUE-002: Artefatos OCR no texto
**Severidade:** Alta
**Impacto:** 8/40 hinos (20%)
**Sintoma:** Textos com "Cl x", "Cx", "sds", "po" no final
**Hinos afetados:** #9, #17, #21, #27, #33, #37, #39
**Causa:** Símbolos não filtrados pelo clean_body_text()
**Status:** Pendente

---

### ISSUE-003: Repetições incorretas
**Severidade:** Média
**Impacto:** 40/40 hinos (100%)
**Sintoma:** Valores como "1-1, 1-1" em vez de "1-4, 5-8"
**Causa:** Mapeamento y-coordinate → linha incorreto
**Status:** Pendente

---

### ISSUE-004: original_number errados
**Severidade:** Média
**Impacto:** 8/40 hinos (20%)
**Sintoma:** Valores como "607" em vez de "67"
**Causa:** OCR interpretando mal números entre parênteses
**Status:** Pendente

---

### ISSUE-005: Capitalização incorreta
**Severidade:** Baixa
**Impacto:** 1+ hino
**Sintoma:** "lansã" em vez de "Iansã"
**Causa:** OCR não reconhece maiúsculas em certas fontes
**Status:** Pendente

---

## Issues Resolvidas

*Nenhuma issue resolvida ainda nesta fase.*

---

## Template para Nova Issue

```markdown
### ISSUE-XXX: [Título]
**Severidade:** Alta/Média/Baixa
**Impacto:** X/40 hinos (Y%)
**Sintoma:** [Descrição do problema]
**Causa:** [Causa raiz identificada]
**Solução:** [Solução implementada]
**Status:** Pendente/Em andamento/Resolvida
**Data resolução:** YYYY-MM-DD
```
