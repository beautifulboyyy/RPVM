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
