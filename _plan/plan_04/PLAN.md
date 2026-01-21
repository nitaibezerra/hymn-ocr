# Plano: Detecção de Barras Aninhadas (Nested Bars)

**Projeto:** hymn-ocr
**Data:** 2026-01-20
**Objetivo:** Detectar barras aninhadas como "1-2, 3-4, 1-4"

---

## Problema Identificado

O algoritmo atual (v2) detecta segmentos contínuos mas **não diferencia barras aninhadas**:

```
Padrão Visual:              Detecção Atual:     Esperado:
║║  Linha 1  (barra dupla)  → Segmento único    → "1-2, 3-4, 1-4"
║║  Linha 2  (barra dupla)    (1-4)
║   (gap interno)
║║  Linha 3  (barra dupla)
║║  Linha 4  (barra dupla)
```

### Causa Raiz

No PDF, barras são renderizadas em **níveis diferentes de X**:
- **Level 1** (barras internas): x = -6pt do texto
- **Level 2** (barra externa): x = -12pt do texto

O perfil vertical SOMA todas as barras, perdendo a informação de que há duas colunas distintas.

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

```python
def extract_bar_region(image: np.ndarray, margin_percent: float = 0.15):
    """Extrai os primeiros 15% da largura (onde estão as barras)."""
    h, w = image.shape[:2]
    bar_width = int(w * margin_percent)
    return image[:, :bar_width]
```

#### Etapa 2: Perfil de Projeção Vertical

```python
def vertical_projection_profile(bar_region: np.ndarray) -> np.ndarray:
    """
    Para cada linha Y, conta quantos pixels pretos existem.
    Linhas com barras terão picos de intensidade.
    """
    gray = cv2.cvtColor(bar_region, cv2.COLOR_BGR2GRAY)
    binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)[1]

    # Soma horizontal: cada Y tem um valor de "quantidade de preto"
    profile = np.sum(binary, axis=1)
    return profile
```

**Visualização do perfil:**
```
Y      Perfil (soma horizontal)
0      ░░░░░░
10     ░░░░░░
20     ████████████  ← Início da barra
30     ████████████
40     ████████████
50     ████████████  ← Fim da barra
60     ░░░░░░
70     ░░░░░░
80     ████████  ← Outra barra (menor)
90     ████████
100    ░░░░░░
```

#### Etapa 3: Detectar Segmentos Contíguos

```python
def find_bar_segments(profile: np.ndarray, threshold: float = 0.3) -> list[tuple[int, int]]:
    """
    Encontra segmentos contíguos onde profile > threshold * max.
    Retorna lista de (y_start, y_end).
    """
    max_val = np.max(profile)
    if max_val == 0:
        return []

    # Binariza: 1 onde há barra, 0 onde não há
    is_bar = (profile > threshold * max_val).astype(int)

    # Encontra transições (início e fim de cada segmento)
    diff = np.diff(is_bar, prepend=0, append=0)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    return list(zip(starts, ends))
```

#### Etapa 4: Mapear Y → Número de Linha

**Abordagem diferente:** Em vez de usar Tesseract para posições, usar contagem de linhas no texto OCR.

```python
def map_y_to_line_number(y_coord: int, body_zone: Zone, text: str) -> int:
    """
    Mapeia coordenada Y para número de linha baseado em:
    1. Altura total da zona de texto
    2. Número de linhas no texto OCR
    3. Posição proporcional
    """
    lines = [l for l in text.split('\n') if l.strip()]
    num_lines = len(lines)

    # Posição relativa dentro da zona do body
    zone_height = body_zone.y_end - body_zone.y_start
    relative_y = y_coord - body_zone.y_start

    # Linha proporcional (1-indexed)
    line_number = int((relative_y / zone_height) * num_lines) + 1
    return max(1, min(line_number, num_lines))
```

---

## Implementação

### Arquivo: `src/hymn_ocr/repetition_detector_v2.py` (NOVO)

```python
"""Detection of repetition bars using vertical projection profile."""

from dataclasses import dataclass
from typing import Optional
import cv2
import numpy as np

from hymn_ocr.zone_detector import Zone, extract_zone


@dataclass
class BarSegment:
    """A detected vertical bar segment."""
    y_start: int
    y_end: int
    intensity: float  # Força do sinal (para debug)


def detect_repetition_bars_v2(
    image: np.ndarray,
    body_zone: Zone,
    body_text: str,
    margin_percent: float = 0.15,
    threshold: float = 0.3,
) -> Optional[str]:
    """
    Detecta barras de repetição usando perfil de projeção vertical.

    Args:
        image: Imagem BGR completa da página
        body_zone: Zona do corpo do hino (para delimitar área)
        body_text: Texto OCR do corpo (para contar linhas)
        margin_percent: Percentual da largura para zona de barras
        threshold: Threshold para detecção de picos

    Returns:
        String no formato "1-4, 5-8" ou None
    """
    # 1. Extrair zona do body
    body_image = extract_zone(image, body_zone)

    # 2. Extrair faixa lateral (onde estão as barras)
    h, w = body_image.shape[:2]
    bar_width = int(w * margin_percent)
    bar_region = body_image[:, :bar_width]

    # 3. Calcular perfil de projeção vertical
    gray = cv2.cvtColor(bar_region, cv2.COLOR_BGR2GRAY)
    binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)[1]
    profile = np.sum(binary, axis=1)

    # 4. Encontrar segmentos contíguos
    segments = find_bar_segments(profile, threshold)

    if not segments:
        return None

    # 5. Mapear para números de linha
    lines = [l for l in body_text.split('\n') if l.strip()]
    num_lines = len(lines)

    if num_lines == 0:
        return None

    repetitions = []
    for y_start, y_end in segments:
        start_line = map_y_to_line(y_start, h, num_lines)
        end_line = map_y_to_line(y_end, h, num_lines)

        if start_line <= end_line:
            repetitions.append(f"{start_line}-{end_line}")

    return ", ".join(repetitions) if repetitions else None


def find_bar_segments(profile: np.ndarray, threshold: float) -> list[tuple[int, int]]:
    """Encontra segmentos contíguos no perfil."""
    max_val = np.max(profile)
    if max_val == 0:
        return []

    is_bar = (profile > threshold * max_val).astype(int)
    diff = np.diff(is_bar, prepend=0, append=0)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    # Filtrar segmentos muito curtos (ruído)
    min_height = len(profile) * 0.02  # Mínimo 2% da altura
    segments = [(s, e) for s, e in zip(starts, ends) if e - s > min_height]

    return segments


def map_y_to_line(y: int, total_height: int, num_lines: int) -> int:
    """Mapeia Y para número de linha (1-indexed)."""
    line = int((y / total_height) * num_lines) + 1
    return max(1, min(line, num_lines))
```

### Modificar: `src/hymn_ocr/pipeline.py`

```python
# Substituir a chamada atual:
# page_data.repetitions = None  # Desabilitado

# Por:
from hymn_ocr.repetition_detector_v2 import detect_repetition_bars_v2

if body_text and zones.body:
    page_data.repetitions = detect_repetition_bars_v2(
        cv2_image,
        zones.body,
        body_text,
    )
```

---

## Verificação

### Script de Debug Visual

```bash
# Criar script para visualizar detecção
poetry run python scripts/debug_repetition.py page_image.png
```

```python
# scripts/debug_repetition.py
"""Visualiza detecção de barras de repetição."""
import cv2
import matplotlib.pyplot as plt
from hymn_ocr.repetition_detector_v2 import vertical_projection_profile

def debug_detection(image_path: str):
    image = cv2.imread(image_path)
    # ... extrair zona ...
    profile = vertical_projection_profile(bar_region)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    axes[0].set_title("Original")

    axes[1].imshow(bar_region, cmap='gray')
    axes[1].set_title("Bar Region (15%)")

    axes[2].plot(profile, range(len(profile)))
    axes[2].invert_yaxis()
    axes[2].set_title("Vertical Profile")

    plt.savefig("debug_output.png")
```

### Validação

```bash
# Re-gerar YAML
poetry run hymn-ocr convert example.pdf -o /tmp/test_output.yaml

# Validar contra original
poetry run python scripts/validate_ocr.py \
    /tmp/test_output.yaml \
    ../hymn_pdf_generator/example/selecao_aniversario_ingrid.yaml
```

### Critérios de Sucesso

| Métrica | Meta | Antes |
|---------|------|-------|
| Repetições | 90%+ | 5% |

---

## Arquivos a Modificar/Criar

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `src/hymn_ocr/repetition_detector_v2.py` | CRIAR | Nova implementação |
| `src/hymn_ocr/pipeline.py` | MODIFICAR | Usar detector v2 |
| `scripts/debug_repetition.py` | CRIAR | Visualização debug |
| `tests/test_repetition_v2.py` | CRIAR | Testes unitários |

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Linhas em branco afetam mapeamento | Ajustar contagem considerando `\n\n` |
| Barras muito finas não detectadas | Reduzir threshold |
| Múltiplas barras no mesmo nível | Usar clustering por X |
| Font size variável | Usar proporção em vez de valores absolutos |

---

## Plano de Execução (ATUALIZADO - Detecção de Barras Aninhadas)

---

## Nova Abordagem: Análise Multi-Coluna

### Insight Chave

Em vez de somar TODA a margem horizontalmente, analisar **colunas separadas**:

```
Margem Esquerda (180px @ 300dpi):
│  Coluna 2  │  Coluna 1  │  Texto...
│  (x=0-90)  │  (x=90-180)│
│            │            │
│  Level 2   │  Level 1   │  Linha 1: barra dupla (ambas colunas)
│  (externa) │  (interna) │  Linha 2: barra dupla (ambas colunas)
│     ║      │            │  Linha 2.5: só externa (gap interno)
│  Level 2   │  Level 1   │  Linha 3: barra dupla (ambas colunas)
│  (externa) │  (interna) │  Linha 4: barra dupla (ambas colunas)
```

### Algoritmo Proposto

#### Etapa 1: Dividir Margem em Colunas

```python
def analyze_bar_columns(bar_region: np.ndarray, num_columns: int = 3):
    """
    Divide a região de barras em colunas e analisa cada uma separadamente.

    Colunas (da esquerda para direita):
    - Coluna 0: Level 3+ (mais externa)
    - Coluna 1: Level 2 (externa)
    - Coluna 2: Level 1 (interna, mais próxima do texto)
    """
    h, w = bar_region.shape[:2]
    column_width = w // num_columns

    profiles = []
    for i in range(num_columns):
        col_start = i * column_width
        col_end = (i + 1) * column_width
        column = bar_region[:, col_start:col_end]
        profile = compute_vertical_profile(column)
        profiles.append(profile)

    return profiles  # [profile_level3, profile_level2, profile_level1]
```

#### Etapa 2: Detectar Segmentos por Coluna

```python
def detect_nested_bars(profiles: list[np.ndarray], threshold: float = 0.15):
    """
    Detecta segmentos em cada coluna e identifica padrões aninhados.

    Exemplo para "1-2, 3-4, 1-4":
    - Coluna 1 (interna): segmentos em [1-2] e [3-4]
    - Coluna 2 (externa): segmento em [1-4]
    """
    all_segments = []

    for level, profile in enumerate(profiles):
        segments = find_bar_segments(profile, threshold)
        for seg in segments:
            all_segments.append({
                'level': level,
                'y_start': seg.y_start,
                'y_end': seg.y_end,
            })

    return all_segments
```

#### Etapa 3: Ordenar e Formatar Resultado

```python
def format_repetitions(segments: list[dict], body_height: int, num_lines: int):
    """
    Ordena segmentos e formata como string.

    Regra: Barras internas (level 1) vêm primeiro, depois externas (level 2+).
    Dentro do mesmo nível, ordena por y_start.
    """
    # Ordenar: primeiro por nível (interno primeiro), depois por posição Y
    sorted_segs = sorted(segments, key=lambda s: (s['level'], s['y_start']))

    # Converter para linhas
    result = []
    for seg in sorted_segs:
        start_line = map_y_to_line_v3(seg['y_start'], ...)
        end_line = map_y_to_line_v3(seg['y_end'], ...)
        result.append(f"{start_line}-{end_line}")

    return ", ".join(result)
```

---

## Implementação

### Arquivo: `src/hymn_ocr/repetition_detector_v2.py`

Modificar a função `detect_repetition_bars_v2()`:

```python
def detect_repetition_bars_v2(
    image: np.ndarray,
    body_zone: Zone,
    body_text: str,
) -> Optional[str]:
    """Detecta barras de repetição incluindo barras aninhadas."""

    # ... código existente para extrair bar_region ...

    # NOVO: Analisar colunas separadas
    profiles = analyze_bar_columns(bar_region, num_columns=3)

    # NOVO: Detectar segmentos em cada coluna
    all_segments = []
    for level, profile in enumerate(profiles):
        segments = find_bar_segments(profile, DETECTION_THRESHOLD)
        for seg in segments:
            all_segments.append({
                'level': level,
                'y_start': seg.y_start,
                'y_end': seg.y_end,
            })

    # NOVO: Ordenar (internas primeiro) e formatar
    # Level 0 = mais à esquerda (externa)
    # Level 2 = mais à direita (interna, próxima do texto)
    sorted_segs = sorted(all_segments, key=lambda s: (-s['level'], s['y_start']))

    # Mapear para linhas e formatar
    repetitions = []
    for seg in sorted_segs:
        start_line = map_y_to_line_v3(seg['y_start'], ...)
        end_line = map_y_to_line_v3(seg['y_end'], ...)
        if start_line <= end_line:
            rep = f"{start_line}-{end_line}"
            if rep not in repetitions:  # Evitar duplicatas
                repetitions.append(rep)

    return ", ".join(repetitions) if repetitions else None
```

---

## Visualização Esperada

```
Caso: "1-2, 3-4, 1-4"

Margem dividida em 3 colunas:
┌────────┬────────┬────────┐
│ Col 0  │ Col 1  │ Col 2  │
│(externa)│       │(interna)│
├────────┼────────┼────────┤
│   ░    │   ░    │   █    │ ← Linha 1: só coluna 2 tem barra
│   ░    │   █    │   █    │ ← Linha 1: colunas 1+2 têm barra
│   ░    │   █    │   █    │ ← Linha 2
│   ░    │   █    │   ░    │ ← Gap: só coluna 1 (barra externa)
│   ░    │   █    │   █    │ ← Linha 3
│   ░    │   █    │   █    │ ← Linha 4
│   ░    │   ░    │   ░    │
└────────┴────────┴────────┘

Perfis por coluna:
- Coluna 0: nenhum segmento
- Coluna 1: segmento contínuo (1-4) → barra externa "1-4"
- Coluna 2: dois segmentos (1-2) e (3-4) → barras internas "1-2", "3-4"

Resultado: "1-2, 3-4, 1-4"
```

---

## Arquivos a Modificar

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `src/hymn_ocr/repetition_detector_v2.py` | MODIFICAR | Adicionar análise multi-coluna |
| `scripts/debug_repetition.py` | MODIFICAR | Visualizar perfis por coluna |

---

## Plano de Execução

1. **Modificar** `repetition_detector_v2.py`:
   - Adicionar função `analyze_bar_columns()`
   - Modificar `detect_repetition_bars_v2()` para usar análise multi-coluna
   - Ajustar ordenação (internas primeiro)

2. **Atualizar** `scripts/debug_repetition.py`:
   - Visualizar os 3 perfis separados
   - Mostrar segmentos detectados por coluna

3. **Testar** em casos específicos:
   - Hymn #5 (Flecha): esperado "1-2, 3-4, 1-4"
   - Hymn #29 (Confiar): esperado "3-4, 1-4"

4. **Validar** com script de comparação

---

## Critérios de Sucesso

| Métrica | Atual | Meta |
|---------|-------|------|
| Repetições | 75% (30/40) | 90%+ (36/40) |
| Overall Score | 93% | 95%+ |

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Colunas não alinhadas com níveis reais | Ajustar número de colunas ou largura |
| Barras muito finas perdidas na divisão | Usar overlap entre colunas |
| Níveis > 2 não detectados | Aumentar num_columns para 4-5 |
