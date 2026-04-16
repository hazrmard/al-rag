#!/bin/bash

# Script to build and package the QuranAI browser extension for distribution.
# This runs the build process and zips the final assets required for the Chrome Web Store or Firefox Add-ons.

# The name of the output zip file
ZIP_NAME="public/quranai-extension.zip"

# Clean up any existing zip
rm -f "$ZIP_NAME"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed. Please install Node.js and npm first."
    exit 1
fi

echo "Installing dependencies..."
npm install --silent

echo "Building extension for production..."
npm run build

echo "Packaging extension into $ZIP_NAME..."

# List of files to include in the distribution zip:
# - manifest.json
# - index.html
# - bundle.js
# - bundle.css
# - background.js
# - content.js
# - main.png

# We will zip from within the extension directory to keep the root clean.
# Exclusions:
# - index.js (source file, not needed in distribution)
# - README.md (source documentation, not needed in distribution)
# - *.map (sourcemaps, usually not needed for final store uploads unless requested)
# - .DS_Store (macOS junk)

(cd public/extension && zip -r "../../$ZIP_NAME" \
  manifest.json \
  index.html \
  bundle.js \
  bundle.css \
  background.js \
  content.js \
  main.png \
  -x "*.map" \
  -x "*/.DS_Store")

echo "Done! Zip file created: $ZIP_NAME"
echo "You can now upload $ZIP_NAME to the Chrome Web Store or Firefox Add-ons portal."
