"""Write the 10 synthetic knowledge-base documents (7 text/markdown + 3 PDF).

"Fiktiva Labs" is a made-up company; every policy, number and product detail below is invented.
Usage: python scripts/generate_docs.py
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).resolve().parent.parent / "data" / "docs"

# (filename, [(heading, paragraph), ...]) -- extension decides the format.
DOCS = {
    "leave_policy.md": ("Leave Policy", [
        ("Annual leave", "Full-time employees receive 18 days of paid annual leave per calendar year. Leave accrues monthly and requests are approved by your line manager at least one week in advance."),
        ("Carry-over", "Up to 5 unused annual leave days may be carried over into the next year. Carried-over days expire on 31 March."),
        ("Sick leave", "Sick leave is paid. A doctor's note is required when an absence lasts more than 2 consecutive days. Please notify your manager before 09:30 on the first day of absence."),
        ("Parental leave", "Primary caregivers are entitled to 12 weeks of paid parental leave, and secondary caregivers to 4 weeks. Parental leave can be taken within the first 12 months after the birth or adoption."),
    ]),
    "expense_policy.pdf": ("Expense Policy", [
        ("Meals", "Meals are reimbursed up to USD 40 per day. Alcohol is not reimbursable. Itemised receipts are required for any single expense above USD 15."),
        ("Submission deadline", "Expense claims must be submitted in the Reimburse portal within 30 days of the expense date. Claims submitted later than 30 days are rejected unless your director approves an exception."),
        ("Approval", "Claims above USD 500 need approval from a department head in addition to your line manager. Claims are paid with the next monthly payroll."),
    ]),
    "remote_work.md": ("Hybrid and Remote Work", [
        ("Office days", "Fiktiva Labs runs a hybrid model: employees work from the office on Tuesday, Wednesday and Thursday, and remotely on Monday and Friday. Teams may agree a different split with their department head."),
        ("Core hours", "Everyone is expected to be reachable during core hours, 10:00 to 15:00 local time, on every working day."),
        ("Home office stipend", "New employees receive a one-time home office stipend of USD 300 for a desk, chair or monitor. Keep the receipt and file it as an expense within 30 days."),
    ]),
    "vpn_setup.txt": ("VPN Setup Guide", [
        ("Installing the client", "Install the Tunnelo VPN client from the internal software portal. Open it and enter the server address vpn.fiktiva.example."),
        ("Signing in", "Sign in with your company email. Multi-factor authentication is mandatory: approve the prompt in your authenticator app, then wait for the green Connected status."),
        ("Troubleshooting", "Error TN-12 means your device certificate has expired. Open the software portal and choose Renew certificate, then restart the client. Error TN-40 means the server is unreachable; check your internet connection and try again."),
    ]),
    "password_policy.md": ("Password and Account Security", [
        ("Password rules", "Passwords must have at least 14 characters. Use the company password manager, Vaultly, to generate and store them. Passwords are rotated only when a compromise is suspected."),
        ("Lockout", "An account is locked for 15 minutes after 5 failed sign-in attempts. If you are still locked out afterwards, contact the IT helpdesk."),
        ("Multi-factor authentication", "Multi-factor authentication is required for email, VPN and the code repository. Hardware security keys are available from IT on request."),
    ]),
    "onboarding.pdf": ("New Employee Onboarding", [
        ("First week", "Collect your laptop from the IT desk on day one. A buddy is assigned to every new employee for the first month. Security awareness training must be completed within 5 days of your start date."),
        ("Reviews", "Your manager holds check-ins at 30, 60 and 90 days. The 90-day review confirms the end of your probation period."),
        ("Accounts", "IT creates your email, chat and code repository accounts before your start date. You will receive credentials by your personal email on the Friday before you start."),
    ]),
    "incident_response.md": ("Incident Response Runbook", [
        ("Severity levels", "SEV1 is a full outage or data exposure: the on-call engineer must respond within 15 minutes. SEV2 is a major degradation: respond within 1 hour. SEV3 is minor and handled in business hours."),
        ("On-call rotation", "The on-call rotation changes every Monday at 09:00. The current on-call engineer is listed in the status channel topic."),
        ("Postmortems", "A written postmortem is required for every SEV1 and SEV2 incident and must be published within 5 business days. Postmortems are blameless."),
    ]),
    "travel_policy.txt": ("Business Travel Policy", [
        ("Flights", "Book economy class for flights shorter than 6 hours. Business class may be booked for flights of 6 hours or longer with director approval. All bookings go through the Wayfarer travel portal."),
        ("Hotels", "Hotel stays are reimbursed up to USD 150 per night. Choose a hotel within the preferred list in the portal where possible."),
        ("Ground transport", "Use public transport or ride-share for local travel. Car rental requires manager approval in advance."),
    ]),
    "office_hours_holidays.md": ("Office Hours and Holidays", [
        ("Opening hours", "The office is open Monday to Friday from 08:00 to 18:00. Badge access outside these hours must be requested from facilities."),
        ("Company holidays", "The company is closed on 1 January, 17 August and 25 December. Floating holidays are not offered."),
        ("Visitors", "Visitors must be registered at reception in advance and wear a visitor badge at all times."),
    ]),
    "product_faq.pdf": ("Fiktiva Docs Product FAQ", [
        ("Plans", "The free plan includes 50 pages per month. The Pro plan costs USD 19 per month and includes 2000 pages per month."),
        ("Supported formats", "Fiktiva Docs accepts PDF, DOCX and PNG files. Handwriting recognition is not supported."),
        ("Data retention", "Uploaded files are deleted automatically after 30 days. Extracted results can be exported as CSV or JSON."),
    ]),
}


def write_pdf(path: Path, title: str, sections) -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10.5, leading=15)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for heading, para in sections:
        story += [Paragraph(heading, styles["Heading3"]), Paragraph(para, body), Spacer(1, 10)]
    SimpleDocTemplate(str(path), pagesize=A4, title=title).build(story)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (title, sections) in DOCS.items():
        path = OUT / name
        if name.endswith(".pdf"):
            write_pdf(path, title, sections)
        elif name.endswith(".md"):
            path.write_text(f"# {title}\n\n" + "\n\n".join(f"## {h}\n\n{p}" for h, p in sections) + "\n", encoding="utf-8")
        else:
            path.write_text(f"{title}\n\n" + "\n\n".join(f"{h}\n{p}" for h, p in sections) + "\n", encoding="utf-8")
    print(f"wrote {len(DOCS)} documents to {OUT}")


if __name__ == "__main__":
    main()
