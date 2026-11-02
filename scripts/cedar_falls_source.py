"""Cedar Falls synthetic bid package: the one source for the PDFs and the golden labels (spec section 3, test set).

Everything here is fictional: the City of Cedar Falls, Tamarack Creek, Marlow Reed Associates, Tessaly Screen Systems,
and Norvane Drive Systems. The package stands in for three real packages the owner could not hand-label:
- Manor: a long spec book where only a few sections matter (several unlabeled filler sections, a divider sheet per
  division, one blank page).
- Sandy: a membrane equipment RFP with several addenda (three addenda: two due date changes, a replaced paragraph, a
  revised paragraph, a deleted paragraph, an added paragraph, a reissued section, and three questions and answers).
- Avila Beach: an MBR RFP with scoring tables and technical data forms (two scoring tables and Attachments A to C).

This file was written after the Phase 4 freeze and before the pipeline ever saw the package (CLAUDE.md rule 6). Nothing
here comes from a model, and none of it was tuned to how the pipeline reads a page.

Labeling rules applied here (spec section 9, labeling protocol; same as lakeview_source.py):
- Requirements are labeled only in relevant sections: the RFP, 00 21 13, 00 73 00, 01 33 00, 01 60 00, 46 21 23, 46 61 23,
  and the reissued 46 43 13 that Addendum 3 attaches.
- Every obligation sentence in a relevant section is labeled; descriptive text carries no "shall".
- One label per obligation. A label's source text is the paragraph text without its marker, unless the label names a
  clause with `source`.
- Permit text yields permit limits, not requirements: its obligations fall on the plant operator.
- Text an addendum replaces, revises, or deletes carries no label; the addendum's version does, with from_addendum set.
- Section 46 43 13 in the spec book is superseded by Addendum 3, so it carries no label and is not a relevant section;
  the reissued section in addendum_3 is the relevant one and every one of its requirements has from_addendum set.
"""

import random
from dataclasses import dataclass

try:
    from scripts.lakeview_source import (
        FICTION,
        Article,
        FillerSpec,
        L,
        P,
        RfpSection,
        SpecSection,
        Table,
        Trap,
        filler_section,
        lab,
        p,
    )
except ModuleNotFoundError:  # run as `python scripts/make_cedar_falls.py`
    from lakeview_source import (  # type: ignore[no-redef,import-not-found]
        FICTION,
        Article,
        FillerSpec,
        L,
        P,
        RfpSection,
        SpecSection,
        Table,
        Trap,
        filler_section,
        lab,
        p,
    )

PACKAGE_ID = "cedar_falls"
PROJECT = "Cedar Falls WPCF Phase 3 Improvements"
BLANK_AFTER = "31 23 00"
COMPETITOR = "Tessaly Screen Systems"
SOLE_SOURCE = "Norvane Drive Systems"


@dataclass(frozen=True)
class FrontSection:
    """A Division 00 section in article form: ARTICLE 1 - TITLE, paragraphs 1.1, 1.2 with sub-items a., b."""

    number: str
    title: str
    articles: tuple[RfpSection, ...]
    relevant: bool = True


@dataclass(frozen=True)
class SeasonalLimit:
    row: int  # index into the permit table rows
    limit_type: str
    value: float
    season: str | None


@dataclass(frozen=True)
class AddLabel:
    """A labeled obligation in an addendum: the section and paragraph it changes, its text, and its label."""

    section: str | None
    paragraph: str
    text: str
    label: L


@dataclass(frozen=True)
class AddendumDoc:
    doc_id: str
    addendum_id: str  # "Addendum 3"
    short: str  # how the header names it: "Addendum No. 3"
    items: tuple[str | P | Table, ...]
    labels: tuple[AddLabel, ...]
    changes: tuple[tuple[str, str | None, str | None], ...]  # (action, target section, target paragraph)
    deadline: tuple[str, str] | None = None  # (brief text, the item text that holds it)
    reissued: SpecSection | None = None


# --- RFP -------------------------------------------------------------------------------------------------------------

RFP_COVER = [
    "CITY OF CEDAR FALLS",
    "REQUEST FOR PROPOSALS",
    "FINE SCREEN, CLARIFIER MECHANISM, AND MEMBRANE BIOREACTOR EQUIPMENT PRESELECTION",
    "CEDAR FALLS WATER POLLUTION CONTROL FACILITY PHASE 3 IMPROVEMENTS",
    "RFP No. CF-2026-14",
    "Issued November 2, 2026",
    "Department of Public Utilities, 218 Mill Street, Cedar Falls",
    FICTION,
]

PRE_PROPOSAL = "Mandatory pre-proposal meeting on November 12, 2026 at 10:00 AM"
QUESTIONS_DUE = "Written questions due November 19, 2026"

RFP = [
    RfpSection(1, "INTRODUCTION", (
        p("The City of Cedar Falls (Owner) is expanding and upgrading the Cedar Falls Water Pollution Control Facility "
          "(WPCF) to meet a new total nitrogen limit in its discharge permit."),
        p("The Owner is preselecting the fine screen, secondary clarifier mechanism, and membrane bioreactor equipment "
          "for the project. The selected Supplier will be assigned to the general contractor, who will install the "
          "equipment under the supervision of the Supplier's representative."),
        p("The Owner's engineer for the project is Marlow Reed Associates (Engineer)."),
        p("The equipment is specified in Sections 46 21 23, 46 43 13, and 46 61 23 of the Technical Specifications, "
          "which form part of this Request for Proposals. Bidding requirements are in Division 00 and general "
          "requirements are in Division 01 of the Technical Specifications."),
        p("The existing WPCF was built in 1984 and expanded in 2003. It provides screening, grit removal, conventional "
          "activated sludge treatment, secondary clarification, and ultraviolet disinfection. Waste sludge is "
          "thickened, anaerobically digested, and dewatered on a belt filter press."),
        p("The Phase 3 Improvements add fine screens at the headworks, replace the sludge collection mechanisms in the "
          "two existing secondary clarifiers, and convert one aeration basin to a membrane bioreactor (MBR) train. "
          "The existing conventional train will remain in service beside the new MBR train."),
        p("The plant serves about 22,000 residents and a small food processing industry. The annual average flow is "
          "2.4 MGD, and the plant will be rated for 3.0 MGD after the upgrade. Wet weather flows reach 7.5 MGD during "
          "spring thaw."),
        p("The discharge permit issued by the Cedar State Department of Environmental Quality limits total nitrogen to "
          "3.0 mg/L from May 1 through October 31, beginning July 1, 2030. An excerpt of the permit is included with "
          "this Request for Proposals."),
        p("The Owner expects to advertise the construction contract in the fall of 2027 and to complete construction "
          "by the end of 2029."),
        p("Record drawings of the existing plant are available from the Engineer on request."),
        p("The existing aeration basins are 14 feet deep and are divided into anoxic and aerobic zones. The two "
          "secondary clarifiers are 80 feet in diameter and were built with the original plant."),
        p("The Owner's goals for this procurement are to select equipment that meets the nitrogen limit with margin, "
          "to confirm the performance of the membrane system on the plant's own wastewater, and to fix the equipment "
          "and its price before the construction contract is advertised."),
        p("Equipment from the preselected Supplier will be furnished to the general contractor as an owner "
          "supplied item. The general contractor will be responsible for receiving, storing, and installing it."),
    )),
    RfpSection(2, "EXISTING PLANT DATA", (
        p("The data below describe the existing plant and the wastewater it treats. The Owner provides these data for "
          "information. They are averages of the plant records for 2024 and 2025."),
        Table(("Parameter", "Existing Plant Value"), (
            ("Annual average flow", "2.4 MGD"),
            ("Maximum month flow", "3.1 MGD"),
            ("Peak day flow", "5.2 MGD"),
            ("Peak hour flow", "7.5 MGD"),
            ("Influent BOD5, average", "260 mg/L"),
            ("Influent TSS, average", "290 mg/L"),
            ("Influent total Kjeldahl nitrogen, average", "52 mg/L"),
            ("Influent total phosphorus, average", "7.5 mg/L"),
            ("Influent alkalinity, average", "210 mg/L as CaCO3"),
            ("Wastewater temperature, winter low", "8 degrees C"),
            ("Wastewater temperature, summer high", "24 degrees C"),
            ("Mixed liquor suspended solids, conventional train", "3,200 mg/L"),
            ("Effluent total nitrogen, conventional train, annual average", "9.5 mg/L"),
        )),
        p("The existing plant effluent has met the current permit limits for BOD5, TSS, and ammonia nitrogen in each of "
          "the past 36 months."),
        p("The existing secondary clarifiers are circular tanks with center drives that were installed in 1984. The "
          "drives and the sludge collection mechanisms are at the end of their service life."),
        p("The headworks has two channels with manual bar screens. The new fine screens will replace the bar screens "
          "in these channels."),
        p("The plant's food processing customer discharges to the sewer on weekdays from 6 AM to 6 PM. The discharge "
          "raises the influent flow, BOD5, and grease during those hours."),
        Table(("Permit Parameter", "Summer Limit", "Winter Limit"), (
            ("Total nitrogen, monthly average", "3.0 mg/L", "8.0 mg/L"),
            ("Ammonia nitrogen, monthly average", "1.0 mg/L", "2.5 mg/L"),
            ("CBOD5, monthly average", "10 mg/L", "10 mg/L"),
            ("TSS, monthly average", "12 mg/L", "12 mg/L"),
        )),
        p("The full permit excerpt follows the Technical Specifications in the proposal package."),
    )),
    RfpSection(3, "SCOPE OF SUPPLY", (
        p("The Supplier shall furnish two traveling band fine screens, two circular secondary clarifier mechanisms, and "
          "one submerged membrane bioreactor system as specified.", lab("commercial")),
        p("The Supplier shall provide engineering, fabrication, delivery to the site, installation inspection, startup, "
          "performance testing, and operator training for the equipment.", lab("commercial")),
        p("Equipment shall be delivered to the site within 36 weeks after approval of the shop drawings.",
          lab("schedule", "delivery time after shop drawing approval", "<=", "36", "weeks")),
        p("Shop drawings shall be submitted within 12 weeks after the notice of selection.",
          lab("schedule", "shop drawing submittal time", "<=", "12", "weeks")),
        p("The Supplier may offer a factory-assembled cassette lifting frame as an option.",
          lab("commercial", m=False)),
    )),
    RfpSection(4, "PROCUREMENT SCHEDULE", (
        p("Key dates for this procurement are listed below."),
        Table(("Event", "Date"), (
            ("Request for Proposals issued", "November 2, 2026"),
            ("Mandatory pre-proposal meeting", "November 12, 2026 at 10:00 AM"),
            ("Deadline for written questions", "November 19, 2026"),
            ("Proposal due date", "December 3, 2026 at 2:00 PM"),
            ("Interviews with the highest scoring Proposers", "Week of January 11, 2027"),
            ("Notice to proceed with pilot testing", "January 29, 2027"),
            ("Pilot testing", "February 2027 through July 2027"),
            ("Anticipated notice of selection", "August 2027"),
        )),
        p("Attendance at the pre-proposal meeting on November 12, 2026 at 10:00 AM is mandatory for every Proposer.",
          lab("schedule", deadline=PRE_PROPOSAL)),
        p("Proposals shall be submitted electronically through the City's bid portal and as one printed original in a "
          "sealed envelope delivered to the City Clerk, 218 Mill Street, Cedar Falls.",
          lab("submittal", source="Proposals shall be submitted electronically through the City's bid portal"),
          lab("submittal", source="as one printed original in a sealed envelope delivered to the City Clerk, "
                                  "218 Mill Street, Cedar Falls")),
        p("Written questions about this Request for Proposals shall be submitted to the Engineer no later than "
          "November 19, 2026.", lab("submittal", deadline=QUESTIONS_DUE)),
    )),
    RfpSection(5, "PROPOSER QUALIFICATIONS", (
        p("The Supplier shall demonstrate at least four (4) full scale installations of the proposed membrane system "
          "in municipal wastewater service at a design flow of 1.5 MGD or more.",
          lab("qualification", "reference installations", ">=", "4", "installations", flag="experience_minimum")),
        p("Each installation shall be listed on Attachment C with the owner's name, a contact person, the design flow, "
          "and the startup date.", lab("submittal")),
        p("The Supplier shall maintain a service center able to place a technician on site within 72 hours of a "
          "request.", lab("qualification", "service response time", "<=", "72", "hours")),
        p("The Supplier should identify the technicians who will perform startup service.",
          lab("qualification", m=False)),
    )),
    RfpSection(6, "PILOT TESTING", (
        p("The two highest scoring Proposers shall each conduct an on site pilot test of the proposed membrane system "
          "for not less than 150 days.",
          lab("testing_piloting", "pilot test duration", ">=", "150", "days", flag="pilot_testing")),
        p("The pilot unit shall be operated on the mixed liquor of the existing plant.", lab("testing_piloting")),
        p("During the final 30 days of operation, the pilot shall demonstrate permeate total nitrogen not exceeding "
          "3 mg/L.", lab("testing_piloting", "pilot permeate total nitrogen", "<=", "3", "mg/L")),
        p("The Owner will provide power, potable water, and a lined pad for the pilot unit."),
        p("The Supplier shall submit a pilot test report within 21 days after the end of pilot testing.",
          lab("submittal", "pilot report submittal time", "<=", "21", "days")),
        p("The cost of pilot testing shall be included in the proposal price.", lab("commercial")),
    )),
    RfpSection(7, "WARRANTY AND PERFORMANCE GUARANTEE", (
        p("The Supplier shall warrant all equipment against defects in materials and workmanship for 12 months after "
          "startup.", lab("warranty", "equipment warranty", "=", "12", "months")),
        p("The Supplier shall provide a process performance guarantee for the membrane bioreactor system, effective "
          "for 12 months after startup.", lab("warranty", "process performance guarantee period", "=", "12", "months")),
        p("If the performance guarantee is not met, the Supplier shall furnish corrective equipment and labor at no "
          "cost to the Owner.", lab("warranty")),
    )),
    RfpSection(8, "COMMERCIAL TERMS", (
        p("Proposal prices shall remain valid for 90 days after the proposal due date.",
          lab("commercial", "price validity", ">=", "90", "days")),
        p("The selected Supplier shall furnish a performance bond and a payment bond, each equal to 100 percent of the "
          "contract price.", lab("commercial", "performance and payment bond amount", "=", "100", "percent",
                                 flag="bond")),
        p("Payment shall be made monthly on the percentage of work completed, less 10 percent retainage.",
          lab("commercial", "retainage", "=", "10", "percent")),
        p("The Supplier shall maintain commercial general liability insurance of not less than $1,000,000 per "
          "occurrence.", lab("commercial", "general liability insurance", ">=", "1,000,000", "USD")),
        p("The Supplier shall name the Owner and the Engineer as additional insureds on its general liability policy.",
          lab("commercial")),
        p("Liquidated damages, delivery, and warranty start terms are stated in Section 00 73 00 Supplementary "
          "Conditions."),
    )),
    RfpSection(9, "EVALUATION OF PROPOSALS", (
        p("Proposals will be scored on the criteria below."),
        Table(("Criterion", "Points"), (
            ("Technical approach and equipment quality", "30"),
            ("Life cycle cost", "30"),
            ("Experience and references", "15"),
            ("Pilot test results", "15"),
            ("Schedule and delivery", "10"),
            ("Total", "100"),
        )),
        p("Each criterion will be rated on the scale below, and the rating will set the share of the available points "
          "that the proposal earns."),
        Table(("Rating", "Share of available points"), (
            ("Excellent", "90 to 100 percent"),
            ("Good", "75 to 89 percent"),
            ("Fair", "60 to 74 percent"),
            ("Poor", "Less than 60 percent"),
        )),
        p("A selection committee of the Owner's staff and the Engineer will score each proposal. Life cycle cost will "
          "be calculated over 20 years at a discount rate of 3 percent, using the energy, chemical, and membrane "
          "replacement values stated on Attachment B."),
        p("Proposers shall state the guaranteed energy, chemical, and membrane replacement values on Attachment B.",
          lab("submittal")),
        p("The Owner may interview the two highest scoring Proposers before pilot testing begins."),
        p("The Owner reserves the right to reject any or all proposals and to waive informalities."),
        p("Proposers should visit the existing plant before submitting a proposal.", lab("commercial", m=False)),
    )),
    RfpSection(10, "PROPOSAL CONTENTS AND FORMS", (
        p("The proposal shall include a completed Attachment A, Proposal Form.", lab("submittal")),
        p("The proposal shall include a completed Attachment B, Technical Data Form 1, Membrane System.",
          lab("submittal")),
        p("The proposal shall include a completed Attachment C, Technical Data Form 2, Experience and Warranty.",
          lab("submittal")),
        p("Values entered on the Technical Data Forms shall be guaranteed values, not typical values.",
          lab("warranty")),
    )),
]

FORM_A = "ATTACHMENT A - PROPOSAL FORM"
FORM_B = "ATTACHMENT B - TECHNICAL DATA FORM 1: MEMBRANE SYSTEM"
FORM_C = "ATTACHMENT C - TECHNICAL DATA FORM 2: EXPERIENCE AND WARRANTY"
FORM_SECTION = "10"

FORM_A_TABLE = Table(("Item", "Description", "Lump Sum Price"), (
    ("1", "Traveling band fine screens (2)", "$"),
    ("2", "Circular secondary clarifier mechanisms (2)", "$"),
    ("3", "Submerged membrane bioreactor system, three trains", "$"),
    ("4", "Pilot testing", "$"),
    ("5", "Optional cassette lifting frame", "$"),
    ("6", "Total proposal price", "$"),
))
FORM_A_ADDENDA = Table(("Addendum", "Date Received", "Initials"), (
    ("Addendum No. 1", "", ""), ("Addendum No. 2", "", ""), ("Addendum No. 3", "", ""), ("Addendum No. ____", "", ""),
))
FORM_B_TABLE = Table(("No.", "Data Item", "Unit", "Proposer's Response"), (
    ("1", "Membrane model and material", "text", ""),
    ("2", "Nominal pore size", "micron", ""),
    ("3", "Membrane area per cassette", "sq ft", ""),
    ("4", "Number of cassettes per train", "each", ""),
    ("5", "Design net flux at average day flow", "gfd", ""),
    ("6", "Design net flux at peak hour flow", "gfd", ""),
    ("7", "Operating transmembrane pressure, maximum", "psi", ""),
    ("8", "Air scour demand per train", "scfm", ""),
    ("9", "Installed power per train", "kW", ""),
    ("10", "Guaranteed permeate turbidity", "NTU", ""),
    ("11", "Guaranteed permeate total suspended solids", "mg/L", ""),
    ("12", "Guaranteed permeate BOD5", "mg/L", ""),
    ("13", "Guaranteed permeate total nitrogen", "mg/L", ""),
    ("14", "Maintenance clean frequency", "per week", ""),
    ("15", "Recovery clean interval", "months", ""),
    ("16", "Sodium hypochlorite use", "lb per year", ""),
    ("17", "Citric acid use", "lb per year", ""),
    ("18", "Expected membrane replacement interval", "years", ""),
    ("19", "Membrane replacement cost per module", "USD", ""),
    ("20", "Annual energy use at design average flow", "kWh per year", ""),
    ("21", "Pilot unit size", "gpm", ""),
    ("22", "Pilot unit availability", "date", ""),
))
FORM_C_TABLE = Table(("No.", "Data Item", "Response"), (
    ("1", "Number of installations of the proposed membrane system", ""),
    ("2", "Number of those installations treating municipal wastewater", ""),
    ("3", "Number of those installations with a design flow of 1.5 MGD or more", ""),
    ("4", "Equipment warranty offered, months from startup", ""),
    ("5", "Membrane module warranty offered, years", ""),
    ("6", "Process performance guarantee offered, months", ""),
    ("7", "Location of nearest service center", ""),
    ("8", "Travel time from service center to Cedar Falls, hours", ""),
))
FORM_C_REFS = Table(("Installation", "Location", "Contact", "Design Flow (MGD)", "Startup Date"),
                    tuple(("", "", "", "", "") for _ in range(5)))

# --- Division 00 front end ---------------------------------------------------------------------------------------------

S002113 = FrontSection("00 21 13", "INSTRUCTIONS TO PROPOSERS", (
    RfpSection(1, "SUMMARY", (
        p("This Section describes the procedures for preparing and submitting proposals under the Request for "
          "Proposals."),
        p("Terms defined in the Request for Proposals have the same meaning in this Section."),
    )),
    RfpSection(2, "EXAMINATION OF DOCUMENTS", (
        p("Proposers shall report any conflict, error, or omission found in the Contract Documents to the Engineer in "
          "writing before the deadline for written questions.", lab("submittal")),
    )),
    RfpSection(3, "ADDENDA", (
        p("Addenda will be issued by the Engineer and posted on the City's bid portal."),
        p("Proposers shall acknowledge receipt of each addendum on Attachment A.", lab("submittal")),
        p("The most recent addendum governs where it conflicts with an earlier addendum or with the Technical "
          "Specifications."),
    )),
    RfpSection(4, "SUBSTITUTIONS AND APPROVED EQUALS", (
        p("Where the Technical Specifications name a manufacturer and model with the words or approved equal, the "
          "named product establishes the standard of quality."),
        p("Requests for approval of an equal product shall be received by the Engineer at least 10 days before the "
          "proposal due date.",
          lab("schedule", "approved equal request lead time", ">=", "10", "days",
              deadline="Requests for approval of an equal product due at least 10 days before the proposal due date")),
        p("Each request shall include the manufacturer's product data, a list of at least three installations, and a "
          "point by point comparison with the named product.", lab("submittal")),
        p("The Engineer will respond to each request by addendum."),
    )),
    RfpSection(5, "PROPOSAL SUBMISSION", (
        p("Each proposal shall be bound and tabbed in the order of Section 10 of the Request for Proposals.",
          lab("submittal")),
    )),
))

S007300 = FrontSection("00 73 00", "SUPPLEMENTARY CONDITIONS", (
    RfpSection(1, "LIQUIDATED DAMAGES", (
        p("The Supplier shall pay the Owner liquidated damages of $1,000 per calendar day for each day that delivery "
          "of the equipment is delayed beyond the delivery date in the purchase order.",
          lab("commercial", "liquidated damages", "=", "1,000", "USD/day", flag="liquidated_damages")),
    )),
    RfpSection(2, "DELIVERY AND INSURANCE IN TRANSIT", (
        p("The Supplier shall ship equipment to arrive at the site not earlier than 30 days before the scheduled "
          "installation date.", lab("schedule", "delivery window before installation", "<=", "30", "days")),
        p("The Supplier shall insure all equipment in transit for its full replacement value.", lab("commercial")),
    )),
    RfpSection(3, "WARRANTY", (
        p("The warranty period for all equipment shall begin on the date of substantial completion of the project.",
          lab("warranty")),
        p("Defective equipment shall be repaired or replaced at the Supplier's cost, including removal and "
          "reinstallation.", lab("warranty")),
    )),
))


# --- Division 01 -----------------------------------------------------------------------------------------------------

def _refs(*items: str) -> P:
    return p("The following standards apply to the work of this Section:", kids=tuple(p(i) for i in items))


TRAP2_TEXT = ("The certificate of proper installation shall be signed by the manufacturer's authorized representative "
              "and submitted within 10 days after completion of the installation inspection.")
SUBMITTAL_SIZE_OLD = "Individual submittal files shall not exceed 50 MB."
SUBMITTAL_SIZE_NEW = "Individual submittal files shall not exceed 100 MB."

S013300 = SpecSection("01 33 00", "SUBMITTAL PROCEDURES", (
    (
        Article("SUMMARY", (
            p("This Section describes the procedures for preparing and transmitting submittals required by the "
              "Contract Documents."),
            p("Submittal requirements for individual equipment items are stated in the equipment Sections."),
        )),
        Article("DEFINITIONS", (
            p("Action submittals: written and graphic information that requires the Engineer's responsive action."),
            p("Informational submittals: written information that does not require the Engineer's approval."),
            p("Closeout submittals: manuals, certificates, and record documents delivered at the end of the work."),
        )),
        Article("SUBMITTAL SCHEDULE", (
            p("The Supplier shall submit a submittal schedule within 10 days after the notice to proceed.",
              lab("submittal", "submittal schedule lead time", "<=", "10", "days")),
            p("Allow 28 days for the Engineer's review of each submittal.",
              lab("schedule", "engineer review period", "=", "28", "days")),
        )),
        Article("SUBMITTAL FORMAT", (
            p("Each submittal shall be transmitted electronically as a searchable PDF file.",
              lab("submittal")),
            p("Each submittal shall be identified by specification Section number and paragraph number.",
              lab("submittal")),
            p(SUBMITTAL_SIZE_OLD),  # revised by Addendum 2
            p("Submittals should be organized in the order of the specification paragraphs.",
              lab("submittal", m=False)),
        )),
        Article("SHOP DRAWINGS AND PRODUCT DATA", (
            p("Shop drawings shall show dimensions, materials, equipment weights, and anchor bolt locations.",
              lab("submittal")),
            p("Product data shall be marked to show the specific model, options, and accessories proposed.",
              lab("submittal")),
        )),
        Article("OPERATION AND MAINTENANCE DATA", (
            p("Operation and maintenance manuals shall be submitted at least 3 weeks before startup.",
              lab("submittal", "O&M manual submittal lead time", ">=", "3", "weeks")),
            p("Manuals shall include equipment descriptions, operating procedures, lubrication schedules, "
              "troubleshooting guides, and a recommended spare parts list.", lab("submittal")),
        )),
        Article("CERTIFICATES OF PROPER INSTALLATION", (
            p(TRAP2_TEXT, lab("certification", "installation certificate submittal time", "<=", "10", "days",
                              trap=2)),
        )),
        Article("RESUBMITTALS", (
            p("Resubmittals shall identify every change made since the previous submission.", lab("submittal")),
        )),
    ),
    (),
    (),
), relevant=True)

S016000 = SpecSection("01 60 00", "PRODUCT REQUIREMENTS", (
    (
        Article("SUMMARY", (
            p("This Section describes general requirements for products incorporated into the Work."),
        )),
        Article("DOMESTIC CONTENT", (
            p("All iron and steel products, manufactured products, and construction materials incorporated into the "
              "Work shall comply with the Build America, Buy America Act (BABA).",
              lab("domestic_content", flag="domestic_content")),
            p("The Supplier shall submit a BABA compliance certification with each invoice.",
              lab("domestic_content")),
        )),
    ),
    (
        Article("PRODUCT QUALITY", (
            p("Products shall be new, of current manufacture, and suitable for the service intended.",
              lab("material")),
            p("Products that are not covered by an equipment Section are described in the Divisions that cover "
              "them."),
        )),
    ),
    (),
), relevant=True)


# --- Division 46 equipment sections ----------------------------------------------------------------------------------

SCREEN_DELETED = ("The washer compactor shall reduce the organic content of the screenings by not less than 70 "
                  "percent.")

S462123 = SpecSection("46 21 23", "TRAVELING BAND FINE SCREENS", (
    (
        Article("SUMMARY", (
            p("Section includes two traveling band fine screens, screenings washer compactors, and local control "
              "panels for the new headworks channels."),
            p("Related sections: Section 01 33 00 Submittal Procedures and Section 01 60 00 Product Requirements."),
        )),
        Article("REFERENCES", (
            _refs("ANSI/AGMA 6013 - Standard for Industrial Enclosed Gear Drives.",
                  "ASTM A240/A240M - Chromium and Chromium-Nickel Stainless Steel Plate, Sheet, and Strip.",
                  "ASTM A276/A276M - Stainless Steel Bars and Shapes.",
                  "ASTM D4101 - Polypropylene Injection and Extrusion Materials.",
                  "NEMA 250 - Enclosures for Electrical Equipment (1000 Volts Maximum).",
                  "NEMA MG 1 - Motors and Generators.",
                  "NFPA 70 - National Electrical Code.",
                  "UL 508A - Industrial Control Panels."),
        )),
        Article("DESIGN CONDITIONS", (
            p("Each screen shall be designed for a peak hour flow of 7.5 MGD with the other screen out of service.",
              lab("design_basis", "screen design peak flow", "=", "7.5", "MGD")),
            p("The headworks channels are 4 feet wide, and the screens will be installed in the existing "
              "channels after the channels are drained and cleaned."),
        )),
        Article("SYSTEM DESCRIPTION", (
            p("The traveling band screens remove rags, hair, and trash from the raw wastewater to protect the "
              "downstream membrane system."),
            p("Screenings are lifted on the moving panels, washed off by the spray bar, and conveyed to the "
              "washer compactors."),
            p("Wastewater enters each screen from the front, flows through the perforated panels, and leaves "
              "through the bottom of the frame to the channel downstream. A seal plate closes the gap between the "
              "frame and the channel floor."),
            p("The panels are connected to a pair of drive chains that run over the head sprockets at the top of "
              "the frame. As the panels travel up the back of the screen, the spray bar washes the screenings into "
              "the discharge chute."),
            p("A differential level sensor starts the screen when the screenings build up on the panels. The "
              "screen also runs on a timer to keep the panels clean in low flow periods."),
            p("The washer compactor receives the screenings from the discharge chute, washes out fecal matter, and "
              "presses the screenings into a bagging or conveying chute."),
        )),
        Article("QUALITY ASSURANCE", (
            p("The screen manufacturer shall have at least 10 band screen installations in municipal service in "
              "North America.", lab("qualification", "manufacturer installed base", ">=", "10", "installations")),
        )),
        Article("WARRANTY", (
            p("The band screens shall be warranted against defects in materials and workmanship for 36 months after "
              "startup.", lab("warranty", "band screen warranty", "=", "36", "months")),
        )),
    ),
    (
        Article("MANUFACTURERS", (
            p(f"Band screens shall be {COMPETITOR} Model TS-4400, or approved equal.",
              lab("material", named_manufacturer=(COMPETITOR,), or_equal_allowed=True, trap=4,
                  flag="named_manufacturer")),
        )),
        Article("SCREEN COMPONENTS", (
            p("Screen frames shall be Type 304L stainless steel with polypropylene panels.",
              lab("material", "frame and panel material")),
            p("Screen panels shall have round perforations of 3 mm.",
              lab("design_basis", "screen panel perforation", "=", "3", "mm")),
            p("Fasteners and anchor bolts shall be Type 316 stainless steel.",
              lab("material", "fastener material")),
            p("Headloss through a clean screen shall not exceed 12 inches at peak hour flow.",
              lab("performance", "clean screen headloss", "<=", "12", "inches")),
        )),
        Article("SPRAY WASH SYSTEM", (
            p("The spray wash water demand of each screen shall not exceed 40 gpm at 60 psi.",
              lab("performance", "spray wash water demand", "<=", "40", "gpm")),
            p("Spray nozzles should be of the quick disconnect type.", lab("material", m=False)),
        )),
        Article("SCREENINGS HANDLING", (
            p("Screenings discharged from each screen shall have a dry solids content of not less than 25 percent.",
              lab("performance", "screenings dry solids", ">=", "25", "percent")),
            p("Provide one screenings washer compactor for each screen.", lab("performance")),
            p(SCREEN_DELETED),  # deleted by Addendum 2
        )),
        Article("CONTROLS", (
            p("Each screen shall be furnished with a local control panel in a NEMA 4X stainless steel enclosure.",
              lab("material", "control panel enclosure")),
            p("Screen drive motors shall be 460 volts, 3 phase, 60 Hz, and totally enclosed fan cooled.",
              lab("material", "motor voltage", "=", "460", "volts")),
        )),
    ),
    (
        Article("INSTALLATION", (
            p("The general contractor installs the screens in the drained channels and sets the anchor bolts in "
              "epoxy grout."),
        )),
        Article("FIELD TESTING", (
            p("After installation, each screen shall be operated continuously for not less than 12 hours without "
              "malfunction.", lab("testing_piloting", "screen field test duration", ">=", "12", "hours")),
        )),
        Article("MANUFACTURER'S SERVICES", (
            p("Provide a manufacturer's representative on site for not less than 3 days for installation inspection "
              "and startup of the screens.", lab("commercial", "screen field service", ">=", "3", "days")),
            p("Provide not less than 4 hours of operator training on the screens.",
              lab("commercial", "screen operator training", ">=", "4", "hours")),
        )),
    ),
), relevant=True)


def clarifier(reissued: bool) -> SpecSection:
    """Section 46 43 13 as bound in the spec book (superseded, no labels) or as reissued by Addendum 3 (labeled)."""
    def q(text: str, *labels: L) -> P:
        return p(text, *(labels if reissued else ()))

    diameter, torque, life = ("80", "85,000", "25") if reissued else ("70", "55,000", "20")
    months, dry, wet, tip = ("24", "1", "48", "15") if reissued else ("12", "4", "24", "10")
    days = "2" if reissued else "3"
    drive = (f"The clarifier drive unit shall be furnished by {SOLE_SOURCE}, Series ND-9, and no substitutions will be "
             "considered.") if reissued else (f"The clarifier drive unit shall be {SOLE_SOURCE} Series ND-9, or "
                                              "approved equal.")
    drive_label = lab("material", named_manufacturer=(SOLE_SOURCE,), or_equal_allowed=not reissued,
                      flag="named_manufacturer")
    coating = ("Submerged carbon steel shall be blast cleaned to SSPC-SP 10 and coated with a two-coat epoxy system."
               if reissued else "Submerged carbon steel shall be galvanized after fabrication in accordance with "
                                "ASTM A123.")
    dry_unit = "hour" if dry == "1" else "hours"
    return SpecSection("46 43 13", "CIRCULAR SECONDARY CLARIFIER EQUIPMENT", (
        (
            Article("SUMMARY", (
                p("Section includes two center drive circular sludge collection mechanisms with scum skimming "
                  "equipment, for the existing secondary clarifiers."),
                p("Related sections: Section 01 33 00 Submittal Procedures and Section 01 60 00 Product "
                  "Requirements."),
            )),
            Article("REFERENCES", (
                _refs("ANSI/AGMA 2001 - Fundamental Rating Factors and Calculation Methods for Involute Spur and "
                      "Helical Gear Teeth.",
                      "AISC 360 - Specification for Structural Steel Buildings.",
                      "ASTM A36/A36M - Carbon Structural Steel.",
                      "ASTM A123/A123M - Zinc (Hot-Dip Galvanized) Coatings on Iron and Steel Products.",
                      "AWS D1.1 - Structural Welding Code - Steel.",
                      "SSPC-SP 10 - Near-White Blast Cleaning."),
            )),
            Article("DEFINITIONS", (
                p("Center drive: a drive unit mounted on a bridge over the center of the tank that turns the "
                  "collector arms."),
                p("Collector arm: a truss or arm that carries the scraper blades across the tank floor."),
                p("Continuous torque rating: the torque that the drive delivers continuously without exceeding the "
                  "rating of its gearing or its motor."),
                p("Influent well: a baffled cylinder at the center of the tank that dissipates the energy of the "
                  "incoming flow."),
                p("Scum box: a box at the tank wall that receives scum from the skimmer."),
                p("Squeegee: a replaceable rubber strip along the bottom edge of a scraper blade."),
                p("Torque overload device: a device that measures the drive torque and trips an alarm or stops the "
                  "motor at set points."),
            )),
            Article("SYSTEM DESCRIPTION", (
                p("The mechanisms collect settled sludge from the tank floor and move it to a center hopper, where "
                  "the return sludge pumps draw it off. A rotating skimmer collects scum from the tank surface and "
                  "pushes it to a scum box at the tank wall."),
                p("A center drive turns a truss that carries the collector arms and the skimmer. The drive sits on a "
                  "bridge that spans the tank, and the walkway on the bridge gives access to the drive for "
                  "service."),
                p("Influent enters through the center column and passes through an energy dissipating influent "
                  "well. Effluent leaves over the weirs around the tank perimeter."),
            )),
            Article("DESIGN CONDITIONS", (
                q(f"Each mechanism shall be furnished for an existing tank {diameter} feet in diameter.",
                  lab("design_basis", "tank diameter", "=", diameter, "feet")),
                p("The existing tanks were built in 1984 and have a side water depth of 14 feet."),
                p("The tanks stay in service during the work, one at a time, while the conventional train runs on the "
                  "other clarifier."),
                p("The existing center columns, bridges, and walkways are reused. The new mechanisms are bolted to "
                  "the existing center columns."),
            )),
            Article("WARRANTY", (
                q(f"The clarifier mechanisms shall be warranted against defects in materials and workmanship for "
                  f"{months} months after startup.", lab("warranty", "clarifier warranty", "=", months, "months")),
            )),
        ),
        (
            Article("MANUFACTURERS", (q(drive, drive_label),)),
            Article("DRIVE UNIT", (
                q(f"The drive shall have a continuous torque rating of not less than {torque} ft-lb.",
                  lab("performance", "drive continuous torque", ">=", torque, "ft-lb")),
                q(f"The drive shall be rated for a service life of not less than {life} years at continuous torque.",
                  lab("performance", "drive service life", ">=", life, "years")),
                q("Drive motors shall be 460 volts, 3 phase, totally enclosed, and not larger than 2 hp.",
                  lab("material", "drive motor size", "<=", "2", "hp")),
            )),
            Article("CONTROLS AND ALARMS", (
                q("The torque overload device shall sound an alarm at 100 percent of the continuous torque rating.",
                  lab("performance", "torque alarm setpoint", "=", "100", "percent")),
                q("The torque overload device shall shut down the drive motor at 120 percent of the continuous torque "
                  "rating.", lab("performance", "torque shutdown setpoint", "=", "120", "percent")),
            )),
            Article("COLLECTOR ARMS AND SCRAPERS", (
                q(f"Scraper blades shall travel at a tip speed of not more than {tip} feet per minute.",
                  lab("performance", "scraper tip speed", "<=", tip, "feet per minute")),
                p("The collector arms carry the steel scraper blades and the replaceable squeegees."),
            )),
            Article("MATERIALS AND COATINGS", (
                q(coating, lab("material", "submerged steel coating")),
                p("The squeegees are replaceable without removing the scraper blades from the collector arms."),
            )),
        ),
        (
            Article("FIELD TESTING", (
                q(f"Operate each mechanism in the dry for not less than {dry} {dry_unit} to show freedom from "
                  "binding.", lab("testing_piloting", "dry run test duration", ">=", dry, dry_unit)),
                q(f"Operate each mechanism with water for not less than {wet} hours and record the drive torque.",
                  lab("testing_piloting", "wet test duration", ">=", wet, "hours")),
            )),
            Article("MANUFACTURER'S SERVICES", (
                q(f"Provide a manufacturer's representative on site for not less than {days} days for installation "
                  "inspection, startup, and training on the clarifier mechanisms.",
                  lab("commercial", "clarifier field service", ">=", days, "days")),
            )),
        ),
    ), relevant=reissued)


