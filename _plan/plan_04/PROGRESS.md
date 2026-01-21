# Progresso de Execução - Plan 04

**Início:** 2026-01-20
**Status:** ✅ Concluído
**Objetivo:** Detecção de Barras Aninhadas (Nested Bars)

---

## Fase 1: Implementar Análise Multi-Coluna

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Adicionar analyze_bar_columns() | ✅ Completo | 2026-01-20 | Implementado mas não usado (ver Fase 1.5) |
| Modificar detect_repetition_bars_v2() | ✅ Completo | 2026-01-20 | |
| Ajustar ordenação de resultados | ✅ Completo | 2026-01-20 | Barras internas primeiro |

---

## Fase 1.5: Mudança de Abordagem

**Descoberta:** A análise multi-coluna não funcionou porque:
- Barras no PDF são separadas por apenas ~6pt (~25px a 300dpi)
- Colunas de 60px são muito largas para separar barras tão próximas
- Ambos os níveis de barras caem na mesma coluna

**Nova abordagem:** Detecção de gaps (vales) dentro de segmentos
- Analisa variações de intensidade dentro de um segmento único
- Detecta "vales" onde a intensidade cai abaixo do threshold
- Divide o segmento em barras internas + mantém a barra externa

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Implementar detect_gaps_in_segment() | ✅ Completo | 2026-01-20 | Detecta vales no perfil |
| Filtrar segmentos muito pequenos | ✅ Completo | 2026-01-20 | min 15% da altura do segmento |
| Verificar simetria das barras internas | ✅ Completo | 2026-01-20 | ratio >= 0.5 |
| Aplicar gap detection seletivamente | ✅ Completo | 2026-01-20 | Apenas para 1 segmento > 15% |

---

## Fase 2: Atualizar Script de Debug

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Visualizar perfis por coluna | ✅ Completo | 2026-01-20 | |
| Adicionar análise de gaps | ✅ Completo | 2026-01-20 | Mostra vales encontrados |
| Testar em hinos com barras aninhadas | ✅ Completo | 2026-01-20 | |

---

## Fase 3: Validação

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Testar Hymn #5 (Flecha) | ✅ Correto | 2026-01-20 | "1-2, 3-4, 1-4" ✅ |
| Testar Hymn #29 (Confiar) | ⚠️ Parcial | 2026-01-20 | "1-4" vs "3-4, 1-4" - padrão assimétrico não suportado |
| Validação completa | ✅ Completo | 2026-01-20 | 183 testes passaram |

---

## Métricas Finais

| Métrica | Antes | Depois | Meta | Status |
|---------|-------|--------|------|--------|
| Repetições | 75% (30/40) | 77.5% (31/40) | 90%+ | ⚠️ Parcial (+2.5%) |
| Overall Score | 93% | 93.5% | 95%+ | ⚠️ Parcial (+0.5%) |

---

## Erros Restantes (9/40)

1. **Hymn #1 (Disciplina)**: '1-2, 3-4' vs '1-4, 5-8' - Mapeamento de linhas
2. **Hymn #6 (Cuidado)**: '1-4' vs '1-2' - Detecção excessiva
3. **Hymn #16 (Felicidade)**: '1-4' vs '1-5' - Mapeamento
4. **Hymn #18 (Amigo)**: '1-4' vs '1-3' - Detecção excessiva
5. **Hymn #20 (Estrela)**: '1-2, 3-4' vs '1-4, 5-7' - Mapeamento
6. **Hymn #25 (Fogueira)**: '1-2, 3-4' vs '1-3, 4-6' - Mapeamento
7. **Hymn #29 (Confiar)**: '1-4' vs '3-4, 1-4' - Padrão assimétrico
8. **Hymn #35 (A calma)**: '1-4' vs '1-2' - Detecção excessiva
9. **Hymn #37 (Bem estimados)**: '1-4' vs '1-8' - Mapeamento

---

## Log de Execução

### 2026-01-20

**Início** - Plano criado
- Identificado problema: barras aninhadas não detectadas
- Proposta inicial: análise multi-coluna

**Implementação multi-coluna**
- Adicionado analyze_bar_columns() dividindo região em 3 colunas
- Testado em Hymn #5 (Flecha)
- Resultado: todas as barras caíram na mesma coluna (rightmost)
- Descoberta: colunas de 60px são maiores que a separação entre barras (25px)

**Mudança de abordagem: Gap Detection**
- Implementado detect_gaps_in_segment()
- Detecta vales (intensity < 0.5 * max) dentro de segmentos
- Problema inicial: muitos falsos positivos ("1-1, 2-2, 4-4")
- Score caiu de 75% para 30%

**Refinamento do algoritmo**
- Adicionado filtro de altura mínima para segmentos internos (15% do segmento)
- Adicionado verificação de simetria (ratio >= 0.5)
- Aplicação seletiva: apenas para 1 segmento > 15% do body
- Score recuperou para 77.5%

**Resultado final**
- Hymn #5 (Flecha): "1-2, 3-4, 1-4" ✅ (antes: "1-4")
- Overall Score: 93.5% (+0.5%)
- Repetições: 77.5% (+2.5%)
- 183 testes passaram

---

## Limitações Identificadas

1. **Padrões assimétricos** não suportados (ex: "3-4, 1-4" onde apenas parte tem barra interna)
2. **Mapeamento de linhas** ainda impreciso para alguns hinos
3. **Detecção excessiva** em alguns casos onde barra cobre menos linhas que o detectado

## Próximos Passos (se continuar)

1. Implementar detecção de **picos de intensidade** (não só gaps) para padrões assimétricos
2. Melhorar mapeamento Y → linha usando posições OCR do Tesseract
3. Ajustar threshold dinâmico baseado no perfil específico de cada hino
