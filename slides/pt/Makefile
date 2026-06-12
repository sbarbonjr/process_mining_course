TEX = slides.tex
PDF = slides.pdf
MODULE_TEX = \
	module-01-foundations.tex \
	module-02-log-engineering-exploration.tex \
	module-03-modeling-discovery.tex \
	module-04-evaluation-conformance.tex \
	module-05-enhancement-organization.tex \
	module-06-object-centric-delivery.tex
MODULE_PDF = $(MODULE_TEX:.tex=.pdf)

.PHONY: all modules clean

all: $(PDF) modules

modules: $(MODULE_PDF)

$(PDF): $(TEX)
	latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX)

module-%.pdf: module-%.tex $(TEX)
	latexmk -pdf -interaction=nonstopmode -halt-on-error $<

clean:
	latexmk -C $(TEX)
	@for file in $(MODULE_TEX); do latexmk -C "$$file"; done
