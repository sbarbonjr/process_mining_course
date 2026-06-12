# Guia de ensino

Este diretório conecta os seis módulos de slides aos oito laboratórios do curso.
Os roteiros assumem encontros de 4 horas, com pausas incluídas, e podem ser
adaptados para aulas de 2 horas dividindo cada módulo em suas duas unidades.

## Mapa do curso

| Módulo | Unidades | Slides | Prática principal | Extensão ou entrega |
| --- | --- | --- | --- | --- |
| 1. Fundamentos | 1-2 | `module-01-foundations.pdf` | Inspeção orientada do log usado no Lab 01 | Formulação da pergunta e contrato semântico |
| 2. Engenharia e exploração | 3-4 | `module-02-log-engineering-exploration.pdf` | Lab 01: variantes e Pareto | Relatório de profiling e escolha de encoding |
| 3. Modelagem e descoberta | 5-6 | `module-03-modeling-discovery.pdf` | Lab 02: descoberta e qualidade | Shortlist de modelos candidatos |
| 4. Avaliação e conformidade | 7-8 | `module-04-evaluation-conformance.pdf` | Labs 02 e 03 | Decisão Pareto e diagnóstico de desvios |
| 5. Aprimoramento e organização | 9-10 | `module-05-enhancement-organization.pdf` | Lab 04: desempenho e organização | Tabela de features para o Lab 05 |
| 6. Objetos e entrega | 11-12 | `module-06-object-centric-delivery.pdf` | Labs 05 e 06 | Lab 07 como extensão e Lab 08 como capstone |

Os caminhos dos slides existem em `slides/en/` e `slides/pt/`. Os nomes dos
PDFs são iguais nos dois idiomas.

## Sequência de laboratórios

1. `labs/01-variant-pareto/variant_pareto_lab.ipynb`
2. `labs/02-discovery-model-quality/discovery_quality_lab.ipynb`
3. `labs/03-conformance-checking/conformance_lab.ipynb`
4. `labs/04-performance-organization/performance_lab.ipynb`
5. `labs/05-predictive-monitoring/predictive_monitoring_lab.ipynb`
6. `labs/06-object-centric-analysis/object_centric_lab.ipynb`
7. `labs/07-multimodal-event-logs/multimodal_lab.ipynb`
8. `labs/08-capstone-integration/capstone_lab.ipynb`

## Modelo de avaliação

| Evidência | Frequência | Peso sugerido |
| --- | ---: | ---: |
| Exit ticket conceitual | 6 | 10% |
| Entregas dos Labs 01-07 | 7 | 30% |
| Revisão por pares | 2 | 10% |
| Capstone reproduzível | 1 | 35% |
| Apresentação do capstone | 1 | 15% |

Cada entrega deve ser avaliada por quatro critérios: validade semântica,
reprodutibilidade, interpretação e adequação da decisão. Executar o código sem
justificar as escolhas não é evidência suficiente.

## Preparação comum

Antes do primeiro encontro:

```bash
python3 -m pip install -r labs/requirements.txt
make lab-check
make all
```

O professor deve executar os notebooks antecipadamente, manter os outputs de
demonstração disponíveis e preparar uma versão de contingência em PDF ou CSV.

## Roteiros

- [Módulo 1: Fundamentos](module-01-foundations.md)
- [Módulo 2: Engenharia e exploração](module-02-log-engineering-exploration.md)
- [Módulo 3: Modelagem e descoberta](module-03-modeling-discovery.md)
- [Módulo 4: Avaliação e conformidade](module-04-evaluation-conformance.md)
- [Módulo 5: Aprimoramento e organização](module-05-enhancement-organization.md)
- [Módulo 6: Objetos e entrega](module-06-object-centric-delivery.md)

## Material do estudante

As fichas de atividades, regras de entrega e rubricas estão no
[pacote do estudante](student/README.md).
