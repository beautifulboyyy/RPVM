## Input Information

**Original Question**: {question}

**Current Plan (Verified)**: {plan}

**Retrieved Documents**:
{docs_text}

**Existing Memory**:
{memory}

## Task

The plan above has been VERIFIED by the evidence in the documents.
Your task is to:
1. Extract the key factual information from the documents that supports the plan
2. Refine and compress this into a path-level knowledge statement
3. Ensure it can be directly used for subsequent reasoning

## Requirements

- Start with "First-hop reasoning:" or "Second-hop reasoning:" (infer the hop number from context)
- Bind the evidence to the reasoning path
- Make it concise but preserve critical facts
- Ensure it connects logically with existing Memory

## Output

[Refined Path-Level Knowledge]:
