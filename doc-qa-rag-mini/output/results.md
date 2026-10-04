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
