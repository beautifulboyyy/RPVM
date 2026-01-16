Based on the retrieved documents, verify and COMPLETE the following statement.

Statement to verify: {plan}

Retrieved Documents:
{docs_text}

# Verification Rules:

## 1. INFORMATION COMPLETION (Critical)
If the original statement contains a vague guess and the document provides EXACT information, you MUST fill in the details:

**Examples:**
- Statement: "The director died in a specific year." → Document: "died Dessau, 12 June 1516"
  → Corrected Statement: "Ernest I, Prince of Anhalt-Dessau died on 12 June 1516."

- Statement: "He won a specific award." → Document: "two-time Myanmar Motion Picture Academy Awards-winning"
  → Corrected Statement: "Maung Wunna won the Myanmar Motion Picture Academy Awards."

- Statement: "The director was born in a specific year." → Document: "born January 20, 1946"
  → Corrected Statement: "David Lynch was born on January 20, 1946."

## 2. ENTITY GROUNDING
Ensure all names, dates, titles, and plural forms are extracted DIRECTLY from the document:
- "Awards" ≠ "Award" (plural matters)
- "12 June 1516" ≠ "1516" (full date preferred)
- "David Lynch" ≠ "the director" (use actual names)

## 3. Verdict Definitions

| Verdict | Condition |
|---------|-----------|
| **SUPPORTED** | Documents confirm the statement with matching details |
| **CONTRADICTED** | Documents provide different information → provide corrected version |
| **INSUFFICIENT** | Documents do NOT mention the entities at all |

## 4. STRICT REQUIREMENTS
- If the document mentions any relevant name, date, or award → you CANNOT use INSUFFICIENT
- Always extract the MOST GRANULAR information available (full dates over years, full names over pronouns)
- If the statement was vague but document has details → use CONTRADICTED with completed information

# Response Format:
Verdict: [SUPPORTED/CONTRADICTED/INSUFFICIENT]
Corrected Statement: [The full factual statement with exact names, dates, and complete details extracted from the document]
Evidence: [Quote the specific phrase from the document that supports your verdict]

Your response:
