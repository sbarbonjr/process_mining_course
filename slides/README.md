# Course Slides

- `en/`: canonical English Beamer source, complete deck, and six module decks.
- `pt/`: Portuguese Beamer source, complete deck, and six module decks.

Build both languages from the repository root:

```bash
make all
```

Build one language:

```bash
make slides-en
make slides-pt
```

The Portuguese source is generated from the English source with:

```bash
python3 tools/translate_slides_pt.py
```

After regeneration, compile and inspect the Portuguese deck because translated
text can require language-specific layout adjustments.

The six module decks are connected to the laboratories through the Portuguese
[teaching guide](../teaching/pt/README.md).