S464313_ORIGINAL = clarifier(False)
S464313_REISSUED = clarifier(True)


# --- 46 61 23 submerged membrane bioreactor ----------------------------------------------------------------------------

DESIGN_ROWS: tuple[tuple[str, str, str | None, str, str | None], ...] = (
    # parameter, value text, operator, label value, label unit
    ("Design average daily flow", "1.8 MGD", "=", "1.8", "MGD"),
    ("Peak hour flow", "4.5 MGD", "=", "4.5", "MGD"),
    ("Number of membrane trains", "3", "=", "3", None),
    ("Mixed liquor suspended solids in membrane tanks", "8,000 to 10,000 mg/L", "range", "8,000 to 10,000", "mg/L"),
    ("Maximum net flux, design average flow, all trains in service", "14 gfd", "<=", "14", "gfd"),
    ("Maximum net flux, peak hour flow, one train out of service", "30 gfd", "<=", "30", "gfd"),
    ("Maintenance clean frequency, maximum", "1 per week", "<=", "1", "per week"),
    ("Recovery clean interval, minimum", "6 months", ">=", "6", "months"),
    ("Maximum membrane tank side water depth", "14 feet", "<=", "14", "feet"),
    ("Permeate pump turndown, minimum", "5:1", ">=", "5:1", None),
)
TRAP3_PARAMETER = "Permeate pump turndown, minimum"
DESIGN_TABLE = Table(
    ("Parameter", "Value"),
    tuple((name, shown) for name, shown, *_ in DESIGN_ROWS),
    tuple(lab("design_basis", name.lower(), op, value, unit, trap=3 if name == TRAP3_PARAMETER else None)
          for name, _, op, value, unit in DESIGN_ROWS),
)

TRAP1_TEXT = ("The Supplier shall hold the unit prices of replacement membrane modules firm for 10 years after "
              "substantial completion.")
TRAP6_TEXT = "Membrane modules should have an expected service life of not less than 10 years."
TRAP5_TEXT = ("The membrane bioreactor system shall produce effluent total nitrogen not exceeding 3 mg/L as a "
              "monthly average.")
SPARES_OLD = "Furnish spare membrane modules equal to 2 percent of the installed modules."
SPARES_NEW = "Furnish spare membrane modules equal to 4 percent of the installed modules."
REMOTE_SUPPORT = ("The Supplier shall provide remote monitoring and troubleshooting support for 90 days after startup "
                  "at no additional cost to the Owner.")

S466123 = SpecSection("46 61 23", "SUBMERGED MEMBRANE BIOREACTOR EQUIPMENT", (
    (
        Article("SUMMARY", (
            p("Section includes a complete submerged membrane bioreactor system for the new MBR train, including "
              "membrane modules and cassettes, permeate pumps, membrane air scour blowers, chemical cleaning "
              "equipment, instruments, and the membrane system control panel."),
            p("Related sections: Section 01 33 00 Submittal Procedures, Section 01 60 00 Product Requirements, and "
              "Section 46 21 23 Traveling Band Fine Screens."),
            p("The equipment furnished under this Section includes the following items:", kids=tuple(p(x) for x in (
                "Membrane modules and cassettes with their support frames and air diffusers.",
                "Permeate pumps, valves, and permeate headers inside the membrane building.",
                "Membrane air scour blowers with sound enclosures, filters, and silencers.",
                "Chemical cleaning pumps, day tanks, and the cleaning piping to the permeate headers.",
                "Flow meters, pressure transmitters, turbidimeters, and level instruments.",
                "The membrane system control panel, operator interface, and control software.",
                "Special tools, lifting devices, and the cassette lifting frame.",
                "Spare parts and consumables for startup."))),
            p("The following items are furnished by others and are shown on the Drawings:", kids=tuple(p(x) for x in (
                "Membrane tanks, support rails, and the monorail hoist above the tanks.",
                "Process piping beyond the equipment connections.",
                "Electrical power feeders, conduit, and motor control centers.",
                "The plant control system and the plant network.",
                "Bulk chemical storage tanks and the chemical delivery piping.",
                "Anoxic and aerobic zone mixers, diffusers, and the mixed liquor recycle pumps."))),
        )),
        Article("REFERENCES", (
            _refs("ANSI/ASME B16.5 - Pipe Flanges and Flanged Fittings.",
                  "ANSI/HI 9.6.4 - Rotodynamic Pumps for Vibration Measurements and Allowable Values.",
                  "ANSI/HI 14.6 - Rotodynamic Pumps for Hydraulic Performance Acceptance Tests.",
                  "ASME PTC 13 - Wire-to-Air Performance Test Code for Blower Systems.",
                  "ASTM A240/A240M - Chromium and Chromium-Nickel Stainless Steel Plate, Sheet, and Strip.",
                  "ASTM A276/A276M - Stainless Steel Bars and Shapes.",
                  "ASTM A269/A269M - Seamless and Welded Austenitic Stainless Steel Tubing for General Service.",
                  "ASTM A312/A312M - Seamless, Welded, and Heavily Cold Worked Austenitic Stainless Steel Pipes.",
                  "ASTM A380/A380M - Cleaning, Descaling, and Passivation of Stainless Steel Parts and Equipment.",
                  "ASTM D1785 - Poly(Vinyl Chloride) (PVC) Plastic Pipe, Schedules 40, 80, and 120.",
                  "ASTM D2467 - Poly(Vinyl Chloride) (PVC) Plastic Pipe Fittings, Schedule 80.",
                  "ASTM F1554 - Anchor Bolts, Steel, 36, 55, and 105-ksi Yield Strength.",
                  "AWS D1.6/D1.6M - Structural Welding Code - Stainless Steel.",
                  "IEC 61131-3 - Programmable Controllers, Programming Languages.",
                  "IEEE 519 - Harmonic Control in Electric Power Systems.",
                  "ISA 5.1 - Instrumentation Symbols and Identification.",
                  "ISA 18.2 - Management of Alarm Systems for the Process Industries.",
                  "ISO 9001 - Quality Management Systems - Requirements.",
                  "NEMA 250 - Enclosures for Electrical Equipment (1000 Volts Maximum).",
                  "NEMA ICS 1 - Industrial Control and Systems: General Requirements.",
                  "NEMA MG 1 - Motors and Generators.",
                  "NFPA 70 - National Electrical Code.",
                  "NFPA 79 - Electrical Standard for Industrial Machinery.",
                  "NFPA 820 - Fire Protection in Wastewater Treatment and Collection Facilities.",
                  "NSF/ANSI 61 - Drinking Water System Components - Health Effects.",
                  "UL 508A - Industrial Control Panels."),
        )),
        Article("DEFINITIONS", (
            p("Flux: permeate flow per unit of membrane surface area, in gallons per square foot per day (gfd)."),
            p("Net flux: flux averaged over a full production and relaxation or backpulse cycle, after deducting "
              "backpulse volume."),
            p("Transmembrane pressure (TMP): the pressure difference across the membrane between the mixed liquor "
              "side and the permeate side."),
            p("Train: one membrane tank with its cassettes, permeate pump, valves, and instruments."),
            p("Cassette: a frame holding membrane modules, lifted into and out of the tank as one unit."),
            p("Maintenance clean: a short chemical clean done in place with the tank in service."),
            p("Recovery clean: an extended chemical soak done with the tank drained of mixed liquor."),
            p("Permeability: net flux divided by transmembrane pressure, corrected to 20 degrees C."),
            p("Relaxation: a pause in permeate production while air scour continues."),
            p("Backpulse: a short reversal of permeate flow through the membrane to loosen surface deposits."),
            p("Air scour: coarse bubble air released under the cassettes that scours solids from the membrane "
              "surface and mixes the tank."),
            p("Fouling: the buildup of solids or dissolved material on or inside the membrane that raises "
              "transmembrane pressure."),
            p("Integrity test: a test that detects a breach in a membrane module or in a seal."),
            p("Mixed liquor: the mixture of wastewater and biological solids in the aerobic zone."),
            p("Membrane tank: the tank that holds the cassettes and the mixed liquor around them."),
            p("Module: a membrane element, or a group of plates, mounted in a cassette."),
            p("Permeate: the treated water that passes through the membranes."),
            p("Design average flow: the annual average daily flow that the membrane system treats."),
            p("Peak hour flow: the highest flow that the membrane system treats for a sustained period."),
            p("Substantial completion: the date the Owner accepts the project as ready for its intended use."),
            p("Startup: the first operation of the equipment on mixed liquor after the Supplier's representative "
              "has checked the installation."),
        )),
        Article("ABBREVIATIONS", (
            p("The following abbreviations are used in this Section:", kids=tuple(p(x) for x in (
                "AGMA: American Gear Manufacturers Association.", "ANSI: American National Standards Institute.",
                "BOD5: five-day biochemical oxygen demand.", "CIP: clean in place.", "DO: dissolved oxygen.",
                "gfd: gallons per square foot per day.", "HMI: human machine interface.",
                "ISA: International Society of Automation.", "MBR: membrane bioreactor.",
                "MLSS: mixed liquor suspended solids.", "NEMA: National Electrical Manufacturers Association.",
                "NFPA: National Fire Protection Association.", "NTU: nephelometric turbidity units.",
                "PLC: programmable logic controller.", "SCADA: supervisory control and data acquisition.",
                "SRT: solids retention time.", "TKN: total Kjeldahl nitrogen.", "TMP: transmembrane pressure.",
                "TSS: total suspended solids.", "UL: Underwriters Laboratories.",
                "UPS: uninterruptible power supply.", "VFD: variable frequency drive."))),
        )),
        Article("SYSTEM DESCRIPTION", (
            p("The membrane system separates mixed liquor from the aerobic zone into permeate and returned mixed "
              "liquor. Permeate is drawn through the membranes by the permeate pumps and sent to ultraviolet "
              "disinfection."),
            p("Each train operates on a filtration cycle of production followed by relaxation or backpulse. Air "
              "scour runs during production to limit solids buildup on the membrane surface."),
            p("After the upgrade the plant operates two treatment trains in parallel. The existing conventional "
              "train keeps its aeration basins and secondary clarifiers, and the new MBR train takes the place of "
              "one existing aeration basin."),
            p("Screened wastewater from the headworks flows to a splitter box that divides the flow between the "
              "two trains. The operators set the share of the flow that the MBR train receives at the splitter "
              "gates."),
            p("In the MBR train, the wastewater passes through an anoxic zone, an aerobic zone, and the membrane "
              "tanks. Mixed liquor is recycled from the membrane tanks to the anoxic zone to remove nitrogen."),
            p("The membrane tanks are arranged as parallel trains. Each train has its own cassettes, permeate pump, "
              "and instruments, so that one train can be cleaned or serviced while the others remain in "
              "service."),
            p("Cassettes sit on support rails on the floor of each membrane tank and are lifted out with the "
              "monorail hoist above the tanks. The hoist and the monorail are furnished by the general "
              "contractor."),
            p("Permeate is drawn from the cassettes into a permeate header for each train. The permeate pump moves "
              "the permeate through a flow meter and a turbidimeter before it flows to disinfection."),
            p("Air scour is supplied by blowers in the blower room next to the membrane building. The blowers "
              "supply air to the diffusers under the cassettes through stainless steel air headers."),
            p("Cleaning solutions are fed to the permeate header and flow back through the membranes. Sodium "
              "hypochlorite is the maintenance cleaning chemical, and citric acid is the recovery cleaning "
              "chemical."),
            p("The membrane system control panel controls each train and communicates with the plant control "
              "system. Operators start, stop, and adjust the system from the operator interface or from the plant "
              "control system."),
            p("Waste sludge is drawn from the aerobic zone and sent to the existing thickening process. Return "
              "flows from the dewatering process go back to the headworks."),
            p("The membrane system shall be designed to accept sidestream return flows of up to 0.3 MGD from the "
              "solids dewatering process without exceeding the design net flux.",
              lab("design_basis", "sidestream return flow", "<=", "0.3", "MGD"),
              broken=("dewatering", "dewater-<br>ing")),
        )),
        Article("SUBMITTALS", (
            p("Submit shop drawings showing the cassette arrangement, the piping and valve layouts, and the "
              "dimensions of each membrane tank.", lab("submittal")),
            p("Submit the membrane manufacturer's written warranty.", lab("submittal")),
            p("Submit control system software documentation, including control narratives and alarm lists, 45 days "
              "before factory testing.",
              lab("submittal", "control documentation lead time", ">=", "45", "days")),
            p("Submit the certificate of proper installation in accordance with Section 01 33 00.",
              lab("submittal")),
        )),
        Article("QUALITY ASSURANCE", (
            p("Membrane modules shall be manufactured at a facility certified to ISO 9001.", lab("certification")),
            p("Membrane modules shall have NSF/ANSI 61 drinking water system component approval.",
              lab("certification")),
        )),
        Article("DELIVERY, STORAGE, AND HANDLING", (
            p("Membrane modules shall tolerate storage at temperatures between -10 and 45 degrees C without damage.",
              lab("material", "module storage temperature", "range", "-10 to 45", "degrees C")),
        )),
        Article("WARRANTY", (
            p("The membrane system, except the membrane modules, shall be warranted against defects in materials and "
              "workmanship for 24 months after startup.",
              lab("warranty", "membrane system warranty", "=", "24", "months")),
            p("Warranty claims shall be acknowledged by telephone within 8 hours.",
              lab("warranty", "warranty claim acknowledgment time", "<=", "8", "hours")),
        )),
    ),
    (
        Article("MANUFACTURERS", (
            p("The membrane system shall be furnished by the Supplier selected under the Request for Proposals.",
              lab("commercial")),
        )),
        Article("DESIGN CRITERIA", (
            p(TRAP5_TEXT, lab("effluent_limit", "effluent total nitrogen", "<=", "3", "mg/L", trap=5,
                              expected_status="needs_engineer")),
            p("The operating conditions in the table below are the Owner's design basis. They set the flux, cleaning, "
              "and tank limits that the Supplier's process design report is checked against."),
            p("The membrane system shall be designed for the following conditions:"),
            DESIGN_TABLE,
            p("Permeate turbidity shall not exceed 0.2 NTU.",
              lab("effluent_limit", "permeate turbidity", "<=", "0.2", "NTU")),
            p("Permeate total suspended solids shall not exceed 5 mg/L.",
              lab("effluent_limit", "permeate TSS", "<=", "5", "mg/L")),
            p("Permeate BOD5 shall not exceed 2 mg/L as a monthly average.",
              lab("effluent_limit", "permeate BOD5", "<=", "2", "mg/L")),
        )),
        Article("MEMBRANE CASSETTES", (
            p("Each cassette shall be removable from its tank without draining the adjacent trains.",
              lab("performance")),
            p("Cassette frames shall be fabricated from Type 316L stainless steel.",
              lab("material", "cassette frame material")),
            p("Each cassette shall weigh not more than 5,000 pounds when lifted wet from the tank.",
              lab("design_basis", "cassette lifting weight", "<=", "5,000", "pounds")),
        )),
        Article("MEMBRANE MODULES", (
            p("Membranes shall have a nominal pore size not larger than 0.05 micron.",
              lab("material", "nominal pore size", "<=", "0.05", "micron")),
            p("Membrane modules shall carry a full replacement warranty of 5 years from startup.",
              lab("warranty", "membrane module warranty", "=", "5", "years")),
            p("Membranes shall tolerate a cumulative sodium hypochlorite exposure of not less than 1,000,000 ppm "
              "hours over the membrane life.",
              lab("material", "chlorine exposure tolerance", ">=", "1,000,000", "ppm hours")),
            p(TRAP6_TEXT, lab("performance", "expected membrane life", ">=", "10", "years", m=False, trap=6)),
        )),
        Article("PERMEATE PUMPS", (
            p("Permeate pumps shall be driven by variable frequency drives.", lab("performance")),
        )),
        Article("MEMBRANE AIR SCOUR BLOWERS", (
            p("Blower sound pressure level shall not exceed 90 dBA at 3 feet from the enclosure.",
              lab("performance", "blower sound pressure level", "<=", "90", "dBA")),
        )),
        Article("INSTRUMENTS", (
            p("Permeate flow meters shall be magnetic flow meters with an accuracy of plus or minus 1 percent of "
              "rate.", lab("performance", "flow meter accuracy", "<=", "1", "percent")),
        )),
        Article("MEMBRANE SYSTEM CONTROL PANEL", (
            p("The membrane system control panel shall be furnished in a NEMA 4X enclosure with a programmable "
              "logic controller (PLC).", lab("material", "control panel enclosure")),
            p("The PLC and network switches shall run on an uninterruptible power supply for not less than 20 "
              "minutes.", lab("performance", "UPS runtime", ">=", "20", "minutes")),
            p("The operator interface shall store trends for each train for not less than 120 days.",
              lab("performance", "trend storage", ">=", "120", "days")),
        )),
        Article("CONTROL DESCRIPTION", (
            p("Backpulse shall occur every 8 to 12 minutes.",
              lab("performance", "backpulse interval", "range", "8 to 12", "minutes")),
        )),
        Article("FACTORY TESTING", (
            p("Notify the Engineer at least 7 days before the factory test of the control panel.",
              lab("testing_piloting", "factory test notice", ">=", "7", "days")),
        )),
        Article("SPARE PARTS", (
            p(SPARES_OLD),  # replaced by Addendum 1
            p("Furnish one set of special tools for each type of equipment.", lab("commercial")),
        )),
        Article("PROJECT CONDITIONS", (
            p("The membrane tanks are in the new membrane building, which is south of the existing aeration basins "
              "and east of the existing blower building."),
            p("The membrane building has a monorail hoist that is sized for the weight of a wet cassette, and a "
              "floor drain system that returns spilled liquid to the headworks."),
            p("The building ventilation system holds the membrane building between 50 and 90 degrees F."),
            p("The plant is at an elevation of 640 feet above sea level."),
            p("Raw wastewater temperature ranges from 8 degrees C in winter to 24 degrees C in summer."),
            p("The wastewater includes fats, oils, and grease from the food processing industry, which the existing "
              "grease handling process and the new fine screens remove before the membrane tanks."),
            p("The membrane building and the blower room share a wall. Air headers pass through the wall to the "
              "membrane tanks at the locations shown on the Drawings."),
        )),
    ),
    (
        Article("EXAMINATION", (
            p("The general contractor cleans and flushes the membrane tanks before the cassettes are delivered to "
              "the site."),
            p("The Supplier's representative checks the tanks, the support rails, and the air headers when the "
              "cassettes are set."),
        )),
        Article("CLEAN WATER TESTING", (
            p("Perform a clean water test on each train to confirm permeate flow and transmembrane pressure before "
              "mixed liquor is introduced.", lab("testing_piloting")),
        )),
        Article("MEMBRANE INTEGRITY TESTING", (
            p("Perform a pressure decay test on each train before startup.", lab("testing_piloting")),
        )),
        Article("PERFORMANCE TESTING", (
            p("Conduct a performance test of 30 days after the biological process has reached steady state.",
              lab("testing_piloting", "performance test duration", "=", "30", "days")),
        )),
        Article("STARTUP", (
            p("Operate the system in manual mode for not less than 72 hours before switching to automatic control.",
              lab("testing_piloting", "manual operation before automatic control", ">=", "72", "hours")),
        )),
        Article("MANUFACTURER'S FIELD SERVICES", (
            p("A manufacturer's process engineer shall be on site during the performance test.",
              lab("commercial")),
        )),
        Article("TRAINING", (
            p("Provide not less than 12 hours of operator training on the membrane system in two sessions.",
              lab("commercial", "membrane operator training", ">=", "12", "hours")),
        )),
        Article("CLOSEOUT", (
            p("Submit a final operation and maintenance manual update within 30 days after the performance test.",
              lab("submittal", "O&M manual update submittal time", "<=", "30", "days")),
            p("The Supplier shall provide the following at closeout:", kids=(
                p("Final as-built drawings of the membrane system.", lab("submittal")),
                p("A summary of operator training sessions with attendance records.", lab("submittal")),
                p(TRAP1_TEXT, lab("commercial", "replacement module price hold", ">=", "10", "years", trap=1)),
            )),
        )),
    ),
), relevant=True)


# --- Irrelevant sections (realistic filler, no labels) -----------------------------------------------------------------

MISC_CONCRETE = FillerSpec(
    "03 30 53", "MISCELLANEOUS CAST-IN-PLACE CONCRETE",
    ("ACI 301 - Specifications for Concrete Construction.",
     "ACI 304R - Guide for Measuring, Mixing, Transporting, and Placing Concrete.",
     "ACI 305R - Guide to Hot Weather Concreting.",
     "ACI 306R - Guide to Cold Weather Concreting.",
     "ACI 318 - Building Code Requirements for Structural Concrete.",
     "ASTM A615/A615M - Deformed and Plain Carbon-Steel Bars for Concrete Reinforcement.",
     "ASTM C31/C31M - Making and Curing Concrete Test Specimens in the Field.",
     "ASTM C39/C39M - Compressive Strength of Cylindrical Concrete Specimens.",
     "ASTM C94/C94M - Ready-Mixed Concrete.",
     "ASTM C143/C143M - Slump of Hydraulic-Cement Concrete.",
     "ASTM C171 - Sheet Materials for Curing Concrete.",
     "ASTM C309 - Liquid Membrane-Forming Compounds for Curing Concrete.",
     "ASTM C494/C494M - Chemical Admixtures for Concrete."),
    (("SUMMARY", ("Section includes miscellaneous cast-in-place concrete for {item}, including formwork, "
                  "reinforcement, and curing.",)),
     ("SUBMITTALS", ("Submit concrete mix designs for {item} at least {n:10-21} days before the first placement.",
                     "Submit reinforcing steel shop drawings for {item}.",
                     "Submit product data for admixtures, curing compounds, and joint sealants.")),
     ("QUALITY ASSURANCE", ("Concrete testing shall be performed by an independent laboratory.",
                            "Hold a preplacement meeting at least {n:3-7} days before the first placement of "
                            "concrete for {item}."))),
    (("MATERIALS", ("Portland cement shall conform to ASTM C150, Type II.",
                    "Reinforcing bars shall be deformed bars conforming to ASTM A615, Grade 60.",
                    "Curing compound shall be a liquid membrane-forming compound conforming to ASTM C309.")),
     ("CONCRETE MIXES", ("Concrete for {item} shall have a compressive strength of {c:4,000|4,500} psi at 28 days.",
                         "The water-cementitious materials ratio shall not exceed 0.{n:42-45}.",
                         "Slump shall be {n:3-5} inches, plus or minus 1 inch.")),
     ("FORM MATERIALS", ("Form ties for {item} shall be the snap-off type.",
                         "Chamfer exposed corners of {item} three-quarter inch."))),
    (("FORMWORK", ("Formwork for {item} shall be designed to support the weight of wet concrete and construction "
                   "loads.",
                   "Do not remove forms from {item} until the concrete has reached {n:60-75} percent of its "
                   "specified strength.")),
     ("REINFORCEMENT", ("Place reinforcement for {item} with concrete cover of {n:2-3} inches unless otherwise "
                        "indicated.",
                        "Lap splices in {item} shall be Class B unless otherwise indicated.")),
     ("PLACING", ("Notify the Engineer at least {n:24-48} hours before placing concrete for {item}.",
                  "Do not drop concrete freely more than {n:4-5} feet when placing {item}.",
                  "Consolidate concrete for {item} with internal vibrators.")),
     ("FINISHING", ("Finish exposed surfaces of {item} with a light broom finish.",
                    "Finish the top surface of {item} to a flatness of plus or minus one quarter inch in 10 feet.")),
     ("CURING", ("Keep {item} continuously moist for at least {n:7-10} days after placement.",
                 "Protect {item} from freezing for at least {n:5-7} days after placement.")),
     ("FIELD QUALITY CONTROL", ("Make one set of {n:4-5} cylinders for each {n:25-50} cubic yards of concrete "
                                "placed for {item}.",
                                "Concrete for {item} that fails to meet the specified strength shall be cored and "
                                "evaluated at the Contractor's expense."))),
    ("equipment pads", "housekeeping pads", "thrust blocks", "curbs", "sidewalks", "light pole bases",
     "manhole bases", "bollard footings", "ramps", "transformer pads", "generator pads", "pipe supports",
     "chemical containment curbs", "stair landings", "valve vault slabs", "duct bank encasements",
     "signage bases", "fence post footings", "scale foundations", "dumpster pads", "flume supports",
     "sample station pads", "meter pad foundations", "mixer support pedestals"),
    pages=7,
)

METAL_FAB = FillerSpec(
    "05 50 00", "METAL FABRICATIONS",
    ("AA ADM 1 - Aluminum Design Manual.",
     "AISC 360 - Specification for Structural Steel Buildings.",
     "ASTM A36/A36M - Carbon Structural Steel.",
     "ASTM A123/A123M - Zinc (Hot-Dip Galvanized) Coatings on Iron and Steel Products.",
     "ASTM A153/A153M - Zinc Coating (Hot-Dip) on Iron and Steel Hardware.",
     "ASTM A240/A240M - Chromium and Chromium-Nickel Stainless Steel Plate, Sheet, and Strip.",
     "ASTM B221 - Aluminum and Aluminum-Alloy Extruded Bars, Rods, Wire, Profiles, and Tubes.",
     "AWS D1.1 - Structural Welding Code - Steel.",
     "AWS D1.2 - Structural Welding Code - Aluminum.",
     "NAAMM MBG 531 - Metal Bar Grating Manual."),
    (("SUMMARY", ("Section includes miscellaneous metal fabrications for {item}, including framing, supports, and "
                  "anchorage.",)),
     ("DESIGN REQUIREMENTS", ("Design fabrications for {item} to support a live load of not less than {n:60-100} "
                              "pounds per square foot.",
                              "Limit deflection of fabrications for {item} to 1/{n:240-360} of the span.")),
     ("SUBMITTALS", ("Submit shop drawings for fabrications for {item}, showing materials, sizes, welds, and "
                     "anchors.",
                     "Submit structural calculations for {item} sealed by a professional engineer.",
                     "Submit welder certificates for welding performed on {item}.")),
     ("QUALITY ASSURANCE", ("Fabricators shall have at least {n:5-10} years of experience with similar work.",
                            "Welding of fabrications for {item} shall be performed by welders qualified under "
                            "AWS D1.1."))),
    (("MATERIALS", ("Structural steel shapes shall conform to ASTM A36.",
                    "Aluminum extrusions shall conform to ASTM B221, alloy 6061-T6.",
                    "Stainless steel fabrications shall be Type 316 unless otherwise indicated.")),
     ("FASTENERS", ("Anchor bolts for {item} shall be Type 316 stainless steel.",
                    "Bolts, nuts, and washers for {item} shall be of the same material as the fabrication.")),
     ("GRATING", ("Grating for {item} shall be fiberglass with a slip resistant surface.",
                  "Grating clips for {item} shall be Type 316 stainless steel.")),
     ("FABRICATION", ("Fabricate {item} true to line and level with accurate angles and surfaces.",
                      "Grind welds on exposed surfaces of {item} smooth.",
                      "Galvanize steel fabrications for {item} after fabrication in accordance with ASTM A123.",
                      "Drill holes for anchors in {item} at the shop where possible."))),
    (("INSTALLATION", ("Install {item} plumb and level, with the anchors set in epoxy grout.",
                       "Isolate dissimilar metals at {item} with a bituminous coating or a gasket.",
                       "Cut and fit fabrications for {item} to the building structure without distortion.")),
     ("HANDRAILS", ("Install handrails at {item} with posts spaced not more than {n:4-6} feet apart.",
                    "Handrail height at {item} shall be {n:42-42} inches above the walking surface.")),
     ("FIELD QUALITY CONTROL", ("Verify the anchors for {item} by pull testing at {n:5-10} percent of the "
                                "locations.",
                                "Repair damage to galvanizing on {item} with a zinc-rich paint."))),
    ("access platforms", "ladders", "stair stringers", "equipment supports", "trench covers", "hatches and frames",
     "handrails", "toe plates", "grating at the screening channels", "monorail beams", "weir plates", "baffles",
     "launders", "pipe supports", "bollards", "equipment davits", "sump covers", "louvers", "stair treads",
     "floor plates", "angle frames", "embedded frames", "lintels", "pipe sleeves"),
    pages=7,
)

COATINGS = FillerSpec(
    "09 96 00", "HIGH-PERFORMANCE COATINGS",
    ("ASTM D3359 - Measuring Adhesion by Tape Test.",
     "ASTM D4541 - Pull-Off Strength of Coatings Using Portable Adhesion Testers.",
     "ASTM D4414 - Measurement of Wet Film Thickness of Organic Coatings by Notch Gages.",
     "ASTM D7091 - Nondestructive Measurement of Dry Film Thickness of Nonmagnetic Coatings.",
     "NACE SP0188 - Discontinuity (Holiday) Testing of New Protective Coatings on Conductive Substrates.",
     "SSPC-PA 2 - Procedure for Determining Conformance to Dry Coating Thickness Requirements.",
     "SSPC-SP 1 - Solvent Cleaning.",
     "SSPC-SP 6 - Commercial Blast Cleaning.",
     "SSPC-SP 10 - Near-White Blast Cleaning."),
    (("SUMMARY", ("Section includes surface preparation and high-performance coatings for {item}.",)),
     ("SUBMITTALS", ("Submit manufacturer's product data and application instructions for the coatings used on "
                     "{item}.",
                     "Submit color charts for {item} at least {n:14-28} days before coating begins.",
                     "Submit certificates that the applicator's personnel have been trained by the coating "
                     "manufacturer.")),
     ("QUALITY ASSURANCE", ("The applicator shall have at least {n:5-10} years of experience applying the specified "
                            "coating systems.",
                            "Apply a mock-up of the coating system on {item} for approval before coating "
                            "begins.")),
     ("WARRANTY", ("The coating system for {item} shall be warranted against peeling, blistering, and "
                   "delamination for {n:1-2} years after final acceptance.",))),
    (("EPOXY COATINGS", ("Epoxy coating for {item} shall be a two-component, polyamide cured epoxy, "
                         "{n:6-8} mils dry film thickness per coat.",
                         "Epoxy coatings shall have a volume solids content of not less than {n:60-75} percent.")),
     ("URETHANE FINISH COATS", ("Urethane finish coat for {item} shall be an aliphatic polyurethane, "
                                "{n:2-4} mils dry film thickness.",)),
     ("PRIMERS", ("Primer for {item} shall be compatible with the intermediate and finish coats.",
                  "Zinc-rich primer shall contain not less than {n:80-85} percent zinc by weight in the dry "
                  "film.")),
     ("THINNERS AND CLEANERS", ("Use only the thinners recommended by the coating manufacturer for {item}.",))),
    (("SURFACE PREPARATION", ("Prepare surfaces of {item} in accordance with SSPC-SP 10 unless otherwise "
                              "indicated.",
                              "Remove oil and grease from {item} by solvent cleaning before blasting.",
                              "Blast profile for {item} shall be {n:2-3} mils measured with replica tape.")),
     ("APPLICATION", ("Apply coatings to {item} when the surface temperature is at least {n:5-10} degrees F above "
                      "the dew point.",
                      "Do not apply coatings to {item} when the relative humidity exceeds {n:80-85} percent.",
                      "Apply a stripe coat to welds, edges, and corners of {item} before each full coat.")),
     ("FIELD QUALITY CONTROL", ("Measure dry film thickness of each coat on {item} in accordance with SSPC-PA 2.",
                                "Holiday test coated surfaces of {item} at {n:100-125} volts per mil.",
                                "Repair coating defects on {item} in accordance with the manufacturer's "
                                "instructions.")),
     ("CLEANUP", ("Remove spent abrasive and coating debris from the area of {item} daily.",))),
    ("ductile iron piping", "carbon steel supports", "handrails", "interior concrete walls", "tank interior surfaces",
     "exposed process piping", "equipment bases", "structural steel", "aluminum hatches", "access platforms",
     "chemical tank exteriors", "pump casings", "valve bodies", "grating supports", "ladders",
     "exterior doors and frames", "louvers", "pipe hangers", "galvanized conduit", "wall sleeves",
     "stair stringers", "concrete floors", "curb tops", "anchor bolts"),
    pages=7,
)

ELECTRICAL = FillerSpec(
    "26 05 00", "COMMON WORK RESULTS FOR ELECTRICAL",
    ("ANSI C80.1 - Electrical Rigid Steel Conduit.",
     "IEEE 80 - Guide for Safety in AC Substation Grounding.",
     "NECA 1 - Standard for Good Workmanship in Electrical Construction.",
     "NEMA 250 - Enclosures for Electrical Equipment (1000 Volts Maximum).",
     "NFPA 70 - National Electrical Code.",
     "NFPA 70E - Standard for Electrical Safety in the Workplace.",
     "UL 6 - Electrical Rigid Metal Conduit - Steel.",
     "UL 651 - Schedule 40, 80, Type EB and A Rigid PVC Conduit and Fittings.",
     "UL 797 - Electrical Metallic Tubing - Steel."),
    (("SUMMARY", ("Section includes basic electrical materials and methods for {item}.",)),
     ("SUBMITTALS", ("Submit product data for raceways, boxes, conductors, and supports used at {item}.",
                     "Submit test reports within {n:7-14} days after testing of circuits serving {item}.",
                     "Submit record drawings showing the routing of conduits serving {item}.")),
     ("QUALITY ASSURANCE", ("Electrical work shall be performed by licensed electricians.",
                            "Materials shall be listed and labeled by a nationally recognized testing "
                            "laboratory.")),
     ("COORDINATION", ("Coordinate the location of conduits and boxes at {item} with structural and mechanical "
                       "work.",))),
    (("RACEWAYS", ("Rigid galvanized steel conduit shall conform to ANSI C80.1.",
                   "Rigid nonmetallic conduit for {item} shall be Schedule 80 PVC.",
                   "Liquidtight flexible conduit for {item} shall not exceed {n:3-6} feet in length.")),
     ("CONDUCTORS", ("Power conductors shall be copper, Type XHHW-2, rated 600 volts.",
                     "Conductors for {item} shall be not smaller than No. {n:10-12} AWG.")),
     ("BOXES AND ENCLOSURES", ("Enclosures at {item} in wet locations shall be NEMA 4X stainless steel.",
                               "Boxes at {item} shall be cast metal with threaded hubs.")),
     ("GROUNDING MATERIALS", ("Ground rods shall be copper-clad steel, {n:8-10} feet long.",
                              "Grounding conductors shall be bare stranded copper."))),
    (("GENERAL INSTALLATION", ("Install electrical equipment at {item} in accordance with NECA 1.",
                               "Provide working clearances at {item} as required by NFPA 70.",
                               "Seal openings in walls at {item} where conduits pass through.")),
     ("RACEWAY INSTALLATION", ("Install conduit at {item} exposed unless otherwise indicated.",
                               "Bury underground conduits for {item} not less than {n:24-36} inches below finished "
                               "grade.",
                               "Provide expansion fittings where conduits at {item} cross structural expansion "
                               "joints.")),
     ("CONDUCTOR INSTALLATION", ("Pull conductors for {item} with a lubricant approved by the cable manufacturer.",
                                 "Leave at least {n:6-12} inches of slack at each box at {item}.")),
     ("GROUNDING", ("Bond metallic raceways and enclosures at {item} to the grounding system.",
                    "The resistance of the grounding electrode system for {item} shall not exceed {n:5-10} ohms.")),
     ("FIELD TESTING", ("Test the insulation resistance of feeders serving {item} at 1,000 volts DC for one "
                        "minute.",
                        "Insulation resistance of circuits serving {item} shall be not less than {n:50-100} "
                        "megohms.",
                        "Correct deficiencies found during testing of {item} and retest at no cost to the Owner."))),
    ("the screening building", "the blower building", "the operations building", "the chemical building",
     "the solids handling building", "the influent pump station", "the effluent pump station",
     "the generator building", "outdoor process areas", "the laboratory", "yard lighting circuits",
     "the plant water system", "the odor control area", "site security systems", "the process building",
     "the secondary clarifiers", "the aeration basins", "the digester building", "the disinfection building",
     "the maintenance shop", "the septage receiving station", "the gatehouse", "the fire alarm system",
     "the data and communication system", "the outfall structure", "the motor control center room"),
    pages=7,
)

EXCAVATION = FillerSpec(
    "31 23 00", "EXCAVATION AND FILL",
    ("ASTM C136/C136M - Sieve Analysis of Fine and Coarse Aggregates.",
     "ASTM D698 - Laboratory Compaction Characteristics of Soil Using Standard Effort.",
     "ASTM D1557 - Laboratory Compaction Characteristics of Soil Using Modified Effort.",
     "ASTM D2487 - Classification of Soils for Engineering Purposes.",
     "ASTM D6938 - In-Place Density and Water Content of Soil by Nuclear Methods.",
     "OSHA 29 CFR 1926 Subpart P - Excavations."),
    (("SUMMARY", ("Section includes excavation, dewatering, backfill, and compaction for {item}.",)),
     ("SUBMITTALS", ("Submit gradation test results for each fill material used at {item}.",
                     "Submit a dewatering plan for {item}.",
                     "Submit an excavation support plan for {item} at least {n:10-21} days before excavation.")),
     ("PROJECT CONDITIONS", ("Protect existing utilities near {item} from damage.",
                             "Groundwater was encountered at depths of {n:5-11} feet below grade in the borings "
                             "near {item}."))),
    (("SOIL MATERIALS", ("Structural fill for {item} shall be well graded sand and gravel with not more than "
                         "{n:8-12} percent passing the No. 200 sieve.",
                         "Common fill shall be free of organic matter, debris, and stones larger than {n:3-5} "
                         "inches.")),
     ("GEOTEXTILES", ("Separation geotextile beneath {item} shall be nonwoven polypropylene.",)),
     ("MARKING MATERIALS", ("Warning tape over utilities at {item} shall be polyethylene, {n:4-6} inches wide.",))),
    (("SITE PREPARATION", ("Clear and grub the area of {item} before excavation.",
                           "Strip topsoil from the area of {item} and stockpile it for reuse.")),
     ("DEWATERING", ("Lower groundwater at {item} at least {n:2-3} feet below the bottom of excavation.",
                     "Discharge water from dewatering at {item} through a sediment control device.")),
     ("EXCAVATION", ("Excavate {item} to the lines and grades indicated on the Drawings.",
                     "Do not excavate below {item} more than {n:2-4} inches below the indicated grade.")),
     ("BACKFILL", ("Place backfill around {item} in lifts not exceeding {n:8-12} inches loose thickness.",
                   "Do not place backfill against walls of {item} until the concrete has reached its specified "
                   "strength.")),
     ("COMPACTION", ("Compact structural fill under {item} to {n:95-98} percent of maximum dry density per ASTM "
                     "D1557.",
                     "Moisture content of fill at {item} shall be within 2 percent of optimum during "
                     "compaction.")),
     ("FIELD QUALITY CONTROL", ("Perform one density test for each {c:2,000|2,500|5,000} square feet of each lift at "
                                "{item}.",
                                "Retest areas at {item} that fail compaction after rework."))),
    ("the screening building", "the process building", "the blower building", "the secondary clarifiers",
     "the aeration basins", "the membrane building", "the operations building", "the chemical building",
     "yard piping", "the outfall pipe", "site roads", "the electrical duct banks", "the stormwater basin",
     "the influent sewer", "the digester building", "the disinfection building", "the maintenance shop",
     "the septage receiving station", "the sludge storage tanks", "the gatehouse", "the parking area",
     "the generator pad", "the chemical containment area", "the plant drain pump station", "the force main",
     "the water main", "the fence line"),
    pages=6,
)

PIPING = FillerSpec(
    "40 05 13", "PROCESS PIPING AND VALVES",
    ("ANSI/AWWA C104/A21.4 - Cement-Mortar Lining for Ductile-Iron Pipe and Fittings.",
     "ANSI/AWWA C110/A21.10 - Ductile-Iron and Gray-Iron Fittings.",
     "ANSI/AWWA C151/A21.51 - Ductile-Iron Pipe, Centrifugally Cast.",
     "ANSI/AWWA C509 - Resilient-Seated Gate Valves.",
     "ANSI/AWWA C504 - Rubber-Seated Butterfly Valves.",
     "ASTM A53/A53M - Pipe, Steel, Black and Hot-Dipped, Zinc-Coated, Welded and Seamless.",
     "ASTM D1785 - Poly(Vinyl Chloride) (PVC) Plastic Pipe, Schedules 40, 80, and 120.",
     "ASME B16.5 - Pipe Flanges and Flanged Fittings.",
     "MSS SP-58 - Pipe Hangers and Supports."),
    (("SUMMARY", ("Section includes process piping, fittings, valves, and supports for {item}.",)),
     ("SUBMITTALS", ("Submit shop drawings of the piping layout for {item}.",
                     "Submit product data for valves serving {item}.",
                     "Submit pressure test reports for {item} within {n:5-10} days after testing.")),
     ("QUALITY ASSURANCE", ("Welding of steel piping shall be performed by welders certified in accordance with AWS "
                            "D1.1.",
                            "Valves for {item} shall be furnished by a manufacturer with at least {n:5-10} years of "
                            "experience in water and wastewater service.")),
     ("DELIVERY AND STORAGE", ("Store pipe for {item} on timbers and cover it to protect it from sunlight.",))),
    (("DUCTILE IRON PIPE", ("Ductile iron pipe for {item} shall be pressure Class {n:250-350} with cement mortar "
                            "lining.",
                            "Flanged joints shall use full face gaskets and Type 316 stainless steel bolting.")),
     ("PVC PIPE", ("PVC pipe for {item} shall be Schedule 80 with solvent weld joints.",)),
     ("PLUG VALVES", ("Plug valves for {item} shall be eccentric type with resilient seats.",
                      "Plug valve operators shall be sized for a differential pressure of {n:60-100} psi.")),
     ("BUTTERFLY VALVES", ("Butterfly valves for {item} shall have cast iron bodies and rubber seats.",
                           "Valve discs shall be Type 316 stainless steel.")),
     ("CHECK VALVES", ("Swing check valves for {item} shall have an outside lever and weight.",
                       "Pilot-operated check valves shall be used only where indicated on the Drawings.")),
     ("PIPE SUPPORTS", ("Pipe supports for {item} shall be Type 316 stainless steel.",))),
    (("INSTALLATION", ("Install piping for {item} in accordance with the manufacturer's instructions.",
                       "Support piping for {item} at intervals not exceeding {n:6-10} feet.",
                       "Provide flexible couplings at each connection to equipment serving {item}.")),
     ("VALVE INSTALLATION", ("Install valves for {item} with the stem horizontal or above horizontal.",
                             "Provide an access opening where a valve serving {item} is installed above a ceiling.")),
     ("PRESSURE TESTING", ("Test piping for {item} at {n:100-150} percent of the working pressure for {n:2-4} "
                           "hours.",
                           "Repair leaks in piping for {item} and retest until no leakage is observed.")),
     ("FLUSHING AND DISINFECTION", ("Flush piping for {item} until the discharge runs clear.",
                                    "Dispose of flushing water in accordance with the permit.")),
     ("IDENTIFICATION", ("Label piping for {item} with the service name and flow direction at intervals not "
                         "exceeding {n:15-25} feet.",))),
    ("the screening building", "the blower building", "the membrane building", "the chemical building",
     "the secondary clarifiers", "the aeration basins", "the sludge pump station", "the plant water system",
     "the scum pump station", "the return sludge pump station", "the digester building", "the dewatering building",
     "the effluent pump station", "yard piping", "the odor control area", "the laboratory", "the polymer system",
     "the drain pump station", "the utility water system", "the filtrate return line"),
    pages=7,
)

PUMPS = FillerSpec(
    "46 71 33", "SUBMERSIBLE NON-CLOG PUMPS",
    ("ANSI/HI 1.3 - Rotodynamic Centrifugal Pumps for Design and Application.",
     "ANSI/HI 11.6 - Submersible Pumps Tests.",
     "ANSI/AGMA 2001 - Fundamental Rating Factors and Calculation Methods for Involute Spur and Helical Gear "
     "Teeth.",
     "IEEE 841 - Severe Duty Totally Enclosed Fan-Cooled Squirrel Cage Induction Motors.",
     "NEMA MG 1 - Motors and Generators.",
     "NFPA 70 - National Electrical Code.",
     "UL 674 - Electric Motors and Generators for Use in Hazardous Locations."),
    (("SUMMARY", ("Section includes submersible non-clog pumps, guide rails, and discharge connections for "
                  "{item}.",)),
     ("SUBMITTALS", ("Submit pump performance curves for {item} showing the design point and the operating range.",
                     "Submit motor data and cable data for {item}.",
                     "Submit factory test reports for pumps serving {item} before shipment.")),
     ("QUALITY ASSURANCE", ("Pumps for {item} shall be the product of a manufacturer with at least {n:10-20} years "
                            "of experience in wastewater pumps.",
                            "Pump motors shall be rated for Class I, Division 1 service.")),
     ("WARRANTY", ("The pumps for {item} shall be warranted for {n:1-5} years against defects in materials and "
                   "workmanship.",))),
    (("PUMP CONSTRUCTION", ("Pump casings and impellers for {item} shall be cast iron, ASTM A48, Class 35B.",
                            "Impellers shall pass spherical solids of not less than {n:3-3} inches.",
                            "Shafts shall be Type 420 stainless steel.")),
     ("MOTORS", ("Motors for {item} shall be 460 volts, 3 phase, 60 Hz, premium efficiency.",
                 "Motor insulation shall be Class H with moisture and temperature sensors in the stator.")),
     ("SEALS AND BEARINGS", ("Pumps for {item} shall have tandem mechanical seals with an oil chamber between the "
                             "seals.",
                             "Bearings shall have a minimum B10 life of {n:50-60},000 hours.")),
     ("GUIDE RAILS AND ACCESSORIES", ("Guide rails and fasteners for {item} shall be Type 316 stainless steel.",
                                      "Lifting chains shall be Type 316 stainless steel with a safe working load "
                                      "of at least {n:2-3} times the pump weight."))),
    (("INSTALLATION", ("Install pumps for {item} in accordance with the manufacturer's instructions.",
                       "Level the discharge base elbows for {item} to within one eighth inch.")),
     ("FIELD TESTING", ("Test each pump for {item} for vibration, noise, and amperage at the design point.",
                        "Operate each pump for {item} continuously for at least {n:2-4} hours during the field "
                        "test.")),
     ("MANUFACTURER'S SERVICES", ("Provide a manufacturer's representative for {n:1-2} days to inspect the "
                                  "installation of pumps for {item}.",
                                  "Provide {n:2-4} hours of operator training on the pumps for {item}."))),
    ("the influent pump station", "the effluent pump station", "the return sludge pump station",
     "the scum pump station", "the plant drain pump station", "the septage receiving station",
     "the digester feed pumps", "the dewatering feed pumps", "the filtrate return pumps", "the sump pumps",
     "the stormwater pump station", "the equalization basin pumps", "the chemical area sumps",
     "the secondary effluent pumps", "the thickened sludge pumps", "the utility water pumps"),
    pages=6,
)

FILLERS = (MISC_CONCRETE, METAL_FAB, COATINGS, ELECTRICAL, EXCAVATION, PIPING, PUMPS)
DIVISIONS = {"00": "PROCUREMENT AND CONTRACTING REQUIREMENTS", "01": "GENERAL REQUIREMENTS", "03": "CONCRETE",
             "05": "METALS", "09": "FINISHES", "26": "ELECTRICAL", "31": "EARTHWORK", "40": "PROCESS INTEGRATION",
             "46": "WATER AND WASTEWATER EQUIPMENT"}


def spec_book() -> list[SpecSection | FrontSection]:
    """The Technical Specifications in book order, divisions in numeric order, one section per slot."""
    rng = random.Random(2718)
    concrete, metals, coatings, electrical, excavation, piping, pumps = (filler_section(f, rng) for f in FILLERS)
    return [S002113, S007300, S013300, S016000, concrete, metals, coatings, electrical, excavation, piping,
            S462123, S464313_ORIGINAL, S466123, pumps]


# --- Permit ----------------------------------------------------------------------------------------------------------

