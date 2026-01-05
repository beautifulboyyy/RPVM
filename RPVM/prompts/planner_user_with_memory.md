{few_shot_examples}

User Question: {question}

Current Memory (Already Known/Verified):
{memory}

Instructions:
- Analyze the Memory first. If the Memory already contains all the necessary facts to answer the question, respond ONLY with: ANSWER_READY.
- Otherwise, identify the MISSING LINK between the current Memory and the final answer.
- Generate ONLY new factual assertions (hypotheses) to bridge this gap.
- DO NOT re-generate or re-verify facts already in the Memory.
- Use format: plan1: [statement], plan2: [statement].

Output your new plans now: