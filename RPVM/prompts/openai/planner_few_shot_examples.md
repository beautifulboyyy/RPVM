### Example 1: Standard Success (Sequential Verification)
User Question: Where was the director of film The Children (1990 Film) born?
Iteration 1 | Memory: (empty)
Output:
plan1: The director of the film "The Children" (1990) is Tony Palmer.
plan2: Tony Palmer was born in London.

Iteration 2 | Memory: 
1. The director of the film "The Children" (1990) is Tony Palmer. (verified)
2. Tony Palmer was born in London. (verified)
Output:
ANSWER_READY

---

### Example 2: Direct Correction (Immediate Answer)
User Question: Who is the child of the director of film The Fall Of A Saint?
Iteration 1 | Memory: (empty)
Output:
plan1: The director of film "The Fall Of A Saint" is W.P. Kellino.
plan2: The child of W.P. Kellino is Fred Kellino.

Iteration 2 | Memory: 
1. The director of film "The Fall Of A Saint" is W.P. Kellino. (verified)
2. The child of W.P. Kellino is Roy Kellino. (corrected)
Output:
ANSWER_READY

---

### Example 3: Short-circuit & Re-planning (Correction during the chain)
User Question: Which country the director of film The Boys In The Band (2020 Film) is from?
Iteration 1 | Memory: (empty)
Output:
plan1: The director of "The Boys In The Band" (2020) is Mart Crowley.
plan2: Mart Crowley comes from the United States.

Iteration 2 | Memory: 
1. The director of "The Boys In The Band" (2020) is Joe Mantello. (corrected)
Output:
plan1: Joe Mantello comes from the United States.

Iteration 3 | Memory: 
1. The director of "The Boys In The Band" (2020) is Joe Mantello. (corrected)
2. Joe Mantello comes from the United States. (verified)
Output:
ANSWER_READY

---

### Example 4: Selection (Same) - Parallel Comparison
User Question: Do both Logan (Film) and May Stars films have the directors from the same country?
Iteration 1 | Memory: (empty)
Output:
plan1: The director of "Logan" is James Mangold, who is from the United States.
plan2: The director of "May Stars" is a director from the United States.

Iteration 2 | Memory: 
1. The director of "Logan" is James Mangold, who is from the United States. (verified)
2. The director of "May Stars" is a South Korean director named Nan-seon Choi. (corrected)
Output:
ANSWER_READY

---

### Example 5: Selection (Same) - Incremental Step-by-Step
User Question: Are both director of film The Green Scarf and director of film The Coast Guard (Film) from the same country?
Iteration 1 | Memory: (empty)
Output:
plan1: The director of "The Green Scarf" is from the United States.
plan2: The director of "The Coast Guard" is also from the United States.

Iteration 2 | Memory: 
1. The director of "The Green Scarf" is a Hong Kong director named Ng See-yuen. (corrected)
Output:
plan1: The director of "The Coast Guard" is a Hong Kong filmmaker.

Iteration 3 | Memory: 
1. The director of "The Green Scarf" is a Hong Kong director named Ng See-yuen. (corrected)
2. The director of "The Coast Guard" is a South Korean director named Kim Ki-duk. (corrected)
Output:
ANSWER_READY

---

### Example 6: Selection (Born First) - Comparative Reasoning
User Question: Which film has the director who was born first, State Penitentiary (Film) or Folly Of Love?
Iteration 1 | Memory: (empty)
Output:
plan1: The director of "State Penitentiary" was born in a specific year.
plan2: The director of "Folly Of Love" was born in an earlier year than the director of "State Penitentiary".

Iteration 2 | Memory: 
1. The director of "State Penitentiary" is Lew Landers, who was born in 1901. (verified)
Output:
plan1: The director of "Folly Of Love" was born before 1901.

Iteration 3 | Memory:
1. The director of "State Penitentiary" is Lew Landers, who was born in 1901. (verified)
2. The director of "Folly Of Love" is a filmmaker born in 1895. (verified)
Output:
ANSWER_READY

---

### Example 7: Avoiding Vague Language (INCORRECT vs CORRECT)
User Question: When did John V, Prince Of Anhalt-Zerbst's father die?
Memory: (empty)

❌ **INCORRECT - Too Vague** (No retrieval value):
plan1: John V's father was a specific German prince.
plan2: His father died in a specific year.

✅ **CORRECT - Specific Hypotheses**:
plan1: John V, Prince of Anhalt-Zerbst is the son of Ernest I, Prince of Anhalt-Dessau.
plan2: Ernest I, Prince of Anhalt-Dessau died in the early 16th century (around 1516).

---

### Example 8: Handling Dates (INCORRECT vs CORRECT)
User Question: What year was the director of Ronnie Rocket born?
Memory: (empty)

❌ **INCORRECT - Placeholder Terms**:
plan1: The director of "Ronnie Rocket" is a known filmmaker.
plan2: He was born in a specific year.

✅ **CORRECT - Bold Guesses**:
plan1: "Ronnie Rocket" is an unfinished film project written by David Lynch.
plan2: David Lynch was born in the mid-20th century (around 1946).

---

### Example 9: Handling Awards (INCORRECT vs CORRECT)
User Question: What award did the director of Wearing Velvet Slippers Under A Golden Umbrella win?
Memory: (empty)

❌ **INCORRECT - Vague Award Reference**:
plan1: The director of the Burmese film won a specific award.
plan2: The award was a known film award.

✅ **CORRECT - Specific Hypotheses**:
plan1: "Wearing Velvet Slippers under a Golden Umbrella" is a 1970 Burmese film directed by Maung Wunna.
plan2: Maung Wunna won the Myanmar Motion Picture Academy Awards (a national film award).

---

### Example 10: Handling Comparisons (INCORRECT vs CORRECT)
User Question: Which film came out first, Blind Shaft or The Mask Of Fu Manchu?
Memory: (empty)

❌ **INCORRECT - Unverifiable Statements**:
plan1: Blind Shaft was released in a known year.
plan2: The Mask of Fu Manchu was released in a specific year.

✅ **CORRECT - Retrieval-Oriented**:
plan1: "Blind Shaft" is a modern Chinese film released around 2003.
plan2: "The Mask of Fu Manchu" is a classic pre-Code film released in the early 1930s (1932).