PERMIT_TITLE = "NPDES DISCHARGE PERMIT EXCERPT"
SUMMER = "May 1 - October 31"
WINTER = "November 1 - April 30"
PERMIT_TABLE = Table(
    ("Parameter", "Season", "Monthly Average", "Weekly Average", "Daily Maximum", "Units"),
    (("Total Nitrogen (as N)", SUMMER, "3.0", "--", "--", "mg/L"),
     ("Total Nitrogen (as N)", WINTER, "8.0", "--", "--", "mg/L"),
     ("Ammonia Nitrogen (as N)", SUMMER, "1.0", "1.5", "--", "mg/L"),
     ("Ammonia Nitrogen (as N)", WINTER, "2.5", "4.0", "--", "mg/L"),
     ("Carbonaceous BOD (CBOD5)", "Year round", "10", "15", "--", "mg/L"),
     ("Total Suspended Solids (TSS)", "Year round", "12", "18", "--", "mg/L"),
     ("Total Phosphorus", "Year round", "1.0", "--", "2.0", "mg/L")),
)
PERMIT_LIMITS = [
    SeasonalLimit(0, "monthly_avg", 3.0, SUMMER),
    SeasonalLimit(1, "monthly_avg", 8.0, WINTER),
    SeasonalLimit(2, "monthly_avg", 1.0, SUMMER), SeasonalLimit(2, "weekly_avg", 1.5, SUMMER),
    SeasonalLimit(3, "monthly_avg", 2.5, WINTER), SeasonalLimit(3, "weekly_avg", 4.0, WINTER),
    SeasonalLimit(4, "monthly_avg", 10.0, None), SeasonalLimit(4, "weekly_avg", 15.0, None),
    SeasonalLimit(5, "monthly_avg", 12.0, None), SeasonalLimit(5, "weekly_avg", 18.0, None),
    SeasonalLimit(6, "monthly_avg", 1.0, None), SeasonalLimit(6, "daily_max", 2.0, None),
]
SCANNED_PERMIT_PAGE = 4  # the monitoring page is an image of itself, like a scanned page; no label sits on it

PERMIT_PAGES: list[list[str | Table]] = [
    [PERMIT_TITLE,
     "Cedar State Department of Environmental Quality",
     "Permit No. CF0023871",
     "Permittee: City of Cedar Falls, Cedar Falls Water Pollution Control Facility",
     "Receiving water: Tamarack Creek",
     "Effective date: October 1, 2025. Expiration date: September 30, 2030.",
     FICTION,
     "In compliance with the state water pollution control law and the federal Clean Water Act, the City of Cedar "
     "Falls is authorized to discharge treated wastewater from the Cedar Falls Water Pollution Control Facility to "
     "Tamarack Creek in accordance with the effluent limitations, monitoring requirements, and other conditions of "
     "this permit.",
     "This excerpt reproduces Part I of the permit. Part II, standard conditions, is incorporated by reference and "
     "is not reproduced here.",
     "The design flow of the facility is 3.0 million gallons per day as an annual average."],
    ["PART I. EFFLUENT LIMITATIONS AND MONITORING REQUIREMENTS",
     "A. During the period beginning on the effective date and lasting through expiration, the permittee is "
     "authorized to discharge treated wastewater from outfall 001. The discharge is limited and monitored by the "
     "permittee as specified in Table 1.",
     "B. Samples taken in compliance with the monitoring requirements are taken at the effluent sampling station "
     "after final treatment and before discharge to the receiving water.",
     "C. The discharge does not cause a visible sheen, foam, or floating solids in Tamarack Creek.",
     "D. The seasonal total nitrogen limits take effect on July 1, 2030, at the end of the compliance schedule in "
     "Part I.G. Until then the permittee reports total nitrogen monthly without a numeric limit.",
     "E. Monthly average limits apply to the arithmetic mean of all samples collected in a calendar month. Weekly "
     "average limits apply to the arithmetic mean of all samples collected in a calendar week."],
    ["Table 1. Effluent Limitations, Outfall 001", PERMIT_TABLE,
     "Seasonal limits apply from May 1 through October 31 for the summer season and from November 1 through April 30 "
     "for the winter season. Report the results of all analyses on the monthly discharge monitoring report."],
    ["F. MONITORING REQUIREMENTS",
     "1. Flow is measured continuously and recorded daily.",
     "2. Total nitrogen, ammonia nitrogen, CBOD5, and TSS are sampled three times per week as 24 hour flow "
     "proportional composite samples.",
     "3. Total phosphorus is sampled weekly as a 24 hour composite sample.",
     "4. pH and total residual chlorine are measured daily by grab sample."],
    ["G. COMPLIANCE SCHEDULE FOR TOTAL NITROGEN",
     "1. Complete the facility plan for nitrogen removal by October 1, 2026.",
     "2. Begin construction of the nitrogen removal upgrade by October 1, 2028.",
     "3. Achieve compliance with the seasonal total nitrogen limits by July 1, 2030.",
     "4. Submit a written progress report every six months until compliance is achieved."],
]


# --- Addenda ---------------------------------------------------------------------------------------------------------

ADDENDUM_HEAD = (
    "City of Cedar Falls, Cedar Falls WPCF Phase 3 Improvements: Fine Screen, Clarifier Mechanism, and Membrane "
    "Bioreactor Equipment Preselection"
)
ADDENDUM_INTRO = ("This Addendum modifies the Request for Proposals and the Technical Specifications as described "
                  "below. All other terms remain unchanged.")
_FIRMS = ("Fenwick Process", "Larkspur Controls", "Brindle Mechanical", "Westmere Filtration", "Corbin Hill Equipment",
          "Harrowgate Environmental", "Ironwood Contractors", "Kettleridge Electric", "Pennick Instruments",
          "Quarry Lane Builders", "Redfern Fabrication", "Stillwater Pump")
_ROLES = ("Equipment representative", "Applications engineer", "Estimator", "Project manager", "Sales engineer")
ATTENDEES = Table(
    ("Firm", "Attendee role", "Contact"),
    tuple((f"{firm} {kind}", _ROLES[(i + j) % len(_ROLES)], f"bids{i}{j}@{firm.split()[0].lower()}.example.com")
          for i, firm in enumerate(_FIRMS) for j, kind in enumerate(("Inc.", "LLC", "Co."))),
)

ADDENDUM_1 = AddendumDoc(
    doc_id="addendum_1", addendum_id="Addendum 1", short="Addendum No. 1",
    items=(
        "ADDENDUM NO. 1",
        ADDENDUM_HEAD,
        "RFP No. CF-2026-14. Date of Addendum: November 16, 2026.",
        FICTION,
        ADDENDUM_INTRO,
        "CHANGES TO THE REQUEST FOR PROPOSALS",
        p("Revise the proposal due date to December 10, 2026 at 2:00 PM."),
        "CHANGES TO THE TECHNICAL SPECIFICATIONS",
        p("Section 46 61 23 Submerged Membrane Bioreactor Equipment: Delete paragraph 2.11.A and replace with the "
          "following: " + SPARES_NEW),
        "QUESTIONS AND ANSWERS",
        "Question: Will the Owner accept a pilot test conducted at another operating plant instead of at the Cedar "
        "Falls WPCF?",
        "Answer: No. The pilot test will be conducted on the Cedar Falls WPCF mixed liquor, and the Owner will not "
        "waive pilot testing for any Proposer.",
        "Question: Is Tessaly Screen Systems the only acceptable screen manufacturer?",
        "Answer: No. Requests for approval of an equal product will be accepted under Section 00 21 13.",
        "ATTACHMENT 1 - PRE-PROPOSAL MEETING SIGN-IN SHEET, NOVEMBER 12, 2026",
        "The following firms attended the pre-proposal meeting at the plant. Attendance was recorded at the door.",
        ATTENDEES,
        "END OF ADDENDUM NO. 1",
    ),
    labels=(AddLabel("46 61 23", "2.11.A", SPARES_NEW,
                     lab("commercial", "spare membrane module quantity", "=", "4", "percent", trap=7)),),
    changes=(("revise_date", None, None), ("replace_paragraph", "46 61 23", "2.11.A")),
)

ADDENDUM_2 = AddendumDoc(
    doc_id="addendum_2", addendum_id="Addendum 2", short="Addendum #2",
    items=(
        "ADDENDUM #2",
        ADDENDUM_HEAD,
        "RFP No. CF-2026-14. Date of Addendum: November 24, 2026.",
        FICTION,
        ADDENDUM_INTRO,
        "CHANGES TO THE REQUEST FOR PROPOSALS",
        p("Revise the proposal due date to December 17, 2026 at 2:00 PM."),
        "CHANGES TO THE TECHNICAL SPECIFICATIONS",
        p("Section 46 21 23 Traveling Band Fine Screens: Delete paragraph 2.04.C."),
        p("Section 01 33 00 Submittal Procedures: Revise paragraph 1.04.C to read: " + SUBMITTAL_SIZE_NEW),
        "QUESTIONS AND ANSWERS",
        "Question: Does the pilot test requirement apply to the screens and the clarifier mechanisms?",
        "Answer: No. Pilot testing applies to the membrane bioreactor system only.",
        "END OF ADDENDUM #2",
    ),
    labels=(AddLabel("01 33 00", "1.04.C", SUBMITTAL_SIZE_NEW,
                     lab("submittal", "submittal file size", "<=", "100", "MB")),),
    changes=(("revise_date", None, None), ("delete_paragraph", "46 21 23", "2.04.C"),
             ("replace_paragraph", "01 33 00", "1.04.C")),
    deadline=("Proposal due date revised to December 17, 2026 at 2:00 PM",
              "Revise the proposal due date to December 17, 2026 at 2:00 PM."),
)

ADDENDUM_3 = AddendumDoc(
    doc_id="addendum_3", addendum_id="Addendum 3", short="Addendum No. Three",
    items=(
        "Addendum No. Three",
        ADDENDUM_HEAD,
        "RFP No. CF-2026-14. Date of Addendum: December 2, 2026.",
        FICTION,
        ADDENDUM_INTRO,
        "CHANGES TO THE TECHNICAL SPECIFICATIONS",
        p("Delete Section 46 43 13 in its entirety and replace with the attached Section 46 43 13, Circular "
          "Secondary Clarifier Equipment, issued with this Addendum."),
        p("Section 46 61 23 Submerged Membrane Bioreactor Equipment: Add paragraph 3.08.C: " + REMOTE_SUPPORT),
        "QUESTIONS AND ANSWERS",
        "Question: Does the reissued Section 46 43 13 change the warranty or the field services for the clarifier "
        "mechanisms?",
        "Answer: The reissued Section 46 43 13 replaces the earlier section in full. The Owner will evaluate "
        "proposals on the equipment described in the reissued section.",
        "END OF ADDENDUM NO. THREE",
    ),
    labels=(AddLabel("46 61 23", "3.08.C", REMOTE_SUPPORT,
                     lab("commercial", "remote support period", ">=", "90", "days")),),
    changes=(("replace_section", "46 43 13", None), ("add_paragraph", "46 61 23", "3.08.C")),
    reissued=S464313_REISSUED,
)
ADDENDA = (ADDENDUM_1, ADDENDUM_2, ADDENDUM_3)
# The text each replace, revise, or delete instruction points at in the spec book: (section, paragraph, old text).
ADDENDUM_TARGETS = (
    ("46 61 23", "2.11.A", SPARES_OLD),
    ("46 21 23", "2.04.C", SCREEN_DELETED),
    ("01 33 00", "1.04.C", SUBMITTAL_SIZE_OLD),
)

TRAPS = [
    Trap(1, "Mandatory commercial requirement buried at 46 61 23 paragraph 3.08.B.3: replacement membrane module unit "
            "prices held firm for 10 years, in the last quarter of the section"),
    Trap(2, "Installation certificate timing in 01 33 00 paragraph 1.07.A, reached through the reference in 46 61 23 "
            "paragraph 1.06.D"),
    Trap(3, "Requirement in a design-criteria table row after a page break: Permeate pump turndown, minimum 5:1 "
            "(46 61 23 paragraph 2.02.C)"),
    Trap(4, "Named manufacturer Tessaly Screen Systems Model TS-4400 with an approved equal clause at 46 21 23 "
            "paragraph 2.01.A"),
    Trap(5, "Effluent total nitrogen of 3 mg/L where the product literature only claims plants below 3 mg/L; expected "
            "needs_engineer"),
    Trap(6, "A 'should' statement at 46 61 23 paragraph 2.04.D that must not be marked mandatory"),
    Trap(7, "Addendum 1 replaces 46 61 23 paragraph 2.11.A: spare membrane modules rise from 2 percent to 4 percent of "
            "the installed modules"),
]

SPECS_COVER = [
    "CEDAR FALLS WATER POLLUTION CONTROL FACILITY PHASE 3 IMPROVEMENTS",
    "TECHNICAL SPECIFICATIONS AND BIDDING REQUIREMENTS",
    "FINE SCREEN, CLARIFIER MECHANISM, AND MEMBRANE BIOREACTOR EQUIPMENT PRESELECTION",
    "City of Cedar Falls",
    "Marlow Reed Associates",
    "October 2026",
    "Volume 2 of 2: Divisions 00 to 46",
    FICTION,
]
