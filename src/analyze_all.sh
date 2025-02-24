# !/bin/bash

EXTENSIONS_DIR="/home/minhyuk/Desktop/Download_extension/Extensions"
ANALYZER="/home/minhyuk/Desktop/ChromeExtension_Analysis/src/analyzer"

find "$EXTENSIONS_DIR" -type f -name "*zip" | while IFS= read -r zip_file; do
    echo "Analyzing: $zip_file"
    "$ANALYZER" "$zip_file"
done