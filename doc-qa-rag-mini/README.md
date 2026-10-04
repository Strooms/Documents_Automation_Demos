# doc-qa-rag-mini

> **Demo project with synthetic data. Not client work.**
> "Fiktiva Labs" is a made-up company; all 10 documents were written for this demo by `scripts/generate_docs.py`.

## Problem

Teams keep policies and how-tos in scattered files (Markdown, text, PDF). People want a direct answer
**with a source they can check** — and, just as important, a clear "I couldn't find that" instead of an
invented answer.

## Approach

A deliberately small, fully local pipeline (no API key, no paid service, no GPU):

1. **Load** `.md` / `.txt` / `.pdf` (`pdfplumber`; PDF paragraph breaks are rebuilt from vertical gaps) — `docqa/loader.py`.
2. **Chunk** by paragraph, keeping each heading attached to its text (31 chunks from 10 docs) — `docqa/chunker.py`.
3. **Retrieve** with one of two interchangeable lexical retrievers — `docqa/retrievers.py`:
   - **TF-IDF** (scikit-learn, unigrams + bigrams, sublinear tf, cosine similarity)
   - **BM25** (own ~30-line implementation; scores normalised to 0–1)
   - a tiny suffix-stripping stemmer so "days" matches "day".
4. **Answer extractively** — the sentence in the best chunk that shares the most terms with the question
   — plus a citation `file, page, chunk` and the full passage. **No generative model is used**, so there is nothing to hallucinate; the trade-off is that answers are quotes, not rephrasings.
5. **Not found**: if the best score is below a threshold the answer is `Not found in the provided documents.`
   The threshold is chosen on a **separate calibration set** of 8 different questions (`data/calibration_questions.json`),
   not on the 10 test questions.

Sentence-transformers / dense embeddings were *not* used: they would help with the paraphrase failures
below, but need a large model download. See "Limitations".

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/generate_docs.py                       # recreate the synthetic documents
python -m docqa "How many days of annual leave do employees get?"
python -m docqa "What does error TN-12 mean in the VPN client?" --retriever bm25
python -m docqa.evaluate                              # calibrate + run the 10 test questions
python -m pytest -q
```

## Sample input / output

```
$ python -m docqa "What does error TN-12 mean in the VPN client?"
Q: What does error TN-12 mean in the VPN client?
A: Troubleshooting Error TN-12 means your device certificate has expired.
score=0.377  source: vpn_setup.txt, page 1, chunk 2
passage: Troubleshooting Error TN-12 means your device certificate has expired. Open the software portal and choose Renew certificate, then restart the client. Error TN-40 means the server is unreachable; check your internet connection and try again.
```

```
$ python -m docqa "Who is the CEO of Fiktiva Labs?"
Q: Who is the CEO of Fiktiva Labs?
A: Not found in the provided documents.
score=0.236  source: -
```

## Results: 10 test questions (real run of `python -m docqa.evaluate`)

A question passes if (answerable) the top-1 chunk is from the expected document **and** contains the expected
fact, or (unanswerable) the system says "not found". Questions were written before running anything and were not changed afterwards.

### tfidf (not-found threshold 0.28, chosen on the separate calibration set) - **7/10 passed**

| # | Question | Expected | Got | Top score | Right chunk ranked #1? | Result |
|---|---|---|---|---|---|---|
| 1 | How many days of annual leave do employees get? | leave_policy.md | leave_policy.md | 0.448 | yes | PASS |
| 2 | What is the maximum amount I can claim for meals per day? | expense_policy.pdf | NOT FOUND | 0.246 | yes | **FAIL** |
| 3 | Which days must I be in the office? | remote_work.md | NOT FOUND | 0.234 | no | **FAIL** |
| 4 | What does error TN-12 mean in the VPN client? | vpn_setup.txt | vpn_setup.txt | 0.377 | yes | PASS |
| 5 | How quickly must the on-call engineer respond to a SEV1 incident? | incident_response.md | incident_response.md | 0.399 | yes | PASS |
| 6 | How many failed logins before my account is locked? | password_policy.md | password_policy.md | 0.482 | yes | PASS |
| 7 | How much does the Pro plan cost? | product_faq.pdf | product_faq.pdf | 0.413 | yes | PASS |
| 8 | Can I take time off after my baby is born? | leave_policy.md | NOT FOUND | 0.212 | no | **FAIL** |
| 9 | Who is the CEO of Fiktiva Labs? | NOT FOUND | NOT FOUND | 0.236 | n/a | PASS |
| 10 | What is the dress code in the office? | NOT FOUND | NOT FOUND | 0.159 | n/a | PASS |

### bm25 (not-found threshold 0.24, chosen on the separate calibration set) - **7/10 passed**

| # | Question | Expected | Got | Top score | Right chunk ranked #1? | Result |
|---|---|---|---|---|---|---|
| 1 | How many days of annual leave do employees get? | leave_policy.md | leave_policy.md | 0.493 | yes | PASS |
| 2 | What is the maximum amount I can claim for meals per day? | expense_policy.pdf | NOT FOUND | 0.199 | yes | **FAIL** |
| 3 | Which days must I be in the office? | remote_work.md | remote_work.md | 0.491 | no | **FAIL** |
| 4 | What does error TN-12 mean in the VPN client? | vpn_setup.txt | vpn_setup.txt | 0.271 | yes | PASS |
| 5 | How quickly must the on-call engineer respond to a SEV1 incident? | incident_response.md | incident_response.md | 0.282 | yes | PASS |
| 6 | How many failed logins before my account is locked? | password_policy.md | password_policy.md | 0.35 | yes | PASS |
| 7 | How much does the Pro plan cost? | product_faq.pdf | product_faq.pdf | 0.311 | yes | PASS |
| 8 | Can I take time off after my baby is born? | leave_policy.md | NOT FOUND | 0.119 | no | **FAIL** |
| 9 | Who is the CEO of Fiktiva Labs? | NOT FOUND | NOT FOUND | 0.185 | n/a | PASS |
| 10 | What is the dress code in the office? | NOT FOUND | NOT FOUND | 0.137 | n/a | PASS |

Raw per-question answers and citations: [`output/results.json`](output/results.json).

### Honest read of these results

**7 of 10 passed with each retriever; 3 failed.** Both methods fail on the same three questions (#2, #3 and #8), for different reasons:

- **#8 "Can I take time off after my baby is born?"** — a true vocabulary-mismatch failure. The policy says "parental leave … birth or adoption"; the question says "baby … born … time off". Lexical retrieval has no notion of synonyms, so the top-1 chunk is wrong (`office_hours_holidays.md`, a chunk about visitors), and the score is below the threshold. This is the failure that dense embeddings are meant to fix; it is *not tested* here whether they would.
- **#3 "Which days must I be in the office?"** — retrieval picked the wrong chunk of the right document (the "home office stipend" chunk, probably because the question shares the word "office" with it), so it failed on the fact check (BM25 returned it with a high score; TF-IDF fell below the threshold).
- **#2 "maximum amount … meals per day?"** — TF-IDF and BM25 *did* rank the right chunk first, but its score (0.246 / 0.199) was just under the not-found threshold (0.28 / 0.24), so the system wrongly said "not found". That is the cost of a threshold chosen on only 8 calibration questions.

The two unanswerable questions (#9, #10) were correctly refused by both retrievers, but #9 scored 0.236 for TF-IDF —
only slightly below the threshold, so this is a thin margin, not a robust guarantee. With 10 test questions the pass rate has a very wide uncertainty; treat it as a demonstration, not a benchmark.

## Limitations

- Lexical retrieval only: no synonyms or paraphrase understanding (see #8). Adding `sentence-transformers` embeddings or a hybrid is the natural next step.
- Extractive answers: returns an existing sentence; it does not combine facts across chunks or rephrase.
- The not-found threshold is a trade-off between false refusals (#2) and false answers; it is calibrated on 8 questions only and would need re-tuning on real documents.
- Tiny corpus (31 chunks); behaviour on thousands of documents is untested. Index is rebuilt in memory on every run.
- English only; the stemmer is a crude suffix stripper.
