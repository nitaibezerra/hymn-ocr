# Progresso de Execução - Plan 03

**Início:** 2026-01-17
**Status:** ✅ Concluído
**Objetivo:** Detecção de Barras de Repetição v2

---

## Fase 1: Criar Detector v2

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Criar repetition_detector_v2.py | ✅ Completo | 2026-01-17 | Sobel edge detection |
| Implementar extract_bar_region | ✅ Completo | 2026-01-17 | 15% da largura da página |
| Implementar vertical_projection_profile | ✅ Completo | 2026-01-17 | compute_vertical_profile() |
| Implementar find_bar_segments | ✅ Completo | 2026-01-17 | threshold=0.15 |
| Implementar map_y_to_line | ✅ Completo | 2026-01-17 | map_y_to_line_v3() |

---

## Fase 2: Script de Debug

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Criar scripts/debug_repetition.py | ✅ Completo | 2026-01-17 | |
| Visualizar perfil de projeção | ✅ Completo | 2026-01-17 | matplotlib |
| Testar em imagem de exemplo | ✅ Completo | 2026-01-17 | |

---

## Fase 3: Testes Isolados

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Extrair imagens de teste do PDF | ✅ Completo | 2026-01-17 | Via script de debug |
| Testar detector em cada página | ✅ Completo | 2026-01-17 | |
| Comparar com valores esperados | ✅ Completo | 2026-01-17 | |

---

## Fase 4: Integração no Pipeline

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Modificar pipeline.py | ✅ Completo | 2026-01-17 | |
| Substituir detector v1 por v2 | ✅ Completo | 2026-01-17 | |
| Testar pipeline completo | ✅ Completo | 2026-01-17 | |

---

## Fase 5: Validação

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Gerar novo YAML | ✅ Completo | 2026-01-17 | |
| Executar validate_ocr.py | ✅ Completo | 2026-01-17 | |
| Verificar acurácia | ✅ Completo | 2026-01-17 | 75% (meta era 90%+) |

---

## Fase 6: Iteração

| Tarefa | Status | Data | Notas |
|--------|--------|------|-------|
| Ajustar threshold | ✅ Completo | 2026-01-17 | 0.15 |
| Ajustar margin_percent | ✅ Completo | 2026-01-17 | 15% |
| Tratar casos especiais | ✅ Completo | 2026-01-17 | Filtros OCR |
| Ajustar estimativa de linhas | ✅ Completo | 2026-01-17 | 4 linhas para 1 seg, 2 para 2+ |

---

## Métricas Finais

| Métrica | Antes | Depois | Meta | Status |
|---------|-------|--------|------|--------|
| Overall Score | 78% | 93.0% | - | ✅ +15% |
| Repetições | 0% | 75.0% | 90%+ | ⚠️ Parcial |

---

## Log de Execução

### 2026-01-17

**13:00** - Plano criado
- Engenharia reversa do hymn_pdf_generator concluída
- Nova abordagem definida: Perfil de Projeção Vertical
- Documentação criada em _plan/plan_03/

**14:00** - Fase 1 completa: repetition_detector_v2.py criado
- Implementado detector baseado em Sobel edge detection
- Usa perfil de projeção vertical na margem esquerda da página

**14:30** - Fases 2-3: Debug e testes
- Criado scripts/debug_repetition.py para visualização
- Problema identificado: barras estão na margem da PÁGINA (150px), não da zona body
- Ajustado margin_percent de 8% para 15%
- Primeiro sucesso: página 2 detectando "1-4, 5-8" corretamente

**15:00** - Fase 4: Integração no pipeline
- pipeline.py atualizado para usar repetition_detector_v2
- Removido código desabilitado do v1

**15:30** - Fase 5: Validação inicial
- Overall Score: 78% → 81.5% (+3.5%)
- Repetitions: 0% (desabilitado) → 17.5% (7/40 corretos)
- Padrão de erro identificado: "1-3, 3-4" em vez de "1-2, 3-4"
- Mapeamento proporcional funciona para hinos com 8 linhas, mas não para 4 linhas

**16:00** - Fase 6: Iteração e ajustes
- Problema: OCR capturando "|" como parte do texto + artefatos "WC x", datas
- Solução: Filtros aprimorados para remover artefatos e normalizar contagem de linhas
- Implementado map_y_to_line_v3 com estimativa de line_height baseada nos segmentos
- Correção: Para 2+ segmentos, cada um cobre ~2 linhas
- Correção: Para 1 segmento, cobre ~4 linhas (estrofe completa)

**16:30** - Validação final
- Overall Score: 93.0% (+15% em relação ao início)
- Repetitions: 75.0% (30/40 corretos)
- Erros restantes: padrões incomuns (barras de 3, 8 linhas, múltiplas barras aninhadas)

---

## Resultado Final

| Métrica | Antes | Depois | Meta | Status |
|---------|-------|--------|------|--------|
| Overall Score | 78% | 93.0% | - | ✅ +15% |
| Repetições | 0% | 75.0% | 90%+ | ⚠️ Parcial |

### Casos não resolvidos (10/40):
- Padrões de 3 linhas (1-3 vs 1-4)
- Múltiplas barras aninhadas (3-4, 1-4)
- Estrofes de 8 linhas (1-8 vs 1-4)

### Limitação identificada:
O algoritmo assume padrões fixos (2 linhas para múltiplos segmentos, 4 para único).
Para 90%+ seria necessário OCR para posições exatas de linhas ou ML.
