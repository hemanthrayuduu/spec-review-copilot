"""Lakeview synthetic bid package: the one source for the PDFs and the golden labels (spec section 4.1).

Everything here is fictional: the Town of Lakeview, Lake Merrow, Harbor & Pine Engineers, and
Brightwater Systems. The text imitates the style of municipal specifications so the pipeline sees
realistic structure, numbering, and noise.

Labeling rules applied here (spec section 9, labeling protocol):
- Requirements are labeled only in relevant sections: the RFP, 01 33 00, 46 21 00, 46 43 00, 46 61 00.
- One label per obligation. A label's source text is the paragraph text without its marker, unless
  the label names a clause with `source`.
- Permit text yields permit limits, not requirements: its obligations fall on the plant operator,
  not on the equipment supplier.
- Text an addendum replaces carries no label; the addendum's version does, with from_addendum set.
"""

import random
from dataclasses import dataclass

PACKAGE_ID = "lakeview"
ADDENDUM_ID = "Addendum 1"
COMPETITOR = "Brightwater Systems"


@dataclass(frozen=True)
class L:
    """Golden label for one obligation."""

    category: str
    parameter: str | None = None
    operator: str | None = None
    value: str | None = None
    unit: str | None = None
    mandatory: bool = True
    named_manufacturer: tuple[str, ...] = ()
    or_equal_allowed: bool | None = None
    trap: int | None = None
    expected_status: str | None = None
    source: str | None = None  # the clause, when the paragraph holds more than one obligation
    flag: str | None = None  # red flag type for the brief
    deadline: str | None = None  # brief deadline text
    form: str | None = None  # brief required-form text


def lab(category: str, parameter: str | None = None, operator: str | None = None, value: str | None = None,
        unit: str | None = None, *, m: bool = True, **kw: object) -> L:
    return L(category, parameter, operator, value, unit, mandatory=m, **kw)  # type: ignore[arg-type]


@dataclass(frozen=True)
class P:
    """A paragraph. Its marker (A., 1., a. or 2.1) comes from its position."""

    text: str
    labels: tuple[L, ...] = ()
    kids: tuple["P", ...] = ()
    broken: tuple[str, str] | None = None  # (word, rendered form with <br>) for a forced line-end hyphen


def p(text: str, *labels: L, kids: tuple[P, ...] = (), broken: tuple[str, str] | None = None) -> P:
    return P(text, labels, kids, broken)


@dataclass(frozen=True)
class Table:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    labels: tuple[L | None, ...] = ()  # one per row, by position; the table takes the previous paragraph's path


@dataclass(frozen=True)
class Article:
    title: str
    body: tuple[P | Table, ...]


@dataclass(frozen=True)
class SpecSection:
    number: str
    title: str
    parts: tuple[tuple[Article, ...], tuple[Article, ...], tuple[Article, ...]]
    relevant: bool


@dataclass(frozen=True)
class RfpSection:
    number: int
    title: str
    body: tuple[P | Table, ...]


@dataclass(frozen=True)
class Limit:
    row: int  # index into the permit table rows
    limit_type: str
    value: float


@dataclass(frozen=True)
class Trap:
    trap: int
    description: str


BLANK_AFTER = "31 00 00"
FICTION = "FICTIONAL DOCUMENT GENERATED FOR SOFTWARE TESTING - NOT A REAL SOLICITATION"


# --- RFP ---------------------------------------------------------------------------------------

RFP_COVER = [
    "TOWN OF LAKEVIEW",
    "REQUEST FOR PROPOSALS",
    "MEMBRANE FILTRATION, BAND SCREEN, AND CLARIFIER EQUIPMENT PRESELECTION",
    "LAKEVIEW WASTEWATER TREATMENT PLANT PHASE 2 UPGRADE",
    "RFP No. 2026-07",
    "Issued October 5, 2026",
    "Department of Public Works, 41 Harbor Street, Lakeview",
    FICTION,
]

RFP = [
    RfpSection(1, "INTRODUCTION", (
        p("The Town of Lakeview (Owner) is upgrading the Lakeview Wastewater Treatment Plant to meet a new "
          "effluent total phosphorus limit of 0.1 mg/L for its discharge to Lake Merrow."),
        p("The Owner is preselecting the membrane filtration, band screen, and primary clarifier equipment. "
          "The selected Supplier will be assigned to the general contractor, who will install the equipment."),
        p("The Owner's engineer for the project is Harbor & Pine Engineers (Engineer)."),
        p("The equipment is specified in Sections 46 21 00, 46 43 00, and 46 61 00 of the Technical "
          "Specifications, which form part of this Request for Proposals."),
        p("The existing plant was built in 1978 and expanded in 1996. It provides screening, grit removal, "
          "primary settling, conventional activated sludge, secondary clarification, and chlorine disinfection. "
          "Waste sludge is thickened, aerobically digested, and hauled to a regional composting facility."),
        p("The Phase 2 Upgrade replaces the secondary process with a membrane bioreactor, replaces the existing "
          "bar screens with band screens, and rebuilds the two primary settling tanks with new mechanisms. The "
          "secondary clarifiers will be demolished, and their footprint will be used for the new membrane "
          "building."),
        p("The plant serves about 14,000 residents and a small industrial park. The annual average flow is "
          "1.4 MGD, and the plant is rated for 2.0 MGD after the upgrade. Wet weather flows reach 5.0 MGD "
          "during spring snowmelt."),
        p("Lake Merrow is a phosphorus limited lake used for drinking water, swimming, and fishing. The state "
          "total maximum daily load study for the lake assigned the plant a waste load allocation that the "
          "existing process cannot meet, which led to the new limit and the compliance schedule in the permit."),
        p("The Owner expects to advertise the construction contract in the spring of 2027 and to complete "
          "construction by the end of 2028, ahead of the July 1, 2029 compliance date."),
        p("Copies of the permit excerpt and the Technical Specifications are included with this Request for "
          "Proposals. Record drawings of the existing plant are available from the Engineer on request."),
    )),
    RfpSection(2, "SCOPE OF SUPPLY", (
        p("The Supplier shall furnish the membrane filtration system, two band screens, and two circular "
          "primary clarifier mechanisms as specified.", lab("commercial")),
        p("The Supplier shall provide equipment design, fabrication, delivery to the site, installation "
          "supervision, startup, testing, and operator training.", lab("commercial")),
        p("Equipment shall be delivered to the site within 40 weeks after approval of the shop drawings.",
          lab("schedule", "delivery time after shop drawing approval", "<=", "40", "weeks")),
        p("Shop drawings shall be submitted within 10 weeks after the notice of assignment.",
          lab("schedule", "shop drawing submittal time", "<=", "10", "weeks")),
        p("The Supplier may propose packaged skids for the chemical cleaning equipment.",
          lab("commercial", m=False)),
    )),
    RfpSection(3, "PROCUREMENT SCHEDULE", (
        p("Key dates for this procurement are listed below."),
        Table(("Event", "Date"), (
            ("Request for Proposals issued", "October 5, 2026"),
            ("Proposal due date", "November 17, 2026 at 2:00 PM"),
            ("Anticipated notice of selection", "January 2027"),
        )),
        p("Proposals shall be delivered to the Town Clerk, 41 Harbor Street, Lakeview, in a sealed envelope "
          "marked with the RFP number.", lab("submittal")),
        p("Requests for approval of an equal product shall be received no later than 14 days before the "
          "proposal due date.",
          lab("schedule", "approved equal request lead time", ">=", "14", "days",
              deadline="Requests for approval of an equal product due 14 days before the proposal due date")),
        p("Questions about this Request for Proposals shall be submitted in writing to the Engineer.",
          lab("submittal")),
    )),
    RfpSection(4, "PROPOSER QUALIFICATIONS", (
        p("The Supplier shall submit a list of at least three (3) installations of the proposed membrane "
          "system in municipal wastewater service, each in operation for not less than 2 years.",
          lab("qualification", "reference installations", ">=", "3", "installations", flag="experience_minimum")),
        p("For each installation, provide the owner's name, a contact person, the design flow, and the date "
          "of startup on Form B.", lab("submittal")),
        p("The Supplier shall maintain a service center able to place a technician on site within 48 hours "
          "of a request.", lab("qualification", "service response time", "<=", "48", "hours")),
        p("The Supplier should identify the location of its nearest parts warehouse.",
          lab("qualification", m=False)),
    )),
    RfpSection(5, "PILOT TESTING", (
        p("The Supplier shall conduct an on site pilot test of the proposed membrane system for not less "
          "than 90 days.",
          lab("testing_piloting", "pilot test duration", ">=", "90", "days", flag="pilot_testing")),
        p("The pilot unit shall use full scale membrane modules of the type proposed.", lab("testing_piloting")),
        p("The pilot shall demonstrate permeate total phosphorus not exceeding 0.1 mg/L for the final 30 "
          "days of operation.", lab("testing_piloting", "pilot permeate total phosphorus", "<=", "0.1", "mg/L")),
        p("The Owner will provide power, potable water, and a level pad for the pilot unit."),
        p("The Supplier shall submit a pilot test report within 30 days after the end of pilot testing.",
          lab("submittal", "pilot report submittal time", "<=", "30", "days")),
        p("The cost of pilot testing shall be included in the proposal price.", lab("commercial")),
    )),
    RfpSection(6, "WARRANTY AND PERFORMANCE GUARANTEE", (
        p("The Supplier shall warrant all equipment against defects in materials and workmanship for 2 years "
          "from substantial completion.", lab("warranty", "equipment warranty", "=", "2", "years")),
        p("The Supplier shall guarantee that the membrane system meets the effluent requirements of "
          "Section 46 61 00 for 1 year after startup.",
          lab("warranty", "process performance guarantee", "=", "1", "year")),
        p("If the guarantee is not met, the Supplier shall furnish additional equipment and labor at no cost "
          "to the Owner.", lab("warranty")),
    )),
    RfpSection(7, "COMMERCIAL TERMS", (
        p("Proposal prices shall remain valid for 120 days after the proposal due date.",
          lab("commercial", "price validity", ">=", "120", "days")),
        p("The selected Supplier shall furnish a performance bond in the amount of 100 percent of the "
          "contract price.", lab("commercial", "performance bond", "=", "100", "percent", flag="bond")),
        p("Liquidated damages of $1,500 per day shall be assessed for each day that equipment delivery is "
          "late.", lab("commercial", "liquidated damages", "=", "1,500", "USD/day", flag="liquidated_damages")),
        p("All iron and steel, manufactured products, and construction materials shall comply with the "
          "Build America, Buy America Act (BABA).", lab("domestic_content", flag="domestic_content")),
        p("The Supplier shall submit a BABA certification letter with the shop drawings.",
          lab("domestic_content")),
        p("Payment shall be made as follows: 90 percent on delivery and 10 percent on final acceptance.",
          lab("commercial", "payment on delivery", "=", "90", "percent")),
        p("The Supplier shall maintain commercial general liability insurance of not less than $2,000,000 per "
          "occurrence.", lab("commercial", "general liability insurance", ">=", "2,000,000", "USD")),
        p("The Supplier shall name the Owner and the Engineer as additional insureds on its liability "
          "policies.", lab("commercial")),
        p("The Supplier shall indemnify the Owner against claims arising from defects in the equipment.",
          lab("commercial")),
    )),
    RfpSection(8, "EVALUATION OF PROPOSALS", (
        p("Proposals will be scored on the criteria below."),
        Table(("Criterion", "Points"), (
            ("Technical approach and equipment quality", "35"),
            ("Life cycle cost", "30"),
            ("Experience and references", "20"),
            ("Pilot testing plan", "15"),
        )),
        p("A selection committee of the Owner's staff and the Engineer will score each proposal. Life cycle "
          "cost will be calculated over 20 years at a discount rate of 3 percent, using the power, chemical, "
          "and membrane replacement costs stated in the proposal."),
        p("The Owner may interview the two highest scoring Proposers before making a selection."),
        p("The Owner reserves the right to reject any or all proposals and to waive informalities."),
        p("Proposers should visit the existing plant before submitting a proposal.", lab("commercial", m=False)),
    )),
    RfpSection(9, "PROPOSAL FORM", (
        p("The proposal shall include a completed Form A and a completed Form B.", lab("submittal")),
    )),
]

