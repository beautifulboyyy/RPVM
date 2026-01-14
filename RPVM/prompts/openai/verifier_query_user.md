Original Question: {question}

Plan to Verify: {plan}

## Task
Extract the core relationship from the Original Question and generate a search query to verify the Plan.

## Rules
1. DO NOT include names/values from the Plan in your query
2. Use authoritative entities from the Original Question as anchors
3. Generate a query in the form: "Who/What {{relation}} {{entity}}?" or just "{{relation}} {{entity}}"
4. Focus on the relationship the Plan is trying to verify

## Example

**Input:**
Question: "Who is the mother of the director of film Polish-Russian War?"
Plan: "The director of Polish-Russian War is Aleksander Ford."

**Output:**
Query: "Who directed Polish-Russian War?"

---

**Input:**
Question: "{question}"
Plan: "{plan}"

**Output:**
Query:
