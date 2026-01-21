# Decisões Técnicas - Plan 03

## Decisões Tomadas

### 1. Abandonar Hough Transform
**Data:** 2026-01-17
**Decisão:** Usar Perfil de Projeção Vertical em vez de Hough Transform
**Motivo:**
- Hough Transform detecta todas as linhas, não apenas barras de repetição
- Acurácia de apenas 5%
- Muitos falsos positivos

### 2. Abordagem Baseada em Engenharia Reversa
**Data:** 2026-01-17
**Decisão:** Analisar hymn_pdf_generator para entender características exatas
**Motivo:**
- Conhecer dimensões exatas das barras
- Conhecer posicionamento relativo ao texto
- Criar detector específico para este formato

### 3. Usar Faixa Lateral (15% da largura)
**Data:** 2026-01-17
**Decisão:** Analisar apenas os primeiros 15% da largura da zona body
**Motivo:**
- Barras estão sempre à esquerda do texto
- Reduz área de análise e falsos positivos
- Simplifica o algoritmo

### 4. Mapeamento Proporcional Y→Linha
**Data:** 2026-01-17
**Decisão:** Usar proporção simples em vez de Tesseract para posições
**Alternativa rejeitada:** pytesseract.image_to_data() para coordenadas
**Motivo:**
- Tesseract retornava coordenadas imprecisas
- Proporção é mais simples e confiável
- Menos dependências

---

## Parâmetros Configuráveis

| Parâmetro | Valor Inicial | Descrição |
|-----------|---------------|-----------|
| `margin_percent` | 0.15 | Largura da faixa de barras (15%) |
| `threshold` | 0.3 | Threshold para detecção de picos |
| `min_height` | 2% | Altura mínima de segmento (filtro ruído) |

---

## Decisões Pendentes

### Tratamento de Linhas em Branco
**Questão:** Como ajustar contagem quando há linhas em branco?
**Opções:**
1. Ignorar linhas em branco na contagem
2. Contar `\n\n` como separador de estrofes
3. Usar altura variável por tipo de linha
**Status:** A decidir durante implementação

### Múltiplas Barras no Mesmo Nível X
**Questão:** Como diferenciar barras sobrepostas verticalmente?
**Opções:**
1. Clustering por coordenada X
2. Análise de perfil horizontal também
3. Ignorar (aceitar merge de barras adjacentes)
**Status:** A decidir durante testes