FORM_A = "Form A - Proposal Pricing Form"
FORM_B = "Form B - Reference Installations"
FORM_A_TABLE = Table(("Item", "Description", "Lump Sum Price"), (
    ("1", "Membrane filtration system", "$"),
    ("2", "Band screens (2)", "$"),
    ("3", "Circular primary clarifier mechanisms (2)", "$"),
    ("4", "Pilot testing", "$"),
    ("5", "Total proposal price", "$"),
))
FORM_B_TABLE = Table(("Installation", "Location", "Contact", "Design Flow (MGD)", "Startup Date"),
                     (("", "", "", "", ""), ("", "", "", "", ""), ("", "", "", "", "")))


# --- Relevant specification sections ------------------------------------------------------------

def _refs(*items: str) -> P:
    return p("The following standards apply to the work of this Section:", kids=tuple(p(i) for i in items))


S013300 = SpecSection("01 33 00", "SUBMITTAL PROCEDURES", (
    (
        Article("SUMMARY", (
            p("This Section describes the procedures for preparing and transmitting submittals required by "
              "the Contract Documents."),
            p("Submittals for individual equipment are listed in the equipment Sections."),
        )),
        Article("DEFINITIONS", (
            p("Action submittals: written and graphic information that requires the Engineer's responsive "
              "action."),
            p("Informational submittals: written information that does not require the Engineer's approval."),
            p("Operation and maintenance manuals: documents that describe the operation, maintenance, and "
              "repair of equipment."),
        )),
        Article("SUBMITTAL SCHEDULE", (
            p("The Supplier shall submit a submittal schedule within 14 days after the notice to proceed.",
              lab("submittal", "submittal schedule lead time", "<=", "14", "days")),
            p("Allow 21 days for the Engineer's initial review of each submittal.",
              lab("schedule", "engineer review period", "=", "21", "days")),
            p("Submittals should be organized by specification paragraph.", lab("submittal", m=False)),
        )),
        Article("SUBMITTAL FORMAT", (
            p("Each submittal shall be transmitted electronically in PDF format with a transmittal form.",
              lab("submittal")),
            p("Each submittal shall include a cover sheet listing the project name, the specification "
              "Section, and the paragraph numbers covered.", lab("submittal")),
            p("Individual submittal files shall not exceed 50 MB.",
              lab("submittal", "submittal file size", "<=", "50", "MB")),
        )),
        Article("SHOP DRAWINGS AND PRODUCT DATA", (
            p("Shop drawings shall be drawn to scale and shall show dimensions, materials, equipment weights, "
              "and anchor bolt locations.",
              lab("submittal", source="Shop drawings shall be drawn to scale"),
              lab("submittal", source="shall show dimensions, materials, equipment weights, and anchor bolt "
                                      "locations")),
            p("Product data shall be marked to show the specific model, options, and accessories proposed.",
              lab("submittal")),
        )),
        Article("OPERATION AND MAINTENANCE MANUALS", (
            p("Manuals shall include equipment descriptions, operating procedures, lubrication schedules, "
              "troubleshooting guides, and a recommended spare parts list.", lab("submittal")),
            p("Operation and maintenance manuals shall be submitted in searchable PDF format no later than 30 "
              "days before startup.",
              lab("submittal", "O&M manual submittal lead time", ">=", "30", "days", trap=2)),
            p("Preliminary manuals shall be reviewed by the Engineer before the final manuals are prepared.",
              lab("submittal")),
        )),
        Article("RESUBMITTALS", (
            p("Resubmittals shall identify every change made since the previous submission.", lab("submittal")),
        )),
    ),
    (),
    (),
), relevant=True)


S462100 = SpecSection("46 21 00", "BAND SCREENS", (
    (
        Article("SUMMARY", (
            p("Section includes two center flow band screens, wash water booster pumps, screenings washer "
              "compactors, and local control panels."),
            p("Related sections: Section 01 33 00 Submittal Procedures."),
        )),
        Article("REFERENCES", (
            _refs("ASTM A240/A240M - Chromium and Chromium-Nickel Stainless Steel Plate, Sheet, and Strip.",
                  "ASTM A276/A276M - Stainless Steel Bars and Shapes.",
                  "ANSI/AGMA 6013 - Standard for Industrial Enclosed Gear Drives.",
                  "NEMA 250 - Enclosures for Electrical Equipment (1000 Volts Maximum).",
                  "NEMA MG 1 - Motors and Generators.",
                  "NFPA 70 - National Electrical Code.",
                  "UL 508A - Industrial Control Panels."),
        )),
        Article("SYSTEM DESCRIPTION", (
            p("The band screens remove hair, fibers, and trash from the raw wastewater to protect the "
              "downstream membrane system."),
            p("Screenings are lifted by the moving panels, washed off by the spray bar, and conveyed to the "
              "washer compactors."),
        )),
        Article("SUBMITTALS", (
            p("Submit shop drawings for the band screens in accordance with Section 01 33 00.", lab("submittal")),
            p("Submit hydraulic calculations showing the headloss through each screen at peak hour flow with "
              "the screen 30 percent blinded.",
              lab("submittal", "blinding assumed in headloss calculation", "=", "30", "percent")),
        )),
        Article("QUALITY ASSURANCE", (
            p("Screens shall be the product of a manufacturer regularly engaged in producing band screens for "
              "municipal service.", lab("qualification")),
        )),
        Article("WARRANTY", (
            p("The band screens shall be warranted against defects in materials and workmanship for 2 years "
              "from substantial completion.", lab("warranty", "band screen warranty", "=", "2", "years")),
        )),
    ),
    (
        Article("BAND SCREENS", (
            p("Band screens shall be Brightwater Systems Model BS-300, or approved equal.",
              lab("material", named_manufacturer=(COMPETITOR,), or_equal_allowed=True, trap=4,
                  flag="named_manufacturer")),
            p("Each screen shall pass the peak hour flow of 5.0 MGD with the other screen out of service.",
              lab("performance", "screen capacity", ">=", "5.0", "MGD")),
            p("Screen panels shall have perforations of 3 mm diameter."),  # replaced by Addendum 1
            p("Headloss through a clean screen shall not exceed 6 inches at peak hour flow.",
              lab("performance", "clean screen headloss", "<=", "6", "inches")),
        )),
        Article("MATERIALS", (
            p("Screen frames, panels, and wetted parts shall be Type 316 stainless steel.",
              lab("material", "wetted parts material")),
            p("Anchor bolts and fasteners shall be Type 316 stainless steel.", lab("material", "fastener material")),
            p("Seals and brushes shall be resistant to grease, hydrogen sulfide, and chlorine.", lab("material")),
        )),
        Article("SPRAY WASH SYSTEM", (
            p("Provide a spray wash system with a dedicated booster pump for each screen.", lab("performance")),
            p("Each booster pump shall deliver not less than 40 gpm at 80 psi.",
              lab("performance", "booster pump flow", ">=", "40", "gpm")),
            p("Spray nozzles should be of the quick disconnect type.", lab("material", m=False)),
            p("The screen should be arranged for future addition of a second wash water booster pump.",
              lab("design_basis", m=False)),
        )),
        Article("SCREENINGS WASHER COMPACTORS", (
            p("Provide one screenings washer compactor for each screen.", lab("performance")),
            p("Washed and compacted screenings shall have a solids content of not less than 40 percent.",
              lab("performance", "screenings solids content", ">=", "40", "percent")),
            p("The washer compactor shall reduce the organic content of the screenings by not less than 80 "
              "percent.", lab("performance", "organics removal", ">=", "80", "percent")),
        )),
        Article("CONTROLS", (
            p("Each screen shall be furnished with a NEMA 4X stainless steel local control panel.",
              lab("material", "control panel enclosure")),
            p("The screen shall start automatically on high differential level and on an adjustable timer.",
              lab("performance")),
            p("Provide a level sensor upstream and downstream of each screen to measure differential level.",
              lab("performance")),
            p("Motors shall be premium efficiency, totally enclosed, and rated for 460 volts, 3 phase, 60 Hz.",
              lab("material", "motor voltage", "=", "460", "volts")),
        )),
    ),
    (
        Article("INSTALLATION", (
            p("Install the screens in accordance with the manufacturer's written instructions and the approved "
              "shop drawings.", lab("commercial")),
        )),
        Article("FIELD TESTING", (
            p("After installation, each screen shall be operated for not less than 8 hours without malfunction.",
              lab("testing_piloting", "screen field test duration", ">=", "8", "hours")),
            p("The Supplier shall furnish a written field test report signed by the manufacturer's "
              "representative.", lab("testing_piloting")),
        )),
        Article("MANUFACTURER'S SERVICES", (
            p("Provide a manufacturer's representative on site for not less than 4 days for installation "
              "inspection and startup of the screens.",
              lab("commercial", "screen field service", ">=", "4", "days")),
            p("Provide not less than 8 hours of operator training on the band screens.",
              lab("commercial", "screen operator training", ">=", "8", "hours")),
        )),
    ),
), relevant=True)


S464300 = SpecSection("46 43 00", "CIRCULAR CLARIFIER EQUIPMENT", (
    (
        Article("SUMMARY", (
            p("Section includes two 60 foot diameter center drive circular primary clarifier mechanisms with "
              "scum skimming equipment."),
            p("Related sections: Section 01 33 00 Submittal Procedures."),
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
        Article("DESIGN CONDITIONS", (
            p("Each clarifier shall be designed for a peak hour flow of 2.5 MGD.",
              lab("design_basis", "peak hour flow per clarifier", "=", "2.5", "MGD")),
            p("Each clarifier shall be designed for a surface overflow rate not exceeding 2,500 gpd/sf at peak "
              "hour flow.", lab("design_basis", "surface overflow rate", "<=", "2,500", "gpd/sf")),
        )),
        Article("SUBMITTALS", (
            p("Submit drive torque calculations and structural calculations for the clarifier mechanisms, "
              "sealed by a professional engineer.", lab("submittal")),
            p("Submit the drive manufacturer's certification of the AGMA service factor.", lab("certification")),
        )),
        Article("WARRANTY", (
            p("The clarifier drives shall be warranted for 5 years from substantial completion.",
              lab("warranty", "clarifier drive warranty", "=", "5", "years")),
        )),
    ),
    (
        Article("MANUFACTURERS", (
            p("Clarifier mechanisms, drives, and skimmers shall be furnished by a single manufacturer.",
              lab("qualification")),
        )),
        Article("DRIVE UNIT", (
            p("The drive shall have a continuous torque rating of not less than 45,000 ft-lb.",
              lab("performance", "drive continuous torque", ">=", "45,000", "ft-lb")),
            p("The drive shall be rated for a service life of not less than 20 years at continuous torque.",
              lab("performance", "drive service life", ">=", "20", "years")),
            p("Drive motors shall be 1 hp, 460 volts, 3 phase, totally enclosed.",
              lab("material", "drive motor size", "=", "1", "hp")),
        )),
        Article("CONTROLS AND ALARMS", (
            p("Provide a torque overload device that stops the drive motor at 120 percent of the continuous "
              "torque rating.", lab("performance", "torque shutdown setpoint", "=", "120", "percent")),
            p("The torque overload device shall have a local torque indicator.", lab("performance")),
            p("The clarifier drive should be furnished with a torque overload alarm contact.",
              lab("performance", m=False, trap=6)),
        )),
        Article("COLLECTOR ARMS AND SCRAPERS", (
            p("Provide two collector arms with steel scraper blades and replaceable squeegees.", lab("material")),
            p("Scraper blades shall travel at a tip speed of not more than 10 feet per minute.",
              lab("performance", "scraper tip speed", "<=", "10", "feet per minute")),
        )),
        Article("SCUM REMOVAL", (
            p("Provide a full radius skimmer that moves scum to a scum box at each revolution.",
              lab("performance")),
            p("The skimmer should discharge to a scum box located outside the effluent launder.",
              lab("performance", m=False)),
        )),
        Article("MATERIALS AND COATINGS", (
            p("Submerged steel shall be galvanized after fabrication in accordance with ASTM A123.",
              lab("material")),
            p("Anchor bolts, nuts, and washers for the mechanisms shall be Type 316 stainless steel.",
              lab("material", "anchor bolt material")),
        )),
        Article("INFLUENT WELL AND BAFFLES", (
            p("Provide an energy dissipating influent well with a diameter of not less than 15 percent of the "
              "clarifier diameter.", lab("design_basis", "influent well diameter", ">=", "15", "percent")),
            p("Provide fiberglass density current baffles around the full perimeter.", lab("material")),
        )),
    ),
    (
        Article("INSTALLATION", (
            p("Install the mechanisms under the supervision of the manufacturer's representative.",
              lab("commercial")),
            p("Grout the drive support to provide full bearing under the drive base.", lab("commercial")),
        )),
        Article("FIELD TESTING", (
            p("Operate each mechanism in the dry for not less than 4 hours to show freedom from binding.",
              lab("testing_piloting", "dry run test duration", ">=", "4", "hours")),
            p("Operate each mechanism with water for not less than 24 hours and record the drive torque.",
              lab("testing_piloting", "wet test duration", ">=", "24", "hours")),
        )),
        Article("MANUFACTURER'S SERVICES", (
            p("Provide a manufacturer's representative on site for not less than 3 days for installation "
              "inspection, startup, and training on the clarifier mechanisms.",
              lab("commercial", "clarifier field service", ">=", "3", "days")),
        )),
    ),
), relevant=True)


DESIGN_ROWS: tuple[tuple[str, str, str | None, str, str | None], ...] = (
    # parameter, value text, operator, label value, label unit
    ("Design average daily flow", "2.0 MGD", "=", "2.0", "MGD"),
    ("Maximum month flow", "2.6 MGD", "=", "2.6", "MGD"),
    ("Peak day flow", "4.0 MGD", "=", "4.0", "MGD"),
    ("Peak hour flow", "5.0 MGD", "=", "5.0", "MGD"),
    ("Number of membrane trains", "4", "=", "4", None),
    ("Trains in service at peak hour flow", "3", "=", "3", None),
    ("Mixed liquor temperature, minimum", "10 °C", "=", "10", "°C"),
    ("Mixed liquor temperature, maximum", "28 °C", "=", "28", "°C"),
    ("Influent BOD5, design average", "220 mg/L", "=", "220", "mg/L"),
    ("Influent TSS, design average", "240 mg/L", "=", "240", "mg/L"),
    ("Influent TKN, design average", "45 mg/L", "=", "45", "mg/L"),
    ("Influent total phosphorus, design average", "7.0 mg/L", "=", "7.0", "mg/L"),
    ("Influent ammonia nitrogen, design average", "30 mg/L", "=", "30", "mg/L"),
    ("Influent alkalinity, minimum", "150 mg/L as CaCO3", "=", "150", "mg/L as CaCO3"),
    ("Influent pH", "6.5 to 8.5", "range", "6.5 to 8.5", None),
    ("Design BOD5 load", "3,670 lb/day", "=", "3,670", "lb/day"),
    ("Design TSS load", "4,000 lb/day", "=", "4,000", "lb/day"),
    ("Mixed liquor suspended solids in membrane tanks", "8,000 to 10,000 mg/L", "range", "8,000 to 10,000",
     "mg/L"),
    ("Solids retention time", "15 days", "=", "15", "days"),
    ("Maximum net flux, design average flow, all trains in service", "12 gfd", "<=", "12", "gfd"),
    ("Maximum net flux, peak day flow, all trains in service", "18 gfd", "<=", "18", "gfd"),
    ("Maximum net flux, peak hour flow, one train out of service", "22 gfd", "<=", "22", "gfd"),
    ("Minimum installed membrane area per train", "76,000 sf", ">=", "76,000", "sf"),
    ("Spare cassette space per train, minimum", "15 percent", ">=", "15", "percent"),
    ("Maximum membrane tank side water depth", "13 feet", "<=", "13", "feet"),
    ("Maximum air scour demand per train", "1,500 scfm", "<=", "1,500", "scfm"),
    ("Maintenance clean frequency, maximum", "2 per week", "<=", "2", "per week"),
    ("Recovery clean interval, minimum", "6 months", ">=", "6", "months"),
    ("Sodium hypochlorite for maintenance cleaning", "200 mg/L", "=", "200", "mg/L"),
    ("Citric acid for recovery cleaning", "2,000 mg/L", "=", "2,000", "mg/L"),
    ("Permeate pump turndown, minimum", "4:1", ">=", "4:1", None),
    ("Maximum permeate pump suction lift", "15 feet", "<=", "15", "feet"),
    ("Mixed liquor recycle from membrane tanks", "4 to 5 times design average flow", "range", "4 to 5",
     "times design average flow"),
    ("Dissolved oxygen in membrane tanks, minimum", "2.0 mg/L", ">=", "2.0", "mg/L"),
    ("Membrane tank freeboard, minimum", "18 inches", ">=", "18", "inches"),
    ("Permeate BOD5, maximum", "5 mg/L", "<=", "5", "mg/L"),
    ("Permeate ammonia nitrogen, maximum", "1.0 mg/L", "<=", "1.0", "mg/L"),
    ("Maximum transmembrane pressure", "12 psi", "<=", "12", "psi"),
    ("Permeate total nitrogen, maximum", "10 mg/L", "<=", "10", "mg/L"),
)
TRAP3_PARAMETER = "Maximum transmembrane pressure"

DESIGN_TABLE = Table(
    ("Parameter", "Value"),
    tuple((name, shown) for name, shown, *_ in DESIGN_ROWS),
    tuple(lab("effluent_limit" if name.startswith("Permeate ") and "pump" not in name else "design_basis",
              name.lower(), op, value, unit, trap=3) for name, _, op, value, unit in DESIGN_ROWS),
)

TRAP7_OLD = "Membrane modules shall carry a warranty of 5 years."
TRAP7_NEW = "Membrane modules shall carry a full replacement warranty of 7 years from substantial completion."
TRAP1_TEXT = ("The Contractor shall provide a factory-trained service technician on site for not less than 10 "
              "working days during startup.")

S466100 = SpecSection("46 61 00", "MEMBRANE FILTRATION EQUIPMENT", (
    (
        Article("SUMMARY", (
            p("Section includes a complete immersed membrane filtration system for the membrane bioreactor "
              "process, including membrane modules and cassettes, permeate pumps, membrane air scour blowers, "
              "chemical cleaning equipment, instruments, and the membrane system control panel."),
            p("Related sections: Section 01 33 00 Submittal Procedures and Section 46 21 00 Band Screens."),
        )),
        Article("REFERENCES", (
            _refs("ANSI/ASME B16.5 - Pipe Flanges and Flanged Fittings.",
                  "ANSI/HI 9.6.4 - Rotodynamic Pumps for Vibration Measurements and Allowable Values.",
                  "ANSI/HI 14.6 - Rotodynamic Pumps for Hydraulic Performance Acceptance Tests.",
                  "ASME PTC 13 - Wire-to-Air Performance Test Code for Blower Systems.",
                  "ASTM A193/A193M - Alloy-Steel and Stainless Steel Bolting for High Temperature Service.",
                  "ASTM A240/A240M - Chromium and Chromium-Nickel Stainless Steel Plate, Sheet, and Strip.",
                  "ASTM A276/A276M - Stainless Steel Bars and Shapes.",
                  "ASTM A312/A312M - Seamless, Welded, and Heavily Cold Worked Austenitic Stainless Steel Pipes.",
                  "ASTM D1785 - Poly(Vinyl Chloride) (PVC) Plastic Pipe, Schedules 40, 80, and 120.",
                  "ASTM D2467 - Poly(Vinyl Chloride) (PVC) Plastic Pipe Fittings, Schedule 80.",
                  "ASTM F1554 - Anchor Bolts, Steel, 36, 55, and 105-ksi Yield Strength.",
                  "IEC 61131-3 - Programmable Controllers, Programming Languages.",
                  "IEEE 519 - Harmonic Control in Electric Power Systems.",
                  "ISA 5.1 - Instrumentation Symbols and Identification.",
                  "ISA 18.2 - Management of Alarm Systems for the Process Industries.",
                  "NEMA 250 - Enclosures for Electrical Equipment (1000 Volts Maximum).",
                  "NEMA MG 1 - Motors and Generators.",
                  "NFPA 70 - National Electrical Code.",
                  "NFPA 79 - Electrical Standard for Industrial Machinery.",
                  "UL 508A - Industrial Control Panels."),
        )),
        Article("DEFINITIONS", (
            p("Flux: permeate flow per unit of membrane surface area, in gallons per square foot per day (gfd)."),
            p("Net flux: flux averaged over a full production and relaxation or backpulse cycle, after "
              "deducting backpulse volume."),
            p("Transmembrane pressure (TMP): the pressure difference across the membrane between the mixed "
              "liquor side and the permeate side."),
            p("Train: one membrane tank with its cassettes, permeate pump, valves, and instruments."),
            p("Cassette: a frame holding membrane modules, lifted into and out of the tank as one unit."),
            p("Maintenance clean: a short chemical clean done in place with the tank in service."),
            p("Recovery clean: an extended chemical soak done with the tank drained of mixed liquor."),
            p("Permeability: net flux divided by transmembrane pressure, corrected to 20 °C."),
        )),
        Article("ABBREVIATIONS", (
            p("The following abbreviations are used in this Section:", kids=tuple(p(x) for x in (
                "BOD5: five-day biochemical oxygen demand.", "CIP: clean in place.", "DO: dissolved oxygen.",
                "gfd: gallons per square foot per day.", "HMI: human machine interface.",
                "MBR: membrane bioreactor.", "MLSS: mixed liquor suspended solids.",
                "NTU: nephelometric turbidity units.", "PLC: programmable logic controller.",
                "PVDF: polyvinylidene fluoride.", "SCADA: supervisory control and data acquisition.",
                "SRT: solids retention time.", "TKN: total Kjeldahl nitrogen.", "TMP: transmembrane pressure.",
                "TSS: total suspended solids.", "UPS: uninterruptible power supply.",
                "VFD: variable frequency drive."))),
        )),
        Article("SYSTEM DESCRIPTION", (
            p("The membrane system separates mixed liquor from the aerobic zone into permeate and returned "
              "mixed liquor. Permeate is drawn through the membranes by the permeate pumps and sent to "
              "disinfection."),
            p("Each train operates on a filtration cycle of production followed by relaxation or backpulse. "
              "Air scour runs during production to limit solids buildup on the membrane surface."),
            p("The membrane system shall be designed to accept flow equalization basin return flows of up "
              "to 0.5 MGD without exceeding the design net flux.",
              lab("design_basis", "equalization return flow", "<=", "0.5", "MGD"),
              broken=("equalization", "equali-<br>zation")),
        )),
        Article("SUBMITTALS", (
            p("Submit operation and maintenance manuals per Section 01 33 00.", lab("submittal")),
            p("Submit shop drawings showing the cassette arrangement, the piping and valve layouts, and the "
              "dimensions of each membrane tank.", lab("submittal")),
            p("Submit a process design report showing the flux, transmembrane pressure, and air scour demand "
              "at each design flow.", lab("submittal")),
            p("Submit the membrane manufacturer's written warranty.", lab("submittal")),
            p("Submit control system programming documentation, including control narratives and alarm lists, "
              "60 days before factory testing.",
              lab("submittal", "control documentation lead time", ">=", "60", "days")),
        )),
        Article("QUALITY ASSURANCE", (
            p("The membrane modules shall be manufactured under a quality management system certified to "
              "ISO 9001.", lab("certification")),
            p("The membrane system supplier shall have single source responsibility for the membrane "
              "modules, permeate pumps, blowers, and controls.", lab("qualification")),
            p("The membrane system control panel shall be listed under UL 508A.", lab("certification")),
        )),
        Article("DELIVERY, STORAGE, AND HANDLING", (
            p("Membrane modules shall be shipped in sealed containers with a preservative solution.",
              lab("material")),
            p("Store membrane modules indoors at temperatures between 40 and 95 degrees F.",
              lab("material", "module storage temperature", "range", "40 to 95", "degrees F")),
            p("Membrane modules shall not be allowed to dry out after wetting.", lab("material")),
        )),
        Article("WARRANTY", (
            p("The membrane system, except the membrane modules, shall be warranted against defects in "
              "materials and workmanship for 2 years from substantial completion.",
              lab("warranty", "membrane system warranty", "=", "2", "years")),
            p("Warranty claims shall be answered within 5 working days.",
              lab("warranty", "warranty response time", "<=", "5", "working days")),
        )),
    ),
    (
        Article("MANUFACTURERS", (
            p("The membrane system shall be furnished by the Supplier selected under the Request for Proposals.",
              lab("commercial")),
            p("Membranes shall be immersed hollow fiber or flat sheet membranes with a nominal pore size of "
              "0.04 micron or smaller.", lab("material", "nominal pore size", "<=", "0.04", "micron")),
        )),
        Article("DESIGN CRITERIA", (
            p("The membrane system shall produce effluent total phosphorus not exceeding 0.1 mg/L as a "
              "monthly average.",
              lab("effluent_limit", "effluent total phosphorus", "<=", "0.1", "mg/L", trap=5,
                  expected_status="needs_engineer")),
            p("The membrane system shall be designed for the following conditions:"),
            DESIGN_TABLE,
            p("Permeate turbidity shall not exceed 0.2 NTU 95 percent of the time.",
              lab("effluent_limit", "permeate turbidity", "<=", "0.2", "NTU")),
            p("Permeate total suspended solids shall not exceed 1 mg/L.",
              lab("effluent_limit", "permeate TSS", "<=", "1", "mg/L")),
        )),
        Article("MEMBRANE CASSETTES", (
            p("Each cassette shall be removable from its tank without draining the other trains.",
              lab("performance")),
            p("Cassette frames shall be Type 316 stainless steel.", lab("material", "cassette frame material")),
            p("Membrane cassettes should be interchangeable between trains.", lab("design_basis", m=False)),
            p("Each cassette shall weigh not more than 4,000 pounds when lifted wet from the tank.",
              lab("design_basis", "cassette lifting weight", "<=", "4,000", "pounds")),
        )),
        Article("MEMBRANE MODULES", (
            p("Membrane fibers shall be made of polyvinylidene fluoride (PVDF) with an internal support.",
              lab("material", "membrane material")),
            p(TRAP7_OLD),  # replaced by Addendum 1
            p("Each module shall be tested for integrity at the factory before shipment.",
              lab("testing_piloting")),
            p("Membranes shall tolerate a cumulative sodium hypochlorite exposure of not less than 500,000 ppm "
              "hours over the membrane life.",
              lab("material", "chlorine exposure tolerance", ">=", "500,000", "ppm hours")),
        )),
        Article("PERMEATE PUMPS", (
            p("Provide one permeate pump for each train, plus one installed spare pump.", lab("performance")),
            p("Each permeate pump shall deliver 1,160 gpm at peak hour flow with one train out of service.",
              lab("performance", "permeate pump capacity", "=", "1,160", "gpm")),
            p("The Supplier may furnish permeate pumps of either the end suction or the self priming type.",
              lab("material", m=False)),
            p("Permeate pumps shall be driven by variable frequency drives.", lab("performance")),
            p("Permeate pumps shall be capable of reverse flow for backpulsing.", lab("performance")),
        )),
        Article("MEMBRANE AIR SCOUR BLOWERS", (
            p("Provide one air scour blower for each train and one installed standby blower.", lab("performance")),
            p("Blowers shall be rotary lobe or rotary screw type with sound enclosures.", lab("material")),
            p("Blower sound pressure level shall not exceed 80 dBA at 3 feet from the enclosure.",
              lab("performance", "blower sound pressure level", "<=", "80", "dBA")),
        )),
        Article("CHEMICAL CLEANING SYSTEM", (
            p("Provide a chemical cleaning system for maintenance and recovery cleaning with sodium hypochlorite "
              "and citric acid.", lab("performance")),
            p("Chemical metering pumps shall be peristaltic hose pumps.", lab("material")),
            p("Each chemical storage tank shall hold not less than 30 days of chemical at design average "
              "conditions.", lab("design_basis", "chemical storage", ">=", "30", "days")),
            p("Provide secondary containment sized for 110 percent of the largest tank.",
              lab("design_basis", "containment volume", ">=", "110", "percent")),
        )),
        Article("INSTRUMENTS", (
            p("Provide a turbidimeter on the combined permeate of each train.", lab("performance")),
            p("Provide a transmembrane pressure transmitter on each train.", lab("performance")),
            p("Flow meters shall be magnetic flow meters with an accuracy of plus or minus 0.5 percent of rate.",
              lab("performance", "flow meter accuracy", "<=", "0.5", "percent")),
        )),
        Article("MEMBRANE SYSTEM CONTROL PANEL", (
            p("Provide a programmable logic controller (PLC) control panel in a NEMA 12 enclosure for indoor "
              "installation.", lab("material", "control panel enclosure")),
            p("The control panel shall communicate with the plant SCADA system over EtherNet/IP.",
              lab("performance")),
            p("Provide an uninterruptible power supply that keeps the PLC running for not less than 30 minutes.",
              lab("performance", "UPS runtime", ">=", "30", "minutes")),
            p("The control system shall automatically take a train out of production when transmembrane "
              "pressure exceeds the high setpoint.", lab("performance")),
        )),
        Article("CONTROL DESCRIPTION", (
            p("The membrane system shall operate in automatic mode from the membrane system control panel and "
              "from the plant SCADA system.", lab("performance")),
            p("In production mode the PLC shall adjust the permeate pump speed to hold each train at its flow "
              "setpoint.", lab("performance")),
            p("Train flow setpoints shall follow the influent flow so that the membrane tank level stays within 6 "
              "inches of the level setpoint.", lab("performance", "membrane tank level band", "<=", "6", "inches")),
            p("Relaxation or backpulse shall occur every 10 to 15 minutes, adjustable by the operator.",
              lab("performance", "backpulse interval", "range", "10 to 15", "minutes")),
            p("Air scour shall run continuously while a train is in production.", lab("performance")),
            p("The PLC shall start a maintenance clean on each train at an interval set by the operator.",
              lab("performance")),
            p("The PLC shall lock out a train in recovery clean mode until the operator confirms that the clean "
              "is complete.", lab("performance")),
            p("High transmembrane pressure, low permeability, high permeate turbidity, and blower failure shall "
              "each generate an alarm at the control panel and at SCADA.", lab("performance")),
            p("Alarm setpoints shall be adjustable from the operator interface without changes to the PLC "
              "program.", lab("performance")),
            p("The operator interface shall trend flux, transmembrane pressure, permeability, and turbidity for "
              "each train for not less than 90 days.", lab("performance", "trend storage", ">=", "90", "days")),
            p("Provide a color touchscreen operator interface not smaller than 15 inches on the control panel "
              "door.", lab("material", "operator interface size", ">=", "15", "inches")),
        )),
        Article("FACTORY TESTING", (
            p("Test the control panel at the factory with the final PLC program before shipment.",
              lab("testing_piloting")),
            p("Notify the Engineer at least 21 days before the factory test of the control panel.",
              lab("testing_piloting", "factory test notice", ">=", "21", "days")),
            p("Permeate pumps shall be tested at the factory in accordance with ANSI/HI 14.6, acceptance grade 1B.",
              lab("testing_piloting")),
            p("Air scour blowers shall be tested at the factory in accordance with ASME PTC 13.",
              lab("testing_piloting")),
            p("Submit certified factory test reports before the equipment ships.", lab("submittal")),
        )),
        Article("SHOP PAINTING", (
            p("Shop prime and finish coat ferrous metal surfaces that will not be submerged.", lab("material")),
            p("Submerged components shall be stainless steel or plastic and shall not be painted.",
              lab("material")),
        )),
        Article("SPARE PARTS", (
            p("Furnish spare membrane modules equal to 5 percent of the installed modules.",
              lab("commercial", "spare membrane modules", "=", "5", "percent")),
            p("Furnish one spare permeate pump seal kit and one spare set of blower drive belts.",
              lab("commercial")),
        )),
    ),
    (
        Article("EXAMINATION", (
            p("Verify that membrane tanks are clean and free of debris before installing cassettes.",
              lab("commercial")),
        )),
        Article("INSTALLATION", (
            p("Install cassettes level to within 0.25 inch across each cassette.",
              lab("commercial", "cassette installation level tolerance", "<=", "0.25", "inch")),
            p("Do not install membrane modules until the tanks have been flushed and the band screens are in "
              "operation.", lab("schedule")),
        )),
        Article("CLEAN WATER TESTING", (
            p("Perform a clean water test on each train to confirm permeate flow and transmembrane pressure "
              "before mixed liquor is introduced.", lab("testing_piloting")),
            p("Clean water permeability shall be not less than 90 percent of the value stated in the process "
              "design report.", lab("testing_piloting", "clean water permeability", ">=", "90", "percent")),
        )),
        Article("MEMBRANE INTEGRITY TESTING", (
            p("Perform a pressure decay test on each train before startup.", lab("testing_piloting")),
            p("The pressure decay rate shall not exceed 0.5 psi in 10 minutes.",
              lab("testing_piloting", "pressure decay rate", "<=", "0.5", "psi in 10 minutes")),
            p("Repair or replace modules that fail the integrity test and retest the train.",
              lab("testing_piloting")),
        )),
        Article("FUNCTIONAL TESTING", (
            p("Demonstrate every control mode, alarm, and interlock in the presence of the Engineer.",
              lab("testing_piloting")),
            p("Demonstrate a maintenance clean and a recovery clean on one train.", lab("testing_piloting")),
            p("Simulate a power failure and show that the system restarts in automatic mode when power returns.",
              lab("testing_piloting")),
        )),
        Article("PERFORMANCE TESTING", (
            p("Conduct a performance test of 30 days after the biological process has reached steady state.",
              lab("testing_piloting", "performance test duration", "=", "30", "days")),
            p("During the test the system shall treat the design average flow with net flux and transmembrane "
              "pressure within the limits in Article 2.02.", lab("testing_piloting")),
            p("Collect composite permeate samples three times per week for total phosphorus and TSS.",
              lab("testing_piloting", "permeate sampling frequency", "=", "3", "per week")),
            p("If the performance test fails, the Supplier shall modify the system and repeat the test at no "
              "cost to the Owner.", lab("testing_piloting")),
        )),
        Article("STARTUP", (
            p("Seed the membrane tanks with mixed liquor from the existing plant under the direction of the "
              "manufacturer's representative.", lab("commercial")),
            p("Operate the system in manual mode for not less than 48 hours before switching to automatic "
              "control.", lab("testing_piloting", "manual operation before automatic control", ">=", "48",
                              "hours")),
        )),
        Article("OPERATION AND MAINTENANCE DATA", (
            p("Provide operation and maintenance data for the membrane system in accordance with Section "
              "01 33 00.", lab("submittal")),
        )),
        Article("MANUFACTURER'S FIELD SERVICES", (
            p("Provide a manufacturer's process engineer on site during the performance test.", lab("commercial")),
            p("Field service reports shall be submitted within 7 days after each visit.",
              lab("submittal", "field service report submittal time", "<=", "7", "days")),
            p("Field services shall include the following:", kids=(
                p("Inspection of each membrane tank before cassettes are installed.", lab("commercial")),
                p("Inspection of the cassette installation and alignment.", lab("commercial")),
                p("Witnessing of the clean water test.", lab("commercial")),
                p("Calibration checks of the transmembrane pressure and turbidity instruments.", lab("commercial")),
                p("Verification of the PLC programming and alarm setpoints.", lab("commercial")),
                p("Supervision of the first maintenance clean.", lab("commercial")),
                p(TRAP1_TEXT, lab("commercial", "startup service technician time", ">=", "10", "working days",
                                  trap=1)),
                p("Assistance with the performance test and the test report.", lab("commercial")),
            )),
        )),
        Article("TRAINING", (
            p("Provide not less than 16 hours of operator training on the membrane system in two sessions.",
              lab("commercial", "membrane operator training", ">=", "16", "hours")),
            p("Training shall cover normal operation, cleaning procedures, membrane integrity testing, and "
              "troubleshooting.", lab("commercial")),
            p("Training sessions shall be video recorded and the recordings given to the Owner.",
              lab("commercial")),
        )),
        Article("SPARE MODULE STORAGE", (
            p("Spare membrane modules should be stored in the original shipping containers.",
              lab("material", m=False)),
        )),
    ),
), relevant=True)


# --- Irrelevant sections (realistic filler, no labels) ------------------------------------------

@dataclass(frozen=True)
class FillerSpec:
    number: str
    title: str
    refs: tuple[str, ...]
    part1: tuple[tuple[str, tuple[str, ...]], ...]
    part2: tuple[tuple[str, tuple[str, ...]], ...]
    part3: tuple[tuple[str, tuple[str, ...]], ...]
    items: tuple[str, ...]  # things the {item} slot cycles through
    pages: int  # rough target, in pages of text


CONCRETE = FillerSpec(
    "03 30 00", "CAST-IN-PLACE CONCRETE",
    ("ACI 117 - Specification for Tolerances for Concrete Construction and Materials.",
     "ACI 301 - Specifications for Concrete Construction.",
     "ACI 305.1 - Specification for Hot Weather Concreting.",
     "ACI 306.1 - Standard Specification for Cold Weather Concreting.",
     "ACI 309R - Guide for Consolidation of Concrete.",
     "ACI 318 - Building Code Requirements for Structural Concrete.",
     "ACI 350 - Code Requirements for Environmental Engineering Concrete Structures.",
     "ASTM A615/A615M - Deformed and Plain Carbon-Steel Bars for Concrete Reinforcement.",
     "ASTM C31/C31M - Making and Curing Concrete Test Specimens in the Field.",
     "ASTM C33/C33M - Concrete Aggregates.",
     "ASTM C39/C39M - Compressive Strength of Cylindrical Concrete Specimens.",
     "ASTM C94/C94M - Ready-Mixed Concrete.",
     "ASTM C143/C143M - Slump of Hydraulic-Cement Concrete.",
     "ASTM C150/C150M - Portland Cement.",
     "ASTM C231/C231M - Air Content of Freshly Mixed Concrete by the Pressure Method.",
     "ASTM C260/C260M - Air-Entraining Admixtures for Concrete.",
     "ASTM C309 - Liquid Membrane-Forming Compounds for Curing Concrete.",
     "ASTM C494/C494M - Chemical Admixtures for Concrete.",
     "ASTM C618 - Coal Fly Ash and Raw or Calcined Natural Pozzolan for Use in Concrete.",
     "ASTM C1107/C1107M - Packaged Dry, Hydraulic-Cement Grout (Nonshrink)."),
    (("SUMMARY", ("Section includes cast-in-place concrete for {item}, including formwork, reinforcement, "
                  "accessories, and curing.",)),
     ("SUBMITTALS", ("Submit concrete mix designs for each class of concrete at least {n:14-30} days before "
                     "the first placement.",
                     "Submit reinforcing steel shop drawings showing bar sizes, spacing, and splice locations for "
                     "{item}.",
                     "Submit mill certificates for reinforcing steel delivered for {item}.",
                     "Submit concrete placement records for {item} in accordance with Section 01 33 00.",
                     "Submit product data for admixtures, curing compounds, waterstops, and joint fillers.")),
     ("QUALITY ASSURANCE", ("The ready-mix supplier shall be certified by the National Ready Mixed Concrete "
                            "Association.",
                            "Testing shall be performed by an independent laboratory accredited for the tests "
                            "required.",
                            "Hold a preconstruction conference at least {n:7-21} days before the first placement "
                            "of concrete for {item}.")),
     ("DELIVERY, STORAGE, AND HANDLING", ("Store reinforcing steel on supports at least {n:6-12} inches above "
                                          "the ground.",
                                          "Protect admixtures from freezing and from temperatures above "
                                          "{n:90-110} degrees F."))),
    (("CEMENTITIOUS MATERIALS", ("Portland cement shall conform to ASTM C150, Type II.",
                                 "Fly ash shall conform to ASTM C618, Class F, and shall not exceed {n:15-25} "
                                 "percent of the cementitious materials by weight.")),
     ("AGGREGATES", ("Fine aggregate shall be natural sand conforming to ASTM C33.",
                     "Coarse aggregate for {item} shall be size No. {c:57|67} conforming to ASTM C33.",
                     "Aggregates shall be tested for alkali-silica reactivity and shall show an expansion of not "
                     "more than 0.{n:10-12} percent.")),
     ("ADMIXTURES", ("Air-entraining admixture shall conform to ASTM C260.",
                     "Water-reducing admixture shall conform to ASTM C494, Type A.",
                     "Calcium chloride and admixtures containing chlorides shall not be used.")),
     ("REINFORCING STEEL", ("Reinforcing bars shall be deformed bars conforming to ASTM A615, Grade 60.",
                            "Tie wire shall be annealed steel, 16 gauge or heavier.",
                            "Bar supports for {item} shall be plastic-tipped or stainless steel.")),
     ("WATERSTOPS AND JOINT MATERIALS", ("Waterstops shall be PVC, ribbed, {n:6-9} inches wide, with a center "
                                         "bulb.",
                                         "Joint filler shall be preformed, nonextruding, and resilient.")),
     ("CONCRETE MIXES", ("Class A concrete for {item} shall have a compressive strength of {c:4,000|4,500|5,000} psi at "
                         "28 days.",
                         "The water-cementitious materials ratio shall not exceed 0.{n:40-45}.",
                         "Air content shall be {n:5-6} percent, plus or minus 1.5 percent.",
                         "Slump shall be {n:3-5} inches, plus or minus 1 inch, before adding high range water "
                         "reducer."))),
    (("FORMWORK", ("Formwork for {item} shall be designed to support the full weight of wet concrete and "
                   "construction loads.",
                   "Form ties for {item} shall be the snap-off type with water stop washers.",
                   "Chamfer exposed corners of {item} three-quarter inch.",
                   "Do not remove forms from {item} until the concrete has reached {n:60-75} percent of its "
                   "specified strength.")),
     ("REINFORCEMENT PLACEMENT", ("Place reinforcement for {item} within the tolerances of ACI 117.",
                                  "Concrete cover over reinforcement in {item} shall be {n:2-3} inches unless "
                                  "otherwise indicated.",
                                  "Lap splices in {item} shall be Class B unless otherwise indicated.")),
     ("JOINTS", ("Locate construction joints in {item} as indicated on the Drawings.",
                 "Clean and roughen the surface of construction joints in {item} to an amplitude of one quarter "
                 "inch.",
                 "Install waterstops continuous through all construction joints in {item}.")),
     ("PLACING CONCRETE", ("Notify the Engineer at least {n:24-48} hours before placing concrete in {item}.",
                           "Do not drop concrete freely more than {n:4-6} feet when placing {item}.",
                           "Place concrete for {item} in layers not deeper than {n:18-24} inches.",
                           "Consolidate concrete in {item} with internal vibrators.")),
     ("HOT AND COLD WEATHER CONCRETING", ("Concrete temperature at placement in {item} shall not exceed "
                                          "{n:85-95} degrees F.",
                                          "Protect {item} from freezing for at least {n:5-7} days after "
                                          "placement.")),
     ("FINISHING", ("Finish exposed surfaces of {item} with a smooth form finish.",
                    "Floor surfaces in {item} shall be finished to a flatness of plus or minus one quarter inch "
                    "in 10 feet.")),
     ("CURING AND PROTECTION", ("Keep {item} continuously moist for at least {n:7-10} days after placement.",
                                "Curing compound shall not be used on surfaces that will receive coatings.")),
     ("FIELD QUALITY CONTROL", ("Make one set of {n:4-5} cylinders for each {n:50-100} cubic yards of concrete "
                                "placed in {item}.",
                                "Perform slump and air content tests on each truck used for {item}.",
                                "Concrete in {item} that fails to meet the specified strength shall be cored and "
                                "evaluated at the Contractor's expense.")),
     ("REPAIR OF DEFECTS", ("Repair honeycomb and surface defects in {item} within {n:24-48} hours after form "
                            "removal.",
                            "Fill form tie holes in {item} with nonshrink grout."))),
    ("footings", "base slabs", "tank walls", "elevated slabs", "columns", "equipment pads", "channel walls",
     "wet wells", "pipe encasements", "stair landings", "trench drains", "valve vaults", "duct banks",
     "retaining walls", "grade beams", "manholes", "thrust blocks", "sidewalks", "curbs and gutters",
     "generator pads", "transformer pads", "tank roof slabs", "baffle walls", "weir walls", "sumps", "ramps",
     "light pole bases", "chemical containment curbs", "pipe supports", "bollard footings", "stair treads"),
    pages=43,
)

ELECTRICAL = FillerSpec(
    "26 05 00", "COMMON WORK RESULTS FOR ELECTRICAL",
    ("ANSI C80.1 - Electrical Rigid Steel Conduit.",
     "IEEE C2 - National Electrical Safety Code.",
     "NECA 1 - Standard for Good Workmanship in Electrical Construction.",
     "NEMA 250 - Enclosures for Electrical Equipment (1000 Volts Maximum).",
     "NEMA ICS 1 - Industrial Control and Systems: General Requirements.",
     "NEMA RN 1 - Polyvinyl-Chloride (PVC) Externally Coated Galvanized Rigid Steel Conduit.",
     "NETA ATS - Acceptance Testing Specifications for Electrical Power Equipment and Systems.",
     "NFPA 70 - National Electrical Code.",
     "NFPA 70E - Standard for Electrical Safety in the Workplace.",
     "UL 44 - Thermoset-Insulated Wires and Cables.",
     "UL 83 - Thermoplastic-Insulated Wires and Cables.",
     "UL 467 - Grounding and Bonding Equipment.",
     "UL 486A-486B - Wire Connectors.",
     "UL 514A - Metallic Outlet Boxes.",
     "UL 651 - Schedule 40, 80, Type EB and A Rigid PVC Conduit and Fittings.",
     "UL 797 - Electrical Metallic Tubing - Steel."),
    (("SUMMARY", ("Section includes basic electrical materials and methods for {item}.",)),
     ("DEFINITIONS", ("Wet locations: areas below grade, outdoors, and areas subject to washdown, including "
                      "{item}.",
                      "Corrosive locations: chemical storage rooms, headworks areas, and {item}.")),
     ("SUBMITTALS", ("Submit product data for raceways, boxes, conductors, and supports used in {item}.",
                     "Submit field test reports within {n:7-14} days after testing of circuits serving {item}.",
                     "Submit record drawings showing the routing of conduits serving {item}.")),
     ("QUALITY ASSURANCE", ("Electrical work shall be performed by licensed electricians.",
                            "Materials shall be listed and labeled by a nationally recognized testing "
                            "laboratory.")),
     ("COORDINATION", ("Coordinate the location of conduits and boxes in {item} with structural and mechanical "
                       "work.",
                       "Coordinate equipment connections in {item} with the approved shop drawings."))),
    (("RACEWAYS", ("Rigid galvanized steel conduit shall conform to ANSI C80.1 and UL 6.",
                   "PVC-coated rigid steel conduit shall have a 40 mil PVC exterior coating and a 2 mil urethane "
                   "interior coating.",
                   "Rigid nonmetallic conduit for {item} shall be Schedule 80 PVC conforming to UL 651.",
                   "Liquidtight flexible metal conduit shall be used for final connections to motors in {item}, "
                   "in lengths not exceeding {n:3-6} feet.")),
     ("CONDUCTORS", ("Power conductors shall be copper, Type XHHW-2, rated 600 volts.",
                     "Conductors for {item} shall be not smaller than No. {n:10-12} AWG.",
                     "Instrumentation cable shall be twisted shielded pairs, No. 16 AWG, with an overall "
                     "jacket.")),
     ("BOXES AND ENCLOSURES", ("Boxes in {item} shall be cast metal with threaded hubs.",
                               "Enclosures in wet locations shall be NEMA 4X stainless steel.",
                               "Enclosures in dry indoor locations shall be NEMA 12.")),
     ("SUPPORTS", ("Supports in {item} shall be Type 316 stainless steel channel with stainless steel "
                   "hardware.",
                   "Space conduit supports in {item} not more than {n:6-10} feet apart.")),
     ("IDENTIFICATION", ("Nameplates for equipment in {item} shall be engraved laminated plastic with "
                         "letters at least one quarter inch high.",
                         "Wire markers shall be heat-shrink sleeves printed with the circuit number.")),
     ("GROUNDING MATERIALS", ("Ground rods shall be copper-clad steel, {n:8-10} feet long and three-quarter inch "
                              "in diameter.",
                              "Grounding conductors shall be bare stranded copper."))),
    (("GENERAL INSTALLATION", ("Install electrical equipment in {item} in accordance with NECA 1.",
                               "Provide working clearances in {item} as required by NFPA 70.",
                               "Seal openings in walls of {item} where conduits pass through.")),
     ("RACEWAY INSTALLATION", ("Conduit in {item} shall be installed exposed unless otherwise indicated.",
                               "Install conduit in {item} parallel or perpendicular to building lines.",
                               "Provide expansion fittings where conduits in {item} cross structural expansion "
                               "joints.",
                               "Conduits in {item} shall not be smaller than three-quarter inch trade size.",
                               "Bury underground conduits for {item} not less than {n:24-36} inches below "
                               "finished grade.")),
     ("CONDUCTOR INSTALLATION", ("Pull conductors for {item} with a lubricant approved by the cable "
                                 "manufacturer.",
                                 "Do not splice conductors in conduit serving {item}.",
                                 "Leave at least {n:6-12} inches of slack at each box in {item}.")),
     ("GROUNDING", ("Bond metallic raceways and enclosures in {item} to the grounding system.",
                    "The resistance of the grounding electrode system for {item} shall not exceed {n:5-10} "
                    "ohms.")),
     ("FIELD TESTING", ("Test the insulation resistance of feeders serving {item} at 1,000 volts DC for one "
                        "minute.",
                        "Insulation resistance of circuits serving {item} shall be not less than {n:50-100} "
                        "megohms.",
                        "Test ground fault protection for {item} in accordance with NETA ATS.",
                        "Correct deficiencies found during testing of {item} and retest at no cost to the "
                        "Owner.")),
     ("CLEANING", ("Remove dirt and debris from enclosures in {item} before energizing.",
                   "Touch up damaged finishes on electrical equipment in {item}."))),
    ("the headworks building", "the blower building", "the operations building", "the chemical building",
     "the solids handling building", "the influent pump station", "the effluent pump station",
     "the generator building", "outdoor process areas", "the laboratory", "yard lighting circuits",
     "the plant water system", "the odor control area", "site security systems", "the process building",
     "the primary settling tanks", "the aerobic basins", "the equalization basin", "the disinfection building",
     "the maintenance shop", "the septage receiving station", "the sludge storage tanks", "the gatehouse",
     "the fire alarm system", "the telephone and data system", "the outfall structure", "the scum pump station",
     "the grit removal area", "the motor control center room", "the electrical building"),
    pages=43,
)

EARTHWORK = FillerSpec(
    "31 00 00", "EARTHWORK",
    ("AASHTO T99 - Moisture-Density Relations of Soils Using a 2.5-kg Rammer and a 305-mm Drop.",
     "AASHTO T180 - Moisture-Density Relations of Soils Using a 4.54-kg Rammer and a 457-mm Drop.",
     "ASTM C136/C136M - Sieve Analysis of Fine and Coarse Aggregates.",
     "ASTM D698 - Laboratory Compaction Characteristics of Soil Using Standard Effort.",
     "ASTM D1557 - Laboratory Compaction Characteristics of Soil Using Modified Effort.",
     "ASTM D2487 - Classification of Soils for Engineering Purposes.",
     "ASTM D4318 - Liquid Limit, Plastic Limit, and Plasticity Index of Soils.",
     "ASTM D6938 - In-Place Density and Water Content of Soil by Nuclear Methods.",
     "OSHA 29 CFR 1926 Subpart P - Excavations."),
    (("SUMMARY", ("Section includes excavation, dewatering, backfill, and compaction for {item}.",)),
     ("DEFINITIONS", ("Structural fill: fill placed under or around {item} to support loads.",
                      "Unsuitable material: organic soil, frozen material, debris, and soil with more than "
                      "{n:5-10} percent organic content.")),
     ("SUBMITTALS", ("Submit gradation test results for each fill material used at {item}.",
                     "Submit a dewatering plan for {item} sealed by a professional engineer.",
                     "Submit an excavation support plan for {item} at least {n:14-21} days before excavation.")),
     ("PROJECT CONDITIONS", ("Protect existing utilities near {item} from damage.",
                             "Groundwater was encountered at depths of {n:6-12} feet below grade in the borings "
                             "near {item}."))),
    (("SOIL MATERIALS", ("Structural fill for {item} shall be well graded sand and gravel with not more than "
                         "{n:8-12} percent passing the No. 200 sieve.",
                         "Common fill shall be free of organic matter, debris, and stones larger than {n:4-6} "
                         "inches.",
                         "Pipe bedding for {item} shall be crushed stone, three-quarter inch nominal size.")),
     ("GEOTEXTILES", ("Separation geotextile beneath {item} shall be nonwoven polypropylene with a grab "
                      "strength of not less than {n:160-200} pounds.",)),
     ("WARNING TAPE", ("Warning tape over utilities at {item} shall be polyethylene, {n:4-6} inches wide, with "
                       "a metallic core.",))),
    (("SITE PREPARATION", ("Clear and grub the area of {item} before excavation.",
                           "Strip topsoil from the area of {item} and stockpile it for reuse.",
                           "Proof roll the subgrade at {item} with a loaded dump truck in the presence of the "
                           "Engineer.")),
     ("DEWATERING", ("Lower groundwater at {item} at least {n:2-3} feet below the bottom of excavation.",
                     "Discharge water from dewatering at {item} through a sediment control device.",
                     "Maintain dewatering at {item} until backfill reaches the original groundwater level.")),
     ("EXCAVATION", ("Excavate {item} to the lines and grades indicated on the Drawings.",
                     "Remove unsuitable material below {item} and replace it with structural fill.",
                     "Do not excavate below {item} more than {n:2-4} inches below the indicated grade.")),
     ("EXCAVATION SUPPORT", ("Provide excavation support at {item} in accordance with OSHA 29 CFR 1926 Subpart "
                             "P.",
                             "Excavation support at {item} shall be removed as backfill is placed.")),
     ("BACKFILL", ("Place backfill around {item} in lifts not exceeding {n:8-12} inches loose thickness.",
                   "Do not place backfill against walls of {item} until the concrete has reached its "
                   "specified strength.",
                   "Place backfill on both sides of {item} at the same time to keep the difference in level "
                   "below {n:12-24} inches.")),
     ("COMPACTION", ("Compact structural fill under {item} to {n:95-98} percent of maximum dry density per "
                     "ASTM D1557.",
                     "Compact common fill at {item} to {n:90-92} percent of maximum dry density per ASTM D1557.",
                     "Moisture content of fill at {item} shall be within 2 percent of optimum during "
                     "compaction.")),
     ("FIELD QUALITY CONTROL", ("Perform one density test for each {c:2,000|2,500|5,000} square feet of each lift at "
                                "{item}.",
                                "Retest areas at {item} that fail compaction after rework.")),
     ("DISPOSAL OF MATERIALS", ("Dispose of excess excavated material from {item} off site.",
                                "Haul routes from {item} shall be kept clean of mud and debris."))),
    ("the headworks building", "the process building", "the blower building", "the primary settling tanks",
     "the aerobic basins", "the equalization basin", "the operations building", "the chemical building",
     "yard piping", "the outfall pipe", "site roads", "the electrical duct banks", "the stormwater basin",
     "the influent sewer", "the solids handling building", "the disinfection building", "the maintenance shop",
     "the septage receiving station", "the sludge storage tanks", "the gatehouse", "the parking area",
     "the generator pad", "the chemical containment area", "the plant drain pump station", "the scum pump station",
     "the grit removal area", "the force main", "the water main", "the fence line", "the laboratory"),
    pages=43,
)

FILLERS = (CONCRETE, ELECTRICAL, EARTHWORK)


def _fill(template: str, rng: random.Random, item: str) -> str:
    out = template.replace("{item}", item)
    while "{c:" in out:
        start = out.index("{c:")
        end = out.index("}", start)
        out = out[:start] + rng.choice(out[start + 3:end].split("|")) + out[end + 1:]
    while "{n:" in out:
        start = out.index("{n:")
        end = out.index("}", start)
        low, high = (int(x) for x in out[start + 3:end].split("-"))
        out = out[:start] + str(rng.randint(low, high)) + out[end + 1:]
    return out


def filler_section(spec: FillerSpec, rng: random.Random) -> SpecSection:
    """A realistic but unlabeled section of roughly spec.pages pages.

    Volume comes from repeating item-specific articles ("FORMWORK - TANK WALLS"), the way real
    specifications break execution requirements out by element.
    """
    target_words = spec.pages * 330
    items = list(spec.items)

    def articles(topics: tuple[tuple[str, tuple[str, ...]], ...], rounds: int) -> tuple[Article, ...]:
        out = []
        for title, templates in topics:
            if rounds == 1 or not any("{item}" in t for t in templates):
                out.append(Article(title, tuple(p(_fill(t, rng, rng.choice(items))) for t in templates)))
                continue
            for r in range(rounds):
                item = items[r % len(items)]
                out.append(Article(f"{title} - {item.upper()}", tuple(p(_fill(t, rng, item)) for t in templates)))
        return tuple(out)

    def words(sec: SpecSection) -> int:
        return sum(len(it.text.split()) for part in sec.parts for a in part for it in a.body
                   if isinstance(it, P))

    refs = Article("REFERENCES", (_refs(*spec.refs),))
    rounds = 1
    while True:
        p1 = articles(spec.part1[:1], 1) + (refs,) + articles(spec.part1[1:], 1)
        sec = SpecSection(spec.number, spec.title, (p1, articles(spec.part2, max(1, rounds // 2)),
                                                    articles(spec.part3, rounds)), relevant=False)
        if words(sec) >= target_words or rounds >= len(items):
            return sec
        rounds += 1


# --- Permit ------------------------------------------------------------------------------------

PERMIT_TITLE = "NPDES DISCHARGE PERMIT EXCERPT"
PERMIT_TABLE = Table(
    ("Parameter", "Monthly Average", "Weekly Average", "Units"),
    (("Total Phosphorus", "0.1", "--", "mg/L"),
     ("Ammonia Nitrogen (as N)", "2.0", "3.0", "mg/L"),
     ("Biochemical Oxygen Demand (BOD5)", "30", "45", "mg/L"),
     ("Total Suspended Solids (TSS)", "30", "45", "mg/L")),
)
PERMIT_LIMITS = [
    Limit(0, "monthly_avg", 0.1),
    Limit(1, "monthly_avg", 2.0), Limit(1, "weekly_avg", 3.0),
    Limit(2, "monthly_avg", 30.0), Limit(2, "weekly_avg", 45.0),
    Limit(3, "monthly_avg", 30.0), Limit(3, "weekly_avg", 45.0),
]

PERMIT_PAGES: list[list[str | Table]] = [
    [PERMIT_TITLE,
     "Lakeview Department of Environmental Conservation",
     "Permit No. LV0100421",
     "Permittee: Town of Lakeview, Lakeview Wastewater Treatment Plant",
     "Receiving water: Lake Merrow",
     "Effective date: July 1, 2026. Expiration date: June 30, 2031.",
     FICTION,
     "In compliance with the state water pollution control law and the federal Clean Water Act, the Town of "
     "Lakeview is authorized to discharge treated wastewater from the Lakeview Wastewater Treatment Plant to "
     "Lake Merrow in accordance with the effluent limitations, monitoring requirements, and other conditions "
     "of this permit.",
     "This excerpt reproduces Part I of the permit. Part II, standard conditions, is incorporated by "
     "reference and is not reproduced here.",
     "The design flow of the facility is 2.0 million gallons per day as an annual average."],
    ["PART I. EFFLUENT LIMITATIONS AND MONITORING REQUIREMENTS",
     "A. During the period beginning on the effective date and lasting through expiration, the permittee is "
     "authorized to discharge treated wastewater from outfall 001. The discharge is limited and monitored by "
     "the permittee as specified in Table 1.",
     "B. Samples taken in compliance with the monitoring requirements are taken at the effluent sampling "
     "station after final treatment and before discharge to the receiving water.",
     "C. The discharge does not cause a visible sheen, foam, or floating solids in the receiving water.",
     "D. The new total phosphorus limit takes effect on July 1, 2029, at the end of the compliance schedule "
     "in Part I.F. Until then the permittee reports total phosphorus monthly without a numeric limit.",
     "E. Monthly average limits apply to the arithmetic mean of all samples collected in a calendar month. "
     "Weekly average limits apply to the arithmetic mean of all samples collected in a calendar week."],
    ["Table 1. Effluent Limitations, Outfall 001", PERMIT_TABLE,
     "Limits apply year round. Report the results of all analyses on the monthly discharge monitoring report."],
    ["F. MONITORING REQUIREMENTS",
     "1. Flow is measured continuously and recorded daily.",
     "2. Total phosphorus, BOD5, and TSS are sampled three times per week as 24 hour flow proportional "
     "composite samples.",
     "3. Ammonia nitrogen is sampled weekly as a 24 hour composite sample.",
     "4. pH and total residual chlorine are measured daily by grab sample."],
    ["G. COMPLIANCE SCHEDULE FOR TOTAL PHOSPHORUS",
     "1. Complete the facility plan for phosphorus removal by July 1, 2026.",
     "2. Begin construction of the phosphorus removal upgrade by July 1, 2027.",
     "3. Achieve compliance with the total phosphorus limit of 0.1 mg/L by July 1, 2029.",
     "4. Submit a written progress report every six months until compliance is achieved."],
]


# --- Addendum ----------------------------------------------------------------------------------

TRAP7_ITEM = ("Section 46 61 00 Membrane Filtration Equipment: Delete paragraph 2.04.B and replace with the "
              "following: " + TRAP7_NEW)
SCREEN_NEW = "Screen panels shall have perforations of 2 mm diameter."
ADDENDUM: list[str | P] = [
    "ADDENDUM NO. 1",
    "Town of Lakeview, Phase 2 Upgrade: Membrane Filtration, Band Screen, and Clarifier Equipment Preselection",
    "RFP No. 2026-07. Date of Addendum: November 2, 2026.",
    FICTION,
    "This Addendum modifies the Request for Proposals and the Technical Specifications as described below. "
    "All other terms remain unchanged.",
    "CHANGES TO THE REQUEST FOR PROPOSALS",
    p("Revise the proposal due date to December 15, 2026 at 2:00 PM."),
    "CHANGES TO THE TECHNICAL SPECIFICATIONS",
    p(TRAP7_ITEM),
    p("Section 46 21 00 Band Screens: Revise paragraph 2.01.C to read: " + SCREEN_NEW),
    "QUESTIONS AND ANSWERS",
    "Question: Will the Owner accept a pilot unit that uses one full scale membrane module instead of a full "
    "cassette?",
    "Answer: Yes, provided the module is the same model proposed for the full scale system.",
    "END OF ADDENDUM NO. 1",
]
ADDENDUM_DEADLINE = "Proposal due date revised to December 15, 2026 at 2:00 PM"
ADDENDUM_LABELS = {
    8: ("46 61 00", "2.04.B", TRAP7_NEW,
        lab("warranty", "membrane module warranty", "=", "7", "years", trap=7)),
    9: ("46 21 00", "2.01.C", SCREEN_NEW, lab("performance", "screen perforation diameter", "=", "2", "mm")),
}
ADDENDUM_CHANGES = [("revise_date", None, None), ("replace_paragraph", "46 61 00", "2.04.B"),
                    ("replace_paragraph", "46 21 00", "2.01.C")]

TRAPS = [
    Trap(1, "Mandatory field-service requirement buried at 46 61 00 paragraph 3.08.C.7, in the last quarter "
            "of the section"),
    Trap(2, "O&M manual requirement in 01 33 00 paragraph 1.06.B, reached through the reference in 46 61 00 "
            "paragraph 1.05.A"),
    Trap(3, "Requirement in a design-criteria table row after a page break: Maximum transmembrane pressure "
            "12 psi"),
    Trap(4, "Named competitor Brightwater Systems Model BS-300 with an or-equal clause at 46 21 00 "
            "paragraph 2.01.A"),
    Trap(5, "Effluent total phosphorus of 0.1 mg/L where the product literature supports below 0.2 mg/L; "
            "expected needs_engineer"),
    Trap(6, "A 'should' statement at 46 43 00 paragraph 2.03.C that must not be marked mandatory"),
    Trap(7, "Addendum 1 replaces 46 61 00 paragraph 2.04.B: the 5-year module warranty becomes 7 years"),
]

SPECS_COVER = [
    "LAKEVIEW WASTEWATER TREATMENT PLANT PHASE 2 UPGRADE",
    "TECHNICAL SPECIFICATIONS",
    "MEMBRANE FILTRATION, BAND SCREEN, AND CLARIFIER EQUIPMENT PRESELECTION",
    "Town of Lakeview",
    "Harbor & Pine Engineers",
    "October 2026",
    FICTION,
]


def spec_sections() -> list[SpecSection]:
    rng = random.Random(1729)
    concrete, electrical, earthwork = (filler_section(f, rng) for f in FILLERS)
    return [S013300, concrete, electrical, earthwork, S462100, S464300, S466100]
