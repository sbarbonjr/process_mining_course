PYTHON ?= python3
LANG_DIRS = slides/en slides/pt
LAB_CHECKS = \
	labs/01-variant-pareto/variant_pareto_lab.py \
	labs/02-discovery-model-quality/discovery_quality_lab.py \
	labs/03-conformance-checking/conformance_lab.py \
	labs/04-performance-organization/performance_lab.py \
	labs/05-predictive-monitoring/predictive_monitoring_lab.py \
	labs/06-object-centric-analysis/object_centric_lab.py \
	labs/07-multimodal-event-logs/multimodal_lab.py \
	labs/08-capstone-integration/capstone_lab.py

.PHONY: all slides-en slides-pt modules-en modules-pt lab-check clean

all: slides-en slides-pt

slides-en:
	$(MAKE) -C slides/en all

slides-pt:
	$(MAKE) -C slides/pt all

modules-en:
	$(MAKE) -C slides/en modules

modules-pt:
	$(MAKE) -C slides/pt modules

lab-check:
	@for lab in $(LAB_CHECKS); do \
		MPLBACKEND=Agg MPLCONFIGDIR=/tmp/process-mining-matplotlib $(PYTHON) "$$lab" --check || exit 1; \
	done
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp/process-mining-matplotlib $(PYTHON) labs/check_notebooks.py

clean:
	@for directory in $(LANG_DIRS); do $(MAKE) -C "$$directory" clean; done
