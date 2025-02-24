#!/bin/bash

EXTENSIONS_DIR="/Users/minhyuk/Desktop/csf/extension_samples"
ANALYZER="/Users/minhyuk/Desktop/csf/ChromeExtension_Analysis/src/analyzer"

echo "Analyzing all extensions in: $EXTENSIONS_DIR"
"$ANALYZER" "$EXTENSIONS_DIR"