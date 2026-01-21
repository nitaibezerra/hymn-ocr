# Issues Encontradas - Plan 03

## Issues Ativas

*Nenhuma issue ativa no momento.*

---

## Issues Resolvidas

*Nenhuma issue resolvida ainda.*

---

## Template de Issue

```markdown
### [ID] - Título da Issue
**Data:** YYYY-MM-DD
**Severidade:** Alta/Média/Baixa
**Status:** Aberta/Investigando/Resolvida

**Descrição:**
Descrição detalhada do problema.

**Reprodução:**
Passos para reproduzir.

**Causa Raiz:**
(Após investigação)

**Solução:**
(Após resolução)
```

---

## Issues Conhecidas do Detector v1 (para referência)

### LEGACY-001 - Hough Transform detecta linhas incorretas
**Status:** Resolvida (abandonado v1)
**Descrição:** Hough detectava bordas de texto, linhas horizontais, etc.

### LEGACY-002 - Tesseract retorna coordenadas Y imprecisas
**Status:** Resolvida (nova abordagem)
**Descrição:** get_text_line_positions() retornava ranges incorretos.

### LEGACY-003 - Tesseract não captura "|"
**Status:** Resolvida (não depende mais de OCR para barras)
**Descrição:** Abordagem OCR para detectar "|" não funcionava.
