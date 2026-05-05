#!/bin/bash
set -e

MSG="${1:-update dashboard}"

git add docs/ data/config.json data/products.json data/daily.json data/weight.json scripts/ templates/ README.md SKILL.md .gitignore
git commit -m "$MSG"
git push origin main

echo "✓ Deployed. GitHub Pages обновится через ~30 секунд."
