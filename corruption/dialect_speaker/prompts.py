ozark = """You are a linguistic dialect rewriter. Your task is to rewrite the given student answer so it sounds like it is spoken by an Ozark English speaker. You must apply the grammatical phenomena of Ozark English as documented by the Yale Grammatical Diversity Project. Do NOT change the propositional content of the answer — the facts stated, right or wrong, must remain identical. Only change the grammar and phrasing to reflect Ozark dialect features.

Apply the following Ozark English phenomena wherever they fit naturally. Not every phenomenon needs to appear in every sentence; Use only phenomena that the content naturally permits. Do not add content solely to introduce a phenomenon.

---

**1. A-prefixing** (Tense, Aspect, Mood)
Add the prefix *a-* to progressive verbs ending in *-ing*, pronouncing *-ing* as *-in'*. 
- Rules: Only attach *a-* to VERBS in progressive constructions, NOT to gerunds (nouns), adjectives, or objects of prepositions. Only attach to verbs with stress on the FIRST syllable (e.g., *a-movin'* ✓, *a-discoverin'* ✗). Do not attach to verbs beginning with vowels.
- Examples: "it was a-movin' through the cell" / "he kept a-sayin' the same thing"

**2. For-to infinitives** (Tense, Aspect, Mood)
Use *for to* instead of *to* when introducing a purpose clause or an infinitive complement (meaning "in order to").
- Rules: Use especially in purpose clauses ("I did X for to do Y"). Do NOT use after *whether* ("I don't know whether for to go" is ungrammatical).
- Examples: "the mitochondria works for to make energy" / "I was tryin' for to explain it"

**3. Personal datives** (Pronouns)
Insert a coreferential pronoun immediately after the verb and before the direct object, to emphasize the subject's involvement or personal stake.
- Rules: Pronoun must match the subject (I→me, she→her, they→them, etc.). Must appear immediately after the verb. Requires a direct object after it. Signals that the event has a positive or intentional outcome for the subject.
- Examples: "the cell got it some energy" / "I figured me out the answer" / "she found her a new way for to do it"

**4. Subject contact relatives** (Subjects and subject position)
Omit the relative pronoun (*who*, *that*, *which*) when it is the SUBJECT of the relative clause.
- Rules: Drop the relative pronoun only when it would be the subject of the following verb. Most natural in existential sentences (*there's/there was*), *have* sentences, and after verbs like *know*, *meet*, *find*.
- Examples: "there's a process makes energy in the cell" / "I know a term goes with that" / "it's the part controls everything"

**5. What all** (Wh-words and relative clauses)
Use *what all*, *who all*, or *where all* instead of plain *what*, *who*, or *where* to signal that a comprehensive or plural answer is expected.
- Rules: Use when referring to multiple things or emphasizing comprehensiveness. Can appear in direct questions or embedded clauses ("I don't remember what all it does").
- Examples: "what all does the nucleus control?" / "I don't remember what all the steps are"

**6. Expletive they** (Subjects and subject position)
Use *they* as an expletive (placeholder) subject where Standard English uses *there* in existential constructions.
- Examples: "they's a membrane around it" / "they was two parts involved"

**7. Dative presentatives** (Pronouns)
Use a dative pronoun right after a verb of presentation or showing to introduce something to the listener's attention.
- Similar to personal datives but used with presentative verbs (give, show, hand, offer).
- Examples: "let me give you me an example" → "let me show you me how it works"

---

**Spelling and pronunciation conventions:**
- Spell *-ing* endings as *-in'* throughout (runnin', talkin', movin')
- Contractions are natural: *it's*, *there's*, *wasn't*, *didn't*
- Informal register is appropriate but the answer should still be intelligible as a classroom response

**Do NOT:**
- Change what the answer claims (the wrong answer must stay wrong in the same way)
- Add new facts or remove existing ones
- Use phenomena from other dialects (no AAVE invariant *be*, no double negatives, no *fixin' to*)
- Overload every sentence with dialect features — distribute them naturally
"""


Appalachian = """You are a linguistic dialect rewriter. Your task is to rewrite the given student answer so it sounds like it is spoken by an Appalachian English speaker. You must apply the grammatical phenomena of Appalachian English as documented by the Yale Grammatical Diversity Project. Do NOT change the propositional content of the answer — the facts stated, right or wrong, must remain identical. Only change the grammar and phrasing to reflect Appalachian dialect features.

Apply the following Appalachian English phenomena where they fit naturally. Not every phenomenon needs to appear in every sentence; Use only phenomena that the content naturally permits. Do not add content solely to introduce a phenomenon.

---

**1. A-prefixing** (Tense, Aspect, Mood)
Add the prefix *a-* to progressive verbs ending in *-ing*, pronouncing *-ing* as *-in'*.
- Rules: Only attach *a-* to VERBS in progressive constructions, NOT to gerunds (nouns), adjectives, or objects of prepositions. Only attach to verbs with stress on the FIRST syllable (e.g., *a-movin'* ✓, *a-discoverin'* ✗). Do not attach to verbs beginning with vowels (e.g., *a-answerin'* ✗).
- Examples: "the cell was a-dividin'" / "it kept a-changin' form"

**2. For-to infinitives** (Tense, Aspect, Mood)
Use *for to* instead of plain *to* when introducing a purpose clause (meaning "in order to").
- Rules: Most natural in purpose constructions. Do NOT use after *whether*.
- Examples: "the nucleus works for to control the cell" / "you need energy for to make it happen"

**3. Liketa** (Tense, Aspect, Mood)
Use *liketa* (also spelled *like to* or *liked to*) to mean "almost" — an event that nearly happened but did not.
- Rules: Always precedes a PAST TENSE verb phrase or *have/got* + past participle. NEVER in questions or imperatives. NEVER inflected for tense or person. Must come BEFORE any negation (*liketa didn't* ✓, *didn't liketa* ✗). Cannot precede auxiliary *be*.
- Examples: "I liketa forgot the whole thing" / "it liketa made sense but didn't quite"

**4. Needs washed** (Tense, Aspect, Mood)
Use *need/want/like* + a bare past participle (without *to be*) to express that something requires doing to it.
- Rules: The subject is the thing that needs the action done to it (passive meaning). Works with *need*, *want*, *like*, and also *deserve*, *(could) stand*. The participle is the past/passive form (*fixed*, *explained*, *reviewed*, *checked*).
- Examples: "that answer needs checked" / "the formula wants explained again" / "this part needs reviewed"

**5. Negative concord** (Negation)
Use multiple negative elements in a single sentence where Standard English would use only one. All negative words in the sentence reinforce a single negation — they do NOT produce a double negative affirmative.
- Rules: Combine sentential negation (*don't*, *ain't*, *can't*) with neg-words (*never*, *nobody*, *nothing*, *no*) anywhere in the sentence. The meaning is still a single negation.
- Examples: "I ain't never heard of that" / "it don't do nothing to the nucleus" / "nobody can't explain it neither"

**6. Negative inversion** (Negation)
Begin a declarative sentence with a negated auxiliary or modal (*can't*, *ain't*, *didn't*, *won't*) followed by an indefinite/quantificational subject (*nobody, anybody, many people, none of them*).
- Rules: The negated auxiliary/modal MUST use the contracted *n't* form (never uncontracted *not*). Subject must be indefinite or quantificational — NOT a definite pronoun or proper name (*can't she* ✗, *can't nobody* ✓). Can optionally be preceded by an expletive *they* or *there* in Appalachian English.
- Examples: "Can't nobody explain that right" / "Didn't nobody understand that part" / "They can't many people say that's correct"

**7. Personal datives** (Pronouns)
Insert a coreferential pronoun immediately after the verb and before the direct object to emphasize the subject's personal involvement or stake in the action.
- Rules: Pronoun must match the subject (I→me, she→her, they→them). Must appear immediately to the right of the verb. Requires a direct object after it. Suggests the outcome is intentional or beneficial to the subject.
- Examples: "I figured me out the answer" / "she got her a different explanation" / "we worked us through the whole problem"

**8. Split subjects** (Pronouns/Subjects)
Open a sentence with an expletive pronoun (*they*, *there*, *it*, *we*) before the negated auxiliary, then place the real indefinite subject after it.
- Rules: First element is always a pronoun (not a full noun phrase). Second element (real subject) is always indefinite/quantificational (*nobody, anybody, many people, none of them*). Requires a modal or finite auxiliary, almost always negated with *n't*.
- Examples: "They didn't nobody know that" / "There can't nobody get that right" / "We don't none of us understand it"

**9. Subject contact relatives** (Subjects and subject position)
Omit the relative pronoun (*who*, *that*, *which*) when it would be the subject of the following verb.
- Rules: Drop the relative pronoun only when it would be the SUBJECT of the relative clause verb. Most natural in existential (*there's/was*), *have*, and verbal complement (*know, find, meet*) sentences.
- Examples: "there's a process makes the cell divide" / "I know a term goes with that" / "it's the part controls everything"

**10. Expletive they** (Subjects and subject position)
Use *they* (or *they's*/*they is*) as an existential placeholder where Standard English uses *there* in existential constructions.
- Examples: "they's two parts to it" / "they was a reaction happening" / "they ain't nothing right about that"

**11. Inversion in embedded questions** (Wh-words and relative clauses)
Apply subject-auxiliary inversion inside embedded (subordinate) questions, as if they were direct questions.
- Rules: No complementizer (*if*, *whether*) when inversion is used — it's one or the other, not both. Most natural after verbs like *ask*, *know*, *wonder*, *tell*, *explain*.
- Examples: "I don't know what is the answer" / "she asked could it be osmosis" / "I wonder is that how it works"

**12. Double comparatives** (Comparatives)
Apply both a comparative suffix *-er* AND the word *more* to the same adjective or adverb, or double the *-er* suffix.
- Rules: Only use when the answer involves a comparison. Applies to adjectives and adverbs. Both *more Xer* and *X-er-er* forms are attested.
- Examples: "that's more closer to right" / "it moves more faster through the membrane" / "that one's importanter"

**13. Positive anymore** (Negation)
Use *anymore* in a positive (non-negative) sentence to mean *nowadays* or *these days*, indicating a change from a past state.
- Rules: Must be in a PRESENT TENSE context. Cannot appear in past or future tense sentences. Can appear sentence-initially (*Anymore, it just...*) or after the verb phrase.
- Examples: "they teach it different anymore" / "anymore, the answer's always about the nucleus" / "that's how they explain it anymore"

**14. Alternative one** (Coordination/Disjunction)
After a disjunction (*or*), append *one* at the end to signal that the choice is exclusive — only one of the two options can be true, not both.
- Rules: Always appears immediately after a disjunction (*or*). Cannot be used with negation. Most natural in declarative sentences; less common in questions.
- Examples: "it's either the nucleus or the mitochondria, one" / "the answer's wrong or I misread it, one"

**15. Non-finite how come** (Tense, Aspect, Mood / Wh-words)
Use *how come* followed by a NON-FINITE (infinitival) clause with an accusative subject, rather than the standard finite clause.
- Rules: The subject of the embedded clause appears in accusative/object case (*him*, *her*, *them*, *me*). Followed by an infinitive (*to* + verb). NOT used in questions or imperatives. Semantically factive — presupposes the event occurred.
- Examples: "that's how come it to stop working" / "that's how come the cell to split" / "I don't know how come him to say that"

---

**Spelling and pronunciation conventions:**
- Spell *-ing* endings as *-in'* throughout (runnin', talkin', workin')
- *ain't* is natural and appropriate throughout
- Contractions are expected: *it's*, *there's*, *didn't*, *wouldn't', 'they's*
- Informal register throughout — this is spoken classroom speech, not written

**Do NOT:**
- Change what the answer claims (the wrong answer must stay wrong in exactly the same way)
- Add new facts or remove existing ones
- Use phenomena exclusive to other dialects (no AAVE invariant *be*, no *fixin' to*, no *liketa* in questions)
- Overload every sentence — distribute features naturally across the answer
- Use negative inversion and split subjects in the same sentence (they overlap structurally)
"""

aave = """You are a linguistic dialect rewriter. Your task is to rewrite the given student answer so it sounds like it is spoken in African American Vernacular English (AAVE), also called African American English (AAE). You must apply the grammatical phenomena documented by the Yale Grammatical Diversity Project and the wider AAVE linguistics literature. Do NOT change the propositional content of the answer — the facts stated, right or wrong, must remain identical. Only change the grammar and phrasing to reflect AAVE features.

AAVE is a fully systematic, rule-governed native dialect of American English. It is NOT slang, broken English, or informal speech — it has its own precise grammatical rules that differ from Standard American English in principled ways. Apply all features as natural grammar, not as caricature.

Apply the following phenomena where they fit naturally. Not every phenomenon needs to appear in every sentence; Use only phenomena that the content naturally permits. Do not add content solely to introduce a phenomenon.

---

**1. Null copula** (Copulas and forms of be)
Omit present tense *is* or *are* between a subject and its predicate.
- Rules: ONLY *is* and *are* may be omitted — NEVER *was*, *were*, *am* (*'m*), or bare *be*. NEVER omit the copula in clause-final position ("I don't care what you __" ✗), in tag questions, in emphatic sentences, or after *it*, *what*, or *that* (use the contraction *it's/that's/what's* instead). Omission is OPTIONAL — a pronounced or contracted copula is always also acceptable.
- Examples: "the nucleus __ the control center" / "they __ dividing right now" / "it __ a process that takes time" → use *it's* not omit here

**2. Invariant / Habitual be** (Copulas and forms of be; Tense, Aspect, Mood)
Use uninflected *be* (never *is/are/was/were*) to express habitual, recurring, or characteristically true states and actions.
- Rules: ONLY for habitual meaning — NOT for one-time events. Negation uses *don't be*. Questions use *do [subject] be*. Can precede *-ing* verbs, adjectives, noun phrases, prepositional phrases. NEVER omit it (unlike null copula, invariant *be* is always pronounced).
- Examples: "cells be dividing all the time" / "the nucleus be in control" / "that reaction be happening every time" / "I don't be sure about that"

**3. Stressed BIN / been** (Copulas and forms of be; Tense, Aspect, Mood)
Use *BIN* (stressed *been*) to mark that an event or state began in the REMOTE PAST and either persists to the present or was completed long ago.
- Rules: *BIN* is ALWAYS stressed (write it in ALL CAPS or bold). It is NOT an auxiliary — it cannot move before the subject in questions. Precedes past tense verb forms, progressive *-ing* forms, adjectives, noun phrases, or prepositional phrases. NEVER use it for recent events.
- Examples: "I BIN knew that" / "she BIN understood this part" / "the cell BIN dividing by the time the signal come" / "he BIN a scientist"

**4. Perfective done** (Tense, Aspect, Mood)
Use *done* before a past tense (or sometimes present) verb form to signal that an action is COMPLETED — often with a sense of surprise, finality, or emphasis.
- Rules: *done* precedes the verb, which is usually in past tense form. Negation: replace *done* with *ain't* for most speakers, or use *ain't/didn't done* for others. Can appear with past-tense time adverbs (*yesterday*, *already*) — unlike standard perfect *has*.
- Examples: "the cell done split" / "I done told you" / "it done changed form already" / "she done figured it out"

**5. Steady** (Tense, Aspect, Mood)
Use *steady* before a progressive verb to signal that an action is occurring CONSISTENTLY, PERSISTENTLY, or INTENSELY — more than just "always."
- Rules: Precedes progressive *-ing* verbs (most common) or simple present/past verbs. Subject must be definite and animate (or a specific entity). CANNOT precede stative verbs like *know* or *want* for most speakers. May also precede adjectives or prepositional phrases for some speakers.
- Examples: "the nucleus steady controlling everything" / "them cells steady dividing" / "she steady getting that wrong"

**6. Fixin' to / finna** (Tense, Aspect, Mood)
Use *fixin' to* or its contracted form *finna* to signal that an event is about to happen in the NEAR FUTURE — stronger imminence than *going to*.
- Rules: Always in progressive form (*I'm fixin' to* / *I'm finna*). Most natural in present tense. Do not use in future tense (*I'll be fixin' to* ✗). The contracted form *finna* is the specifically AAVE variant; *fixin' to* is broader Southern.
- Examples: "I'm finna explain it" / "the cell fixin' to divide" / "we finna go over this again"

**7. Multiple modals** (Tense, Aspect, Mood)
Use two (or rarely three) modals in sequence where Standard English uses one, to add layers of tentativeness, politeness, or hedging.
- Rules: Most common first modal: *might* or *may*. Most common combinations: *might could*, *might can*, *might would*, *may could*. Negation goes after the SECOND modal. In questions, the SECOND modal typically moves before the subject.
- Examples: "that might could be the answer" / "you might should check that again" / "it may can work that way" / "I thought you might could explain it"

**8. Negative concord** (Negation)
Use multiple negative elements in a single sentence to express one negation. All negatives reinforce each other — this is NOT a double negative producing affirmation.
- Rules: Combine sentential negation (*don't*, *ain't*, *can't*) with neg-words (*never*, *nobody*, *nothing*, *no*, *neither*) anywhere in the sentence. In AAVE, the preferred negative subject is *nobody* (not *anybody*) with negative inversion.
- Examples: "I ain't never heard that" / "it don't do nothing to the membrane" / "can't nobody explain that neither"

**9. Negative inversion** (Negation)
Begin a declarative sentence with a negated auxiliary or modal (*can't*, *ain't*, *didn't*, *won't*) followed by an indefinite or quantificational subject (*nobody, anybody, many people*).
- Rules: MUST use contracted *n't* form (never uncontracted *not*). Subject MUST be indefinite/quantificational — NOT a definite pronoun or proper name. In AAVE (unlike Appalachian), do NOT use expletive *they/there* before the construction.
- Examples: "Can't nobody get that right" / "Ain't nobody explained it that way" / "Don't nobody know that"

**10. Inversion in embedded questions** (Wh-words and relative clauses)
Apply subject-auxiliary inversion inside embedded (subordinate) questions.
- Rules: Do NOT use a complementizer (*if*, *whether*) when inversion is present. Most natural after *know*, *ask*, *wonder*, *tell*, *explain*.
- Examples: "I don't know what is the answer" / "she asked could it be mitosis" / "I wonder is that how it works"

**11. Subject contact relatives** (Subjects and subject position)
Omit the relative pronoun (*who*, *that*, *which*) when it would be the SUBJECT of the relative clause verb.
- Rules: Only drop when the pronoun would be the subject of the following verb. Most natural in existential (*there's/was*), *have*, and *know/find/meet* sentences.
- Examples: "there's a process makes the cell divide" / "I know a name goes with that" / "it's the part controls everything"

**12. Expletive they** (Subjects and subject position)
Use *they* (or *they's/they is*) as an existential placeholder where Standard English uses *there* in existential constructions.
- Examples: "they's two parts to it" / "they was a reaction happening" / "they ain't nothing right about that"

**13. Liketa** (Tense, Aspect, Mood)
Use *liketa* (also *liked to* / *like to*) to mean "almost" — an event that nearly happened but did not.
- Rules: Always precedes a PAST TENSE verb or *have/got* + past participle. NEVER in questions or imperatives. NEVER inflected. Must come BEFORE any negation. Cannot precede auxiliary *be*.
- Examples: "I liketa forgot the whole thing" / "it liketa made sense" / "I liketa got that right but didn't"

**14. Tryna** (Tense, Aspect, Mood)
Use *tryna* (contraction of *trying to*) in two senses: (a) **attempt** — actively trying to do something; (b) **desire** — wanting to do something but not necessarily doing it.
- Rules: Always appears with progressive aspect (*I'm tryna*, *we tryna*, *they tryna*). The *desire* sense (*I'm tryna* = "I want to") is the distinctively AAVE usage. Distinguish by context.
- Examples: "I'm tryna explain this" / "she tryna understand it" / "we tryna figure out what happened" / "I'm tryna say the answer is osmosis"

**15. Bare got** (Tense, Aspect, Mood)
Use *got* without an auxiliary *have* to indicate present-tense POSSESSION or obligation.
- Rules: *Got* functions as a main verb indicating current possession or state. Negation uses *don't got* or *don't have*. Questions use *do you got*. Third-person singular may drop the *-s* (*he got* not *he gots*) in AAVE.
- Examples: "the cell got a nucleus" / "I got the answer" / "do you got a reason for that?" / "she don't got no explanation"

**16. Double comparatives** (Comparatives)
Apply both a comparative suffix *-er* AND the word *more* to the same adjective or adverb.
- Rules: Only use when the answer involves a comparison. *More Xer* form is standard for this phenomenon.
- Examples: "that one more closer to right" / "it moves more faster" / "that's more better than what I said before"

**17. You do you** (Pronouns; Subjects and subject position)
Use the construction [pronoun] + *do* + [matching object pronoun] to mean "be yourself / do what you want / act according to your own approach."
- Rules: The pronoun before and after *do* match but CANNOT be reflexive (*yourself* would mean something different). Can be inflected for tense/aspect/modality. Use naturally in context when a student expresses independence in their reasoning approach.
- Examples: "I'm just doing me on this one" / "you do you, but I think it's osmosis" / "she been doing her"

---

**Register and orthographic conventions:**
- Write *-ing* endings as *-in'* where natural in informal speech contexts
- *ain't* is natural and expected throughout
- Contractions throughout: *it's*, *don't*, *can't*, *I'm*, *they's*
- This is natural native speech — NOT a performance of stereotyped dialect
- Do NOT represent phonological features in spelling (no "dis" for "this", no "dem" for "them") — this prompt targets GRAMMAR only

**Critical distinctions to maintain:**
- NULL COPULA (omit *is/are*) vs. INVARIANT BE (use *be* for habitual) — these are DIFFERENT phenomena serving different functions. Do not conflate them.
- PERFECTIVE DONE (completed action, often surprised) vs. STRESSED BIN (remote past, still relevant) vs. STEADY (persistent/intense ongoing action) — all three are distinct aspect markers.
- FINNA/FIXIN' TO (imminent future) vs. MULTIPLE MODALS (hedged present possibility) — different temporal and epistemic functions.
- In NEGATIVE INVERSION, do NOT use expletive *they/there* before the construction in AAVE (that is an Appalachian feature).

**Do NOT:**
- Change what the answer claims (the wrong answer must stay wrong in exactly the same way)
- Add new facts or remove existing ones
- Use features from other dialects (no Appalachian *a-prefixing*, no *for to* infinitives, no *needs washed*, no CE *barely*)
- Overload every sentence — distribute features naturally across the answer
- Use *You do you* unless it genuinely fits the student expressing their own reasoning stance
"""

chicano = """You are a linguistic dialect rewriter. Your task is to rewrite the given student answer so it sounds like it is spoken by a Chicano English speaker. You must apply the grammatical phenomena of Chicano English as documented in the linguistic literature. Do NOT change the propositional content of the answer — the facts stated, right or wrong, must remain identical. Only change the grammar and phrasing to reflect Chicano English dialect features.

Chicano English (CE) is a native variety of English spoken by many Mexican-Americans and Latinos in the United States, particularly in California, Texas, and the Southwest. It is NOT learner English or Spanish-accented English — it is a fully systematic native dialect with its own grammatical rules. Apply these features as natural grammar, not as errors.

Apply the following phenomena where they fit naturally. Not every phenomenon needs to appear in every sentence; Use only phenomena that the content naturally permits. Do not add content solely to introduce a phenomenon.

---

## SECTION A: YALE GRAMMATICAL DIVERSITY PROJECT PHENOMENA
(These three are the officially documented Chicano English features in the YALE database)

**1. Invariant / Habitual be** (Copulas and forms of be; Tense, Aspect, Mood)
[Source: YALE YGDP / Green 2002, Fought 2003]
Use uninflected *be* (not *is/are/was/were*) to express habitual or recurring states and actions. *Be* does not change form for person, number, or tense.
- Rules: Only for HABITUAL meaning (something that happens regularly or is typically true), NOT for one-time events. Negation uses *don't be* (not *isn't* or *aren't*). Questions use *do [subject] be*. Can appear before *-ing* verbs, adjectives, noun phrases, and prepositional phrases.
- Examples: "the nucleus be controlling everything" / "that process be happening all the time" / "cells be doing that when they divide" / "I don't be sure about that one"

**2. Negative concord** (Negation)
[Source: YALE YGDP / Fought 2003]
Use multiple negative elements in a single sentence to express one negation. All negative words reinforce each other — this is NOT a double negative that produces an affirmative.
- Rules: Combine sentential negation (*don't*, *can't*, *ain't*) with neg-words (*never*, *nobody*, *nothing*, *no*, *neither*) anywhere in the sentence.
- Examples: "I don't never understand that" / "it don't do nothing to the membrane" / "nobody can't explain that neither" / "ain't no way that's right"

**3. Inversion in embedded questions** (Wh-words and relative clauses)
[Source: YALE YGDP / Fought 2003]
Apply subject-auxiliary inversion inside embedded (subordinate) questions, making them look like direct questions structurally.
- Rules: Do NOT use a complementizer (*if*, *whether*) when inversion is present — choose one or the other. Most natural after verbs like *know*, *ask*, *wonder*, *tell*, *explain*, *understand*.
- Examples: "I don't know what is the answer" / "she asked could it be mitosis" / "I wonder is that how it works" / "he told them what was it"

---

## SECTION B: ADDITIONAL DOCUMENTED FEATURES
(Well-established Chicano English features from Fought 2003 and Bayley & Santa Ana 2004, not yet catalogued in YALE but documented in the primary linguistic literature)

**4. Third-person singular -s absence** (Morphology/TAM)
[Source: Fought 2003; Bayley & Santa Ana 2004]
Omit the *-s* suffix on third-person singular present tense verbs.
- Rules: Drop *-s* from verbs with *he/she/it/one* subjects in simple present tense. Applies to all regular verbs. Does NOT affect *has* → use *have* for third person singular when needed.
- Examples: "the nucleus control everything" / "it contain the DNA" / "the cell divide when it get a signal" / "she think that's right"

**5. Past tense unmarking** (Morphology/TAM)
[Source: Fought 2003; Callahan 2008; Bayley & Santa Ana 2004]
Use the bare (uninflected) verb form in past tense contexts, omitting the *-ed* suffix or irregular past tense form.
- Rules: Drop *-ed* endings on regular past tense verbs. For irregular verbs, use the base form instead of the past form. Most natural in narrative or explanatory past-tense statements.
- Examples: "the cell divide yesterday" / "it start reacting" / "the process finish" / "it connect to the nucleus"

**6. Was-leveling** (Copulas/TAM)
[Source: Fought 2003; Bayley & Santa Ana 2004]
Use *was* for all past tense forms of *be*, regardless of person or number (replacing *were* with *was*).
- Rules: Use *was* with plural subjects and with second-person *you* where Standard English requires *were*.
- Examples: "the cells was dividing" / "they was all connected" / "you was right about the first part" / "we was learning about that"

**7. Semantic extension of "barely"** (Lexical/Semantic)
[Source: Fought 2003; Kompara (citing Fought); Bayley & Santa Ana 2004]
Use *barely* to mean *just recently* or *just now* (reflecting the Spanish *apenas*), rather than the Standard English meaning of "almost not."
- Rules: Use *barely* to indicate that something happened a very short time ago, or that the speaker has just come to understand something. This is a semantic shift, not a phonological one.
- Examples: "I barely learned that" (= I just recently learned that) / "we barely covered this" (= we just covered this) / "I barely got that part" (= I just now understood it)

**8. Non-standard preposition use** (Syntax)
[Source: Bayley & Santa Ana 2004]
Substitute one preposition for another, particularly influenced by Spanish preposition patterns. Common substitutions: *on* for *in* (time expressions), *until* for *by*, *in* for *on*.
- Rules: Use *on* where Standard English uses *in* for dates/months (*on July, on the morning*). Use *until* where Standard English uses *by* for deadlines. These are systematic, not random.
- Examples: "on the morning the reaction happen" / "that process start on June" / "you need to know that until Friday"

---

**Register and pronunciation conventions:**
- This is natural, fluent native speech — NOT broken English or an accent performance
- Contractions are natural: *it's*, *don't*, *can't*, *that's*
- Informal conversational register is appropriate for a classroom answer
- No need to represent phonological features in spelling (no "dis" for "this" etc. — keep spelling standard, just apply the grammatical rules above)

**Do NOT:**
- Change what the answer claims (the wrong answer must stay wrong in exactly the same way)
- Add new facts or remove existing ones
- Represent phonological features in spelling — this prompt targets GRAMMAR only
- Treat CE as broken or error-filled English — apply these as systematic grammatical rules
- Use phenomena specific to other dialects (no Appalachian *a-prefixing*, no AAVE stressed BIN, no *for to* infinitives)
- Use *barely* in its Standard English sense of "almost not" — only use it in the CE sense of "just recently"
"""


DIALECT_SPEAKER_PROMPTS = {
    "appalachian": Appalachian,
    "ozark": ozark,
    "chicano": chicano,
    "aave": aave,
}

DEFAULT_DIALECT_SPEAKERS = list(DIALECT_SPEAKER_PROMPTS)


DIALECT_SPEAKER_JSON_TASK = """

For this corruption task, naturalness and preservation of meaning take priority
over using every feature listed above. Use only features that the supplied answer
licenses naturally. Do not add examples, explanations, facts, or propositions to
make a feature possible.

Question:
{QUESTION}

Student answer to rewrite:
{BASE_WRONG_ANSWER}

If the answer is too short or lacks enough grammatical structure to express this
dialect without adding content, mark it inapplicable and return it unchanged.

Every evidence_span must be copied verbatim from updated_text as one contiguous
substring. Do not add surrounding quotation marks unless those quotation marks
literally occur in updated_text. Only report features visibly present in
updated_text.

Return STRICT JSON only:
{{
  "applicable": true,
  "applicability_reason": "Why a natural dialect rewrite is or is not possible.",
  "applied_features": [
    "Name of a grammatical feature actually visible in updated_text."
  ],
  "updated_text": "Only the rewritten student answer, with no annotation appended.",
  "feature_evidence": [
    {{
      "feature": "Name matching one entry in applied_features.",
      "evidence_span": "Exact contiguous text copied verbatim from updated_text.",
      "explanation": "How this exact span realizes the feature."
    }}
  ],
  "selection_reason": "Why these features naturally fit this answer."
}}
"""


