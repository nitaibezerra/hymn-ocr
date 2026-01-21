# Plano: Detecção de Barras de Repetição v2

**Projeto:** hymn-ocr
**Data:** 2026-01-17
**Objetivo:** Reimplementar detecção de barras de repetição baseado em engenharia reversa

---

## Engenharia Reversa do hymn_pdf_generator

### Características Visuais das Barras (ReportLab)

| Propriedade | Valor | Fonte |
|-------------|-------|-------|
| **Espessura** | 0.7 pontos (~1 pixel @ 300dpi) | `VerticalLine.__init__()` |
| **Cor** | Preto (default ReportLab) | Implícito |
| **Posição X** | `-(level * 6pt)` da margem | `_build_vertical_lines()` |
| **Margem esquerda** | 0.5 polegadas (36pt) | `config.py` |

### Cálculo de Posição Y (por linha de texto)

```python
# Constantes de espaçamento (font_size = 14pt default)
y_padding = -8 + resize(-4)     # Offset inicial
one_line = resize(7)            # ~7pt por linha de texto
one_blank_line = resize(8.5)    # ~8.5pt por linha em branco
between_lines = resize(9)       # ~9pt entre linhas

# Cálculo Y para linha N (0-indexed):
y = y_padding - (N * one_line + N * between_lines) - (blanks * one_blank_line)
```

### Sistema de Níveis (múltiplas barras)

```
Texto:                      Barras:
                           Level 2  Level 1
Santa Maria                   |        |
O caminho da disciplina       |        |
Nos ensina e ilumina          |        |
A nossa caminhada             |        |

Por onde vamos               |
Colhendo rosas flores        |
```

- Level 1 = mais próximo do texto (x = -6pt)
- Level 2 = mais à esquerda (x = -12pt)
- Barras no mesmo nível NÃO se sobrepõem verticalmente

---

## Nova Abordagem: Perfil de Projeção Vertical

### Por que Hough Transform falhou

1. Detecta TODAS as linhas (horizontais, diagonais, bordas de texto)
2. Não diferencia barras de repetição de outros elementos
3. Mapeamento Y→linha baseado em Tesseract é impreciso

### Nova Estratégia: Análise de Faixa Lateral

**Insight:** As barras estão em uma região muito específica e previsível.

```
┌─────────────────────────────────────────────┐
│  ZONA DE BARRAS │      ZONA DE TEXTO        │
│  (0-15% width)  │      (15-100% width)      │
│                 │                           │
│       |  |      │  Santa Maria              │
│       |  |      │  O caminho da disciplina  │
│       |  |      │  Nos ensina e ilumina     │
│       |  |      │  A nossa caminhada        │
│                 │                           │
│          |      │  Por onde vamos           │
│          |      │  Colhendo rosas flores    │
└─────────────────────────────────────────────┘
```

### Algoritmo Proposto (4 Etapas)

#### Etapa 1: Extrair Faixa Lateral
- Extrai os primeiros 15% da largura da zona body (onde estão as barras)

#### Etapa 2: Perfil de Projeção Vertical
- Para cada linha Y, conta quantos pixels pretos existem
- Linhas com barras terão picos de intensidade

#### Etapa 3: Detectar Segmentos Contíguos
- Encontra segmentos contíguos onde profile > threshold * max
- Filtra segmentos muito curtos (ruído)

#### Etapa 4: Mapear Y → Número de Linha
- Usa contagem de linhas no texto OCR
- Mapeia proporcionalmente Y para número de linha

---

## Plano de Execução

| Fase | Tarefa | Descrição |
|------|--------|-----------|
| 1 | Criar detector v2 | `repetition_detector_v2.py` |
| 2 | Criar script debug | Visualização do perfil |
| 3 | Testar isoladamente | Imagens individuais |
| 4 | Integrar pipeline | Modificar `pipeline.py` |
| 5 | Validar | Script de comparação |
| 6 | Iterar | Ajustar thresholds |

---

## Arquivos a Modificar/Criar

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `src/hymn_ocr/repetition_detector_v2.py` | CRIAR | Nova implementação |
| `src/hymn_ocr/pipeline.py` | MODIFICAR | Usar detector v2 |
| `scripts/debug_repetition.py` | CRIAR | Visualização debug |
| `tests/test_repetition_v2.py` | CRIAR | Testes unitários |

---

## Critérios de Sucesso

| Métrica | Meta | Antes |
|---------|------|-------|
| Repetições | 90%+ | 5% |
