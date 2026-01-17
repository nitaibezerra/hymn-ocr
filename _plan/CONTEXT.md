# Contexto Técnico - Hymn OCR

Este documento contém o contexto técnico necessário para retomar a execução do projeto.

---

## Objetivo do Projeto

Criar uma ferramenta CLI que converte PDFs de hinários (gerados pelo `hymn_pdf_generator`) em arquivos YAML estruturados. A solução deve ser **100% gratuita**, usando OCR (Tesseract) e visão computacional (OpenCV) em vez de LLMs pagos.

---

## PDF de Referência

**Localização:** `/Users/nitai/Dropbox/dev-mgi/hyms-platform/hymn_pdf_generator/example/selecao_aniversario_ingrid.pdf`

**Características:**
- 50 páginas
- 40 hinos
- Página 1: Capa
- Páginas 2-50: Hinos (alguns ocupam múltiplas páginas)

**YAML Original:** `/Users/nitai/Dropbox/dev-mgi/hyms-platform/hymn_pdf_generator/example/selecao_aniversario_ingrid.yaml`

---

## Estrutura Visual de uma Página de Hino

```
┌─────────────────────────────────────────────────┐
│           01. Disciplina (62)                   │  ← HEADER
│  ─────────────────────────────────────────────  │  ← Linha horizontal
│           Ofertado a X - Valsa                  │  ← METADATA
│                                                 │
│  │ Santa Maria                                  │  ← CORPO com barra
│  │ O caminho da disciplina                      │
│  │ Vem chegando noite e dia                     │
│  │ Como a luz de um clarão                      │
│                                                 │
│                   ✡                             │  ← SÍMBOLO
│                         (18/01/2020)            │  ← DATA
│                                            1    │  ← Página
└─────────────────────────────────────────────────┘
```

---

## Padrões Regex Definidos

```python
# Header: "NN. Título (original)" ou "NN. Título"
HEADER_PATTERN = r'^(\d+)\.\s+(.+?)(?:\s*\((\d+)\))?\s*$'

# Data no formato DD/MM/YYYY
DATE_PATTERN = r'\((\d{2})/(\d{2})/(\d{4})\)'

# Oferecimento: "Ofertado a/ao/à Nome"
OFFERED_PATTERN = r'[Oo]fertado\s+(?:a|ao|à)\s+(.+?)(?:\s*-\s*|\s*$)'

# Estilos musicais
STYLE_KEYWORDS = ['Valsa', 'Marcha', 'Mazurca', 'Bolero']

# Instruções especiais
INSTRUCTION_PATTERN = r'(?:[Ee]m pé|[Ss]em instrumentos|[Ss]entados?)'
```

---

## Algoritmos Principais

### 1. Classificação de Página

```python
def classify_page(image, ocr_text: str) -> PageType:
    """
    - COVER: primeira página, imagem de fundo
    - NEW_HYMN: tem header "NN. Título"
    - CONTINUATION: não tem header (continuação de hino)
    - BLANK: página em branco
    """
```

### 2. Detecção de Zonas (OpenCV)

```python
def detect_zones(image: np.ndarray) -> dict:
    """
    Divide página em:
    - header: acima da linha horizontal
    - metadata: logo abaixo da linha
    - body: corpo principal
    - footer: símbolo + data (últimos 20%)
    """
```

### 3. Detecção de Barras de Repetição (Hough Transform)

```python
def detect_repetition_bars(image: np.ndarray, text_lines: list) -> str:
    """
    1. Detectar bordas (Canny)
    2. Hough Transform para linhas
    3. Filtrar verticais na margem esquerda (x < 15% width)
    4. Mapear y-coords para linhas de texto
    """
```

### 4. Merge Multi-Página

```python
def merge_multipage_hymns(pages_data: list[dict]) -> list[dict]:
    """
    Combina CONTINUATION com hino anterior.
    Ajusta repetições para linhas corretas.
    """
```

---

## Dependências de Sistema

```bash
# Já instalados em 2026-01-17
brew install poppler          # pdfinfo, pdftoppm
brew install tesseract        # OCR engine
brew install tesseract-lang   # Pacotes de idioma (inclui português)
```

**Versões instaladas:**
- tesseract 5.5.2
- poppler 26.01.0

---

## Imagens de Teste Disponíveis

Localização: `/Users/nitai/Dropbox/dev-mgi/hyms-platform/hymn-ocr/tests/fixtures/images/`

| Arquivo | Descrição | Uso nos Testes |
|---------|-----------|----------------|
| page_01.png | Capa do hinário | test_zone_detector (is_cover) |
| page_02.png | Hino 01. Disciplina | test_ocr, test_zone, test_repetition |
| page_03.png | Hino 02 | test_zone, test_parser |
| page_16.png | Início de hino multi-página | test_merger |
| page_17.png | Continuação | test_merger, test_zone (continuation) |
| page_50.png | Último hino | test_pipeline |

---

## Estrutura de Dados (Pydantic Models)

```python
class PageType(Enum):
    COVER = "cover"
    NEW_HYMN = "new_hymn"
    CONTINUATION = "continuation"
    BLANK = "blank"

class Hymn(BaseModel):
    number: int
    title: str
    text: str
    original_number: Optional[int] = None
    style: Optional[str] = None
    offered_to: Optional[str] = None
    extra_instructions: Optional[str] = None
    repetitions: Optional[str] = None
    received_at: Optional[str] = None  # YYYY-MM-DD

class HymnBook(BaseModel):
    name: str
    owner_name: str
    intro_name: Optional[str] = None
    hymns: List[Hymn]
```

---

## Decisões de Arquitetura

1. **Separação de responsabilidades**: Cada módulo faz uma única coisa
2. **Zonas antes de OCR**: Extrair zonas com OpenCV, depois OCR por zona
3. **DPI 300**: Resolução suficiente para OCR de qualidade
4. **Merge no final**: Processar todas as páginas primeiro, depois merge

---

## Thresholds Iniciais (OpenCV)

```python
# Detecção de bordas (Canny)
CANNY_THRESHOLD_LOW = 50
CANNY_THRESHOLD_HIGH = 150

# Hough Transform para linhas
HOUGH_THRESHOLD = 50
HOUGH_MIN_LINE_LENGTH = 30
HOUGH_MAX_LINE_GAP = 10

# Margem esquerda para barras de repetição
LEFT_MARGIN_PERCENT = 0.15

# Footer começa em
FOOTER_START_PERCENT = 0.80
```

Estes valores podem precisar de ajuste na Fase 5.

---

## Comandos Úteis

```bash
# Instalar projeto
cd /Users/nitai/Dropbox/dev-mgi/hyms-platform/hymn-ocr
poetry install

# Rodar testes
poetry run pytest -v

# Rodar com cobertura
poetry run pytest --cov=hymn_ocr --cov-report=html

# Testar CLI
poetry run hymn-ocr convert ../hymn_pdf_generator/example/selecao_aniversario_ingrid.pdf --preview

# Debug de imagem específica
poetry run python -c "
from hymn_ocr.zone_detector import detect_zones
from hymn_ocr.ocr_engine import ocr_zone
import cv2
img = cv2.imread('tests/fixtures/images/page_02.png')
zones = detect_zones(img)
print(zones)
"
```

---

## Links Úteis

- [Tesseract Docs](https://tesseract-ocr.github.io/)
- [OpenCV Hough Lines](https://docs.opencv.org/4.x/d9/db0/tutorial_hough_lines.html)
- [pdf2image](https://pypi.org/project/pdf2image/)
- [Pydantic](https://docs.pydantic.dev/)
