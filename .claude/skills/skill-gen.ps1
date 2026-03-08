# skill-gen.ps1
# Generate Claude Code skill template structure
# Usage: .\skill-gen.ps1 my-skill [-OutputDir path]

param(
    [Parameter(Mandatory=$true)]
    [string]$SkillName,
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "."
)

# Validate skill name format
if ($SkillName -match '[^a-z0-9-]') {
    Write-Error "Skill name must contain only lowercase letters, numbers, and hyphens"
    exit 1
}

# Determine paths
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created base directory: $OutputDir"
}

$baseDir = (Resolve-Path -Path $OutputDir -ErrorAction Stop).ProviderPath
$skillDir = Join-Path $baseDir $SkillName

# Check if skill already exists
if (Test-Path $skillDir) {
    Write-Error "Skill directory already exists: $skillDir"
    exit 1
}

# Create skill directory structure
New-Item -ItemType Directory -Path $skillDir | Out-Null
New-Item -ItemType Directory -Path "$skillDir/examples" | Out-Null
New-Item -ItemType Directory -Path "$skillDir/scripts" | Out-Null
New-Item -ItemType Directory -Path "$skillDir/references" | Out-Null
New-Item -ItemType Directory -Path "$skillDir/assets" | Out-Null

Write-Host "Created skill directory structure inside $baseDir"

# Convert skill name to title case
$titleWords = $SkillName -split '-' | ForEach-Object { $_.Substring(0,1).ToUpper() + $_.Substring(1) }
$skillTitle = $titleWords -join ' '

# Create SKILL.md
$skillMdContent = @"
---
name: $SkillName
description: [TODO: Complete description of what this skill does and when to use it]
---

# $skillTitle

## Overview

[TODO: Brief explanation of the skill's purpose]

## Workflow

[TODO: Step-by-step workflow or decision tree]

## Examples

[TODO: Usage examples]

## Resources

### scripts/
- Executable code for automation and deterministic tasks

### references/
- Documentation and reference materials

### assets/
- Templates, boilerplate files, or static assets
"@

Set-Content -Path "$skillDir/SKILL.md" -Value $skillMdContent
Write-Host "Created SKILL.md"

# Create template.md
$templateContent = @"
# Template for $skillTitle

[TODO: Define the template that Claude should use to generate outputs]

## Fields

- **Input**: [Description]
- **Output**: [Description]

## Structure

[TODO: Define expected structure or format]
"@

Set-Content -Path "$skillDir/template.md" -Value $templateContent
Write-Host "Created template.md"

# Create example output
$exampleContent = @"
# Example Output for $skillTitle

This file demonstrates the expected format and structure of outputs.

## Sample Input
[TODO: Show sample input]

## Sample Output
[TODO: Show expected output based on template]
"@

Set-Content -Path "$skillDir/examples/sample.md" -Value $exampleContent
Write-Host "Created examples/sample.md"

# Create validation script
$validateScript = @"
#!/bin/bash
# Validate $SkillName skill structure

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

echo "$skillTitle skill structure is valid"
exit 0
"@

Set-Content -Path "$skillDir/scripts/validate.sh" -Value $validateScript
Write-Host "Created scripts/validate.sh"

Write-Host "`nSkill '$SkillName' initialized successfully!"
Write-Host "Location: $skillDir`n"
Write-Host "Next steps:"
Write-Host "1. Edit SKILL.md to complete the TODO items"
Write-Host "2. Create template.md with your template structure"
Write-Host "3. Add examples in examples/sample.md"
Write-Host "4. Put docs in references/ and reusable files in assets/"
Write-Host "5. Add helper scripts in scripts/ if needed"