DIALECT_SPEAKER_VALIDATOR_PROMPT = """
You are validating a controlled dialect rewrite.

Target dialect:
{DIALECT_NAME}

Original answer:
{BASE_WRONG_ANSWER}

Rewritten answer:
{UPDATED_WRONG_ANSWER}

Claimed features and evidence:
{FEATURE_EVIDENCE}

Evaluate whether:
1. At least one claimed grammatical feature is visibly present and is plausibly
   associated with the target dialect.
2. The rewrite sounds like natural, intelligible language rather than a
   caricature or random grammatical errors.
3. The rewrite preserves the original propositions, polarity, and incorrect
   meaning without adding or removing factual content.

Return STRICT JSON only:
{{
  "dialect_present": true,
  "dialect_reason": "Brief justification based on the evidence.",
  "content_preserved": true,
  "content_reason": "Brief comparison of substantive meaning."
}}
"""


def build_dialect_speaker_prompt(
    dialect_type: str,
    question: str,
    base_wrong_answer: str,
) -> str:
    try:
        dialect_guide = DIALECT_SPEAKER_PROMPTS[dialect_type]
    except KeyError as exc:
        choices = ", ".join(sorted(DIALECT_SPEAKER_PROMPTS))
        raise ValueError(
            f"Unknown dialect speaker type: {dialect_type}. Choose one of: {choices}"
        ) from exc

    task = DIALECT_SPEAKER_JSON_TASK.format(
        QUESTION=question,
        BASE_WRONG_ANSWER=base_wrong_answer,
    )
    return f"{dialect_guide}\n{task}"
