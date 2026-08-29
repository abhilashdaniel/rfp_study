"""
Generates four fictional supplier RFP response PDFs for the same
procurement request (brief section 7), each with different strengths,
weaknesses, prices, schedules, and evidence quality.

Run:
    python generate_sample_pdfs.py
Outputs into data/sample_rfps/
"""
import os

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "sample_rfps")
os.makedirs(OUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()
h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceAfter=10)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6)
body = ParagraphStyle("body", parent=styles["BodyText"], spaceAfter=8, leading=14)


def build_pdf(filename, title, sections, price_table=None):
    path = os.path.join(OUT_DIR, filename)
    doc = SimpleDocTemplate(path, pagesize=LETTER, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    story = [Paragraph(title, h1), Spacer(1, 6)]

    for heading, paragraphs in sections:
        story.append(Paragraph(heading, h2))
        for p in paragraphs:
            story.append(Paragraph(p, body))
        if heading == "Price Table & Assumptions" and price_table:
            t = Table(price_table, hAlign="LEFT")
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(Spacer(1, 6))
            story.append(t)
            story.append(Spacer(1, 10))

    doc.build(story)
    print(f"Wrote {path}")


# ---------------------------------------------------------------------------
# RFP context shared across all four proposals (for realism)
# ---------------------------------------------------------------------------
RFP_CONTEXT = (
    "Request for Proposal: Supplier response to build and support a cloud-based "
    "order management platform for a mid-size retail distributor, including "
    "integration with existing ERP and payment systems."
)

# ---------------------------------------------------------------------------
# 1. Apex Systems - strong technical/security, higher price, moderate schedule
# ---------------------------------------------------------------------------
build_pdf(
    "Apex_Systems_RFP_Response.pdf",
    "Apex Systems — RFP Response: Order Management Platform",
    [
        ("Executive Summary", [
            RFP_CONTEXT,
            "Apex Systems proposes a cloud-native, microservices-based order management platform "
            "built for scalability, resilience, and long-term maintainability. Our architecture has "
            "been proven across three prior deployments of comparable scale.",
        ]),
        ("Proposed Solution & Implementation Approach", [
            "The solution is built on a Kubernetes-orchestrated microservices architecture with an "
            "event-driven backbone (Kafka) connecting order intake, inventory, and payment services. "
            "REST and webhook integrations are provided for the client's existing ERP (SAP) and payment "
            "gateway, with a dedicated integration layer to isolate future ERP changes.",
            "The platform is designed to scale horizontally to handle 10x current order volume during "
            "peak seasonal demand without architectural changes, based on load testing performed on "
            "our reference deployment.",
        ]),
        ("Timeline, Team Structure & Milestones", [
            "Estimated delivery: 20 weeks. Team: 1 solutions architect, 3 senior engineers, 1 QA lead, "
            "1 project manager (all dedicated full-time). Milestone 1 (Week 4): architecture sign-off and "
            "ERP integration spec. Milestone 2 (Week 10): core order + inventory services in staging. "
            "Milestone 3 (Week 16): payment integration and UAT. Milestone 4 (Week 20): production cutover.",
            "Risk plan includes a two-week buffer before cutover and a rollback plan to the client's "
            "current system if UAT exit criteria are not met.",
        ]),
        ("Price Table & Assumptions", [
            "Pricing assumes standard business-hours support during implementation and excludes "
            "third-party licensing for the client's existing ERP.",
        ]),
        ("Security, Compliance & Risk Controls", [
            "Apex maintains SOC 2 Type II and ISO 27001 certifications, renewed annually (certificates "
            "available on request). All data is encrypted at rest (AES-256) and in transit (TLS 1.3). "
            "Role-based access control and full audit logging are built into the platform core, not "
            "added as an afterthought. Quarterly third-party penetration testing is included in the "
            "support contract.",
            "A named security lead performs a dedicated architecture security review at Milestone 1.",
        ]),
        ("Support Model, Relevant Experience & References", [
            "24/7 support with a 1-hour critical-incident response SLA. Apex has delivered two prior "
            "order-management platforms for retail distributors of similar size (references available "
            "on request, NDA required). Support is staffed by the original delivery engineers for the "
            "first 6 months post-launch.",
        ]),
    ],
    price_table=[
        ["Item", "Cost (USD)", "Notes"],
        ["Implementation (fixed price)", "$420,000", "20-week delivery, team as described above"],
        ["Annual support & maintenance", "$96,000/yr", "24/7 SLA, quarterly pen testing included"],
        ["Total Year 1", "$516,000", "Implementation + first year support"],
    ],
)

# ---------------------------------------------------------------------------
# 2. BrightPath Tech - lowest price, fastest timeline, weak compliance/experience
# ---------------------------------------------------------------------------
build_pdf(
    "BrightPath_Tech_RFP_Response.pdf",
    "BrightPath Tech — RFP Response: Order Management Platform",
    [
        ("Executive Summary", [
            RFP_CONTEXT,
            "BrightPath Tech offers a lean, cost-effective order management solution built rapidly "
            "using our existing SaaS framework, customized for the client's needs at a fraction of "
            "typical enterprise pricing.",
        ]),
        ("Proposed Solution & Implementation Approach", [
            "We will configure our existing multi-tenant order management SaaS product for the "
            "client, adding custom fields and a basic integration connector to the client's ERP. "
            "Most functionality is delivered out-of-the-box with light customization rather than "
            "new development, which keeps costs and timeline low.",
            "Integration with the payment gateway will use a standard connector; deeper customization "
            "of payment workflows is available as a future phase if needed.",
        ]),
        ("Timeline, Team Structure & Milestones", [
            "Estimated delivery: 8 weeks. Team: 1 implementation consultant (part-time) and 1 developer. "
            "Milestone 1 (Week 2): environment provisioned. Milestone 2 (Week 5): configuration complete. "
            "Milestone 3 (Week 8): go-live.",
            "Note: this is an aggressive timeline assuming no major ERP data-mapping surprises.",
        ]),
        ("Price Table & Assumptions", [
            "Pricing assumes the client uses our standard SaaS connectors without deep customization. "
            "Custom integration work beyond the standard connector is billed separately at $150/hour.",
        ]),
        ("Security, Compliance & Risk Controls", [
            "Data is encrypted in transit. We follow general industry best practices for security. "
            "We are in the process of pursuing formal compliance certification but do not currently "
            "hold SOC 2 or ISO 27001 certification.",
        ]),
        ("Support Model, Relevant Experience & References", [
            "Support is provided via email ticketing with a target 24-48 hour response time during "
            "business hours. This will be our first deployment specifically for a retail distributor "
            "of this size; most of our current customers are smaller retail businesses.",
        ]),
    ],
    price_table=[
        ["Item", "Cost (USD)", "Notes"],
        ["Implementation (fixed price)", "$95,000", "8-week delivery, standard connectors only"],
        ["Annual support & maintenance", "$24,000/yr", "Email ticketing, business hours"],
        ["Total Year 1", "$119,000", "Implementation + first year support"],
    ],
)

# ---------------------------------------------------------------------------
# 3. NexaWorks - balanced, strongest implementation plan & support model
# ---------------------------------------------------------------------------
build_pdf(
    "NexaWorks_RFP_Response.pdf",
    "NexaWorks — RFP Response: Order Management Platform",
    [
        ("Executive Summary", [
            RFP_CONTEXT,
            "NexaWorks proposes a balanced solution combining proven modular architecture with a "
            "highly structured implementation methodology, minimizing delivery risk while keeping "
            "cost and timeline reasonable.",
        ]),
        ("Proposed Solution & Implementation Approach", [
            "The platform uses a modular service architecture (order, inventory, payment, notification "
            "services) deployed on managed cloud infrastructure. ERP integration uses a middleware "
            "adapter pattern that has been reused across four prior client engagements, reducing "
            "integration risk.",
            "Payment gateway integration follows the client's existing PCI-scoped workflow, minimizing "
            "changes to the client's compliance boundary.",
        ]),
        ("Timeline, Team Structure & Milestones", [
            "Estimated delivery: 14 weeks, using our structured 5-phase delivery methodology: "
            "Discovery (Weeks 1-2), Design (Weeks 3-4), Build (Weeks 5-10), Test & UAT (Weeks 11-13), "
            "Cutover (Week 14). Team: 1 delivery lead, 2 engineers, 1 QA engineer, all dedicated.",
            "Each phase ends with a formal client sign-off gate and a documented risk log review, "
            "including staffing contingency plans if a team member is unavailable.",
        ]),
        ("Price Table & Assumptions", [
            "Pricing assumes the client's ERP exposes a documented API; additional discovery time will "
            "be billed at standard rates if custom ERP work is required.",
        ]),
        ("Security, Compliance & Risk Controls", [
            "NexaWorks follows documented secure-SDLC practices and encrypts data at rest and in "
            "transit. We are currently mid-process on SOC 2 Type I certification (expected completion "
            "in 4 months) and can provide our internal security policy documentation on request.",
        ]),
        ("Support Model, Relevant Experience & References", [
            "Dedicated support team with a documented escalation path and a 4-hour response SLA for "
            "critical issues during business hours, 24-hour SLA otherwise. NexaWorks has delivered "
            "four similar order-management or inventory platforms in the retail and distribution "
            "sector over the past three years; two client references are available on request.",
        ]),
    ],
    price_table=[
        ["Item", "Cost (USD)", "Notes"],
        ["Implementation (fixed price)", "$260,000", "14-week delivery, structured 5-phase methodology"],
        ["Annual support & maintenance", "$54,000/yr", "4-hr critical SLA, business hours"],
        ["Total Year 1", "$314,000", "Implementation + first year support"],
    ],
)

# ---------------------------------------------------------------------------
# 4. Orbit Digital - strong experience/references, vague integration plan
# ---------------------------------------------------------------------------
build_pdf(
    "Orbit_Digital_RFP_Response.pdf",
    "Orbit Digital — RFP Response: Order Management Platform",
    [
        ("Executive Summary", [
            RFP_CONTEXT,
            "With over a decade of experience delivering retail technology platforms, Orbit Digital "
            "brings deep domain expertise and a proven track record to this engagement.",
        ]),
        ("Proposed Solution & Implementation Approach", [
            "Orbit Digital will build a custom order management system tailored to the client's "
            "workflows. The system will integrate with the client's ERP and payment systems using "
            "modern integration practices. Specific integration architecture will be finalized "
            "collaboratively with the client's technical team during the discovery phase.",
            "We prefer to keep initial technical design flexible so it can evolve based on discovery "
            "findings rather than being locked in during the proposal stage.",
        ]),
        ("Timeline, Team Structure & Milestones", [
            "Estimated delivery: 16 weeks (subject to refinement after discovery). Team: 1 account "
            "director, 2 engineers (allocation may flex based on concurrent projects). Milestones will "
            "be defined jointly with the client after discovery is complete.",
        ]),
        ("Price Table & Assumptions", [
            "Pricing is a not-to-exceed estimate; final scope and cost will be confirmed after the "
            "discovery phase, which is included in the price below.",
        ]),
        ("Security, Compliance & Risk Controls", [
            "Orbit Digital has extensive experience meeting enterprise security requirements across "
            "prior retail engagements. We hold ISO 27001 certification at the company level. Specific "
            "controls for this project (encryption approach, access model, audit logging) will be "
            "documented during the design phase.",
        ]),
        ("Support Model, Relevant Experience & References", [
            "Orbit Digital has delivered over 15 retail and e-commerce platforms over the past decade, "
            "including two large-scale order management systems for national retailers. Three client "
            "references are available, including a Fortune 500 retail account. Support model includes "
            "a named account manager and a shared support queue with a same-business-day response target.",
        ]),
    ],
    price_table=[
        ["Item", "Cost (USD)", "Notes"],
        ["Implementation (not-to-exceed estimate)", "$310,000", "16-week estimate, scope finalized post-discovery"],
        ["Annual support & maintenance", "$60,000/yr", "Same-business-day response target"],
        ["Total Year 1", "$370,000", "Implementation + first year support (estimate)"],
    ],
)

print("\nAll four synthetic supplier RFP PDFs generated in data/sample_rfps/")
