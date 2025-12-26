# RPVM Prompts Collection

All prompts used in the RPVM (Reflective Plan-Verify Memory) system, organized by module.

---

## 1. Planner Module

The Planner generates factual assertions (hypotheses) to break down complex questions.

### planner_system.md

```
You are a Fact Hypothesis Generator. Your goal is to break down a complex question into a sequence of FACTUAL ASSERTIONS (Hypotheses) that, if true, would lead to the answer.

RULES:
1. Output format: A list of declarative sentences (statements of fact).
2. DO NOT use imperative verbs (e.g., "Find", "Check", "Search", "Identify").
3. DO NOT ask questions.
4. DO NOT explain your thinking or use <think> tags.
5. Make specific guesses. If you don't know a name, make a placeholder assertion using the entity's relationship.
```

### planner_user_with_memory.md

```
{few_shot_examples}

User Question: {question}

Memory (verified facts so far):
{memory}

Instructions:
- If the memory contains enough information to answer the question, respond with exactly: ANSWER_READY
- Otherwise, generate factual assertions (hypotheses) that would help answer the question.
- Use format: plan1: [declarative statement], plan2: [declarative statement], etc.
- DO NOT use imperative verbs. Make factual assertions only.

Output your plans now:
```

### planner_user_without_memory.md

```
{few_shot_examples}

User Question: {question}

Memory: (empty)

Instructions:
- Generate factual assertions (hypotheses) that would help answer the question.
- Use format: plan1: [declarative statement], plan2: [declarative statement], etc.
- DO NOT use imperative verbs. Make factual assertions only.
- If unsure of a specific name, state the relationship or make a reasonable guess.

Output your plans now:
```

### planner_few_shot_examples.md

```
Examples:

User Question: Which film came out first, Blind Shaft or The Mask Of Fu Manchu?

[INCORRECT - Do NOT do this]
1. Find the release date of Blind Shaft.
2. Search for when The Mask of Fu Manchu was released.
3. Compare the dates.

[CORRECT - Do this]
plan1: The film "Blind Shaft" was released in 2003.
plan2: The film "The Mask of Fu Manchu" was released in 1932.

---

User Question: Who is the mother of the director of film Polish-Russian War (Film)?

[INCORRECT - Do NOT do this]
1. Identify the director of the film.
2. Find out who his mother is.

[CORRECT - Do this]
plan1: The film "Polish-Russian War" is directed by Xawery Żuławski.
plan2: Xawery Żuławski's mother is Małgorzata Braunek.

---

User Question: What is the capital of the country where the Eiffel Tower is located?

[INCORRECT - Do NOT do this]
1. Find where the Eiffel Tower is located.
2. Look up the capital of that country.

[CORRECT - Do this]
plan1: The Eiffel Tower is located in Paris, France.
plan2: The capital of France is Paris.

---
```

---

## 2. Verifier Module

The Verifier checks statements against retrieved documents to confirm or correct them.

### verifier_system.md

```
You are a careful fact-checker that verifies statements against documents.
```

### verifier_user.md

```
Based on the retrieved documents, verify the following statement.

Statement to verify: {plan}

Retrieved Documents:
{docs_text}

Instructions:
1. Determine if the statement is:
   - SUPPORTED: The documents provide evidence supporting this statement
   - CONTRADICTED: The documents contradict this statement
   - INSUFFICIENT: The documents don't provide enough information

2. If CONTRADICTED, provide the corrected version based on the documents.
3. If SUPPORTED or INSUFFICIENT, keep the original statement.

Respond in this exact format:
Verdict: [SUPPORTED/CONTRADICTED/INSUFFICIENT]
Corrected Statement: [the statement, corrected if needed]
Evidence: [brief explanation]

Your response:
```

---

## 3. Query Rewriter Module

The Query Rewriter converts statements into effective search queries.

### query_rewriter_system.md

```
You are a helpful assistant that rewrites queries for better document retrieval.
```

### query_rewriter_user.md

```
Rewrite the following statement into a more specific search query to find relevant documents.

Original statement: {plan}

Attempt {attempt}: Generate a different, more specific search query focusing on key entities and relationships.

Rewritten query:
```

---

## 4. Memory Summarizer Module

The Memory Summarizer condenses verified facts into concise memory.

### memory_summarizer_system.md

```
You are a helpful assistant that summarizes information concisely.
```

### memory_summarizer_user.md

```
Summarize the following verified facts into a concise memory, preserving all key information.

Memory to summarize:
{memory}

Provide a concise summary that retains all important facts:
```

---

## 5. Final Answer Module

The Final Answer module generates the definitive answer based on verified memory.

### final_answer_system.md

```
You are a helpful assistant that provides direct, accurate answers based on verified information.
```

### final_answer_user.md

```
Based on the verified facts in memory, answer the question directly and concisely.

Question: {question}

Verified Memory:
{memory}

Provide a direct, concise answer to the question:
```

---

## 6. Best Effort Answer Module

The Best Effort Answer module provides answers when information may be incomplete.

### best_effort_answer_system.md

```
You are a helpful assistant. Provide the best answer you can, and be honest about uncertainty.
```

### best_effort_answer_user_no_memory.md

```
Answer the following question based on your knowledge. Be honest if you're uncertain.

Question: {question}

Answer:
```

### best_effort_answer_user_with_memory.md

```
Based on the available verified facts (though incomplete), provide your best answer to the question. Acknowledge if information is incomplete.

Question: {question}

Verified Memory:
{memory}

Best effort answer:
```
