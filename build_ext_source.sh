#!/bin/bash

# Script to package the extension source code for browser extension review.
# This zips the necessary source files while excluding build artifacts.

# The name of the output zip file
ZIP_NAME="quranai-ext-source.zip"

# Clean up any existing zip
rm -f "$ZIP_NAME"

echo "Packaging extension source for review into $ZIP_NAME..."

# List of files/directories to include:
# - package.json and package-lock.json (for dependencies)
# - rollup.config.mjs (for the build process)
# - src/frontend/ (all source files including READMEs)

# Using wildcards for exclusions to catch all build outputs and sourcemaps.
zip -r "$ZIP_NAME" \
  package.json \
  package-lock.json \
  rollup.config.mjs \
  src/frontend/ \
  -x "*bundle.js*" \
  -x "*bundle.css*" \
  -x "*/.DS_Store" \
  -x "*/__pycache__/*" \
  -x "*/.git/*" \
  -x "*/node_modules/*"

echo "Done! Zip file created: $ZIP_NAME"
echo "To build from this source:"
echo "1. Unzip $ZIP_NAME"
echo "2. Run: npm install"
echo "3. Run: npm run build"
