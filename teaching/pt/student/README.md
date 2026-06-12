# Pacote do estudante

Este pacote contém as atividades avaliativas associadas aos oito notebooks do
curso. Cada ficha orienta a análise, mas não prescreve uma única interpretação.
As respostas devem citar tabelas, métricas, traces ou gráficos produzidos pelo
notebook.

## Antes de começar

```bash
python3 -m pip install -r labs/requirements.txt
make lab-check
```

Use uma cópia limpa do notebook correspondente. Preserve células, parâmetros e
outputs necessários para reproduzir suas conclusões.

## Fichas de laboratório

1. [Variantes e seleção Pareto](worksheets/lab-01-variant-pareto.md)
2. [Descoberta e qualidade de modelos](worksheets/lab-02-discovery-quality.md)
3. [Verificação de conformidade](worksheets/lab-03-conformance.md)
4. [Desempenho e organização](worksheets/lab-04-performance-organization.md)
5. [Monitoramento preditivo](worksheets/lab-05-predictive-monitoring.md)
6. [Análise centrada em objetos](worksheets/lab-06-object-centric.md)
7. [Logs de eventos multimodais](worksheets/lab-07-multimodal.md)
8. [Integração do capstone](worksheets/lab-08-capstone.md)

## Avaliação

- [Rubrica comum dos laboratórios](rubrics/lab-rubric.md)
- [Rubrica do capstone](rubrics/capstone-rubric.md)
- [Rubrica da apresentação](rubrics/presentation-rubric.md)

## Regras de entrega

- Entregue o notebook executável e um relatório curto em PDF ou Markdown.
- Identifique claramente observação, interpretação e recomendação.
- Registre alterações de parâmetros e justificativas.
- Não use informação futura em tarefas preditivas.
- Declare limitações, exclusões e apoio de ferramentas de IA, quando houver.
- Nome sugerido: `sobrenome-lab-XX.ipynb` e `sobrenome-lab-XX.md`.

## Estrutura recomendada do relatório

1. Pergunta e decisão.
2. Dados e representação.
3. Método e parâmetros.
4. Evidências.
5. Interpretação.
6. Limitações.
7. Próxima ação.
