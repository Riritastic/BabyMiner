from miner.parser import extract_metadata_fields, parse_workflow_md

SAMPLE_MD = """---
title: Daily Code Review
engine: gpt-4o
description: Automated review workflow
---
# Workflow Body
This is the markdown content of the agentic workflow.
"""


def test_parse_workflow_md():
    metadata, body = parse_workflow_md(SAMPLE_MD)

    assert metadata["title"] == "Daily Code Review"
    assert metadata["engine"] == "gpt-4o"
    assert "Workflow Body" in body


def test_extract_metadata_fields():
    metadata, _ = parse_workflow_md(SAMPLE_MD)
    extracted = extract_metadata_fields(metadata)

    assert extracted["title"] == "Daily Code Review"
    assert extracted["engine"] == "gpt-4o"
    assert extracted["raw_frontmatter_json"] is not None