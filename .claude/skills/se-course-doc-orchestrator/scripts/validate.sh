#!/bin/bash
# Validate se-course-doc-orchestrator skill structure

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

echo "Se Course Doc Orchestrator skill structure is valid"
exit 0
