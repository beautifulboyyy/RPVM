Verify this statement using the documents.

Statement: {plan}

Documents:
{docs_text}

OUTPUT RULES:
- You MUST provide both Verdict AND Corrected lines
- If CONTRADICTED, extract the CORRECT information from documents
- If you cannot find the correct answer, output "Corrected: Unknown"
- Do NOT output any explanation, only the two lines

Example outputs:
Verdict: SUPPORTED
Corrected: The director of film X is John Smith

Verdict: CONTRADICTED
Corrected: The director of film X is Jane Doe

Verdict: INSUFFICIENT
Corrected: The director of film X is Unknown

Output ONLY:
Verdict: [SUPPORTED|CONTRADICTED|INSUFFICIENT]
Corrected: [statement from documents or Unknown]
