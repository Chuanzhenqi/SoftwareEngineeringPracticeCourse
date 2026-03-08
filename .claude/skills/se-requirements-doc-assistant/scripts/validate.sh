#!/bin/bash
# Validate se-requirements-doc-assistant skill structure

if [ ! -f SKILL.md ]; then
    echo "SKILL.md not found"
    exit 1
fi

if [ ! -f template.md ]; then
    echo "template.md not found"
    exit 1
fi

if [ ! -d examples ]; then
    echo "examples/ directory not found"
    exit 1
fi

echo "Se Requirements Doc Assistant skill structure is valid"
exit 0
