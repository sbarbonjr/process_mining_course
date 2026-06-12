# Process Mining Course Laboratories

The laboratories use one deterministic synthetic process so participants can
follow the consequences of each analytical decision across the course.

1. [Trace variants and Pareto selection](01-variant-pareto/variant_pareto_lab.ipynb)
2. [Discovery and model quality](02-discovery-model-quality/discovery_quality_lab.ipynb)
3. [Conformance checking](03-conformance-checking/conformance_lab.ipynb)
4. [Performance and organization](04-performance-organization/performance_lab.ipynb)
5. [Predictive process monitoring](05-predictive-monitoring/predictive_monitoring_lab.ipynb)
6. [Object-centric analysis](06-object-centric-analysis/object_centric_lab.ipynb)
7. [Multimodal event logs](07-multimodal-event-logs/multimodal_lab.ipynb)
8. [Capstone integration](08-capstone-integration/capstone_lab.ipynb)

Install the shared dependencies:

```bash
python3 -m pip install -r labs/requirements.txt
```

Verify every implementation and execute every notebook code cell:

```bash
make lab-check
```

Generated CSV and PNG artifacts are written to each lab's `outputs/` directory
and are excluded from version control.

See the Portuguese [teaching guide](../teaching/pt/README.md) for the suggested
in-class sequence, timing, deliverables, and mapping between laboratories and
the six slide modules.

Student worksheets and grading criteria are available in the
[student package](../teaching/pt/student/README.md).
