all: main.pdf

main.pdf: main.tex references.bib figures/* data/*
	tectonic main.tex

supplement: supplement/supplement.pdf

supplement/supplement.pdf: supplement/supplement.tex references.bib data/*
	cd supplement && tectonic supplement.tex

clean:
	rm -f main.pdf main.aux main.bbl main.blg main.log main.out main.spl
	rm -f supplement/supplement.pdf supplement/supplement.aux supplement/supplement.bbl supplement/supplement.blg supplement/supplement.log supplement/supplement.out

.PHONY: all supplement clean
