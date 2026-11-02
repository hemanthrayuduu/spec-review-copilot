"""Expected match status for every Cedar Falls requirement (the test package, written after the Phase 4 freeze).

Key: (section number or "-", paragraph path, a prefix of the source text that is unique within that path).
Value: (expected status, one-line reason naming the capability ids it rests on, or saying why none settles it).

Written from the status definitions in docs/PROJECT_SPEC.md section 9 and from data/knowledge/capabilities.csv, by the
same builder who wrote the package, before any pipeline run and without any model output:
- comply, comply_with_clarification, and deviation rest on guaranteed or typical capability rows only.
- Claims (BIO-01 to BIO-04, AER-01, SCR-06, SCR-07, CLR-01, MBR-13, MBR-19), brochure pages, and past exceptions never
  settle a status. A nutrient limit that only claims speak to is needs_engineer.
- not_applicable means the text puts no obligation on the manufacturer's equipment, services, or terms: bid
  procedure, bid forms, design inputs, the owner's own steps, and work for the installing contractor.
- needs_engineer means no guaranteed or typical row settles the text, or a row settles only part of it.
Section 46 43 13 here is the reissued section from Addendum 3 (doc addendum_3); the version bound in the spec book is
superseded and carries no label.
"""

STATUS: dict[tuple[str, str, str], tuple[str, str]] = {
    # --- Request for Proposals ---
    ('3', '3.1', 'The Supplier shall furnish two traveling band'):
        ('comply', 'SCR-03 (band screens), CLR-09 (clarifier mechanisms), and MBR-20 (SiC MBR) show that all three product lines are offered'),
    ('3', '3.2', 'The Supplier shall provide engineering, fabric'):
        ('needs_engineer', 'GEN-09, GEN-11, and GEN-12 cover delivery, installation check, startup, and training; no row covers performance testing'),
    ('3', '3.3', 'Equipment shall be delivered to the site within'):
        ('comply', 'GEN-09: ships 20 to 26 weeks after approved shop drawings'),
    ('3', '3.4', 'Shop drawings shall be submitted within 12 week'):
        ('comply', 'GEN-08: shop drawings 8 weeks after the purchase order'),
    ('3', '3.5', 'The Supplier may offer a factory-assembled cass'):
        ('not_applicable', 'a permission, not an obligation'),
    ('4', '4.2', 'Attendance at the pre-proposal meeting'):
        ('not_applicable', 'bid-procedure instruction (mandatory meeting) that the brief tracks'),
    ('4', '4.3', 'Proposals shall be submitted electronically'):
        ('not_applicable', 'bid-procedure instruction (proposal delivery)'),
    ('4', '4.3', 'as one printed original in a sealed envelope'):
        ('not_applicable', 'bid-procedure instruction (proposal delivery)'),
    ('4', '4.4', 'Written questions about this Request for Propo'):
        ('not_applicable', 'bid-procedure deadline that the brief tracks'),
    ('5', '5.1', 'The Supplier shall demonstrate at least four ('):
        ('needs_engineer', 'GEN-14 lists at least five SiC MBR plants but not their design flows or whether they are municipal'),
    ('5', '5.2', 'Each installation shall be listed on Attachmen'):
        ('not_applicable', 'bid form instruction (Attachment C)'),
    ('5', '5.3', 'The Supplier shall maintain a service center a'):
        ('comply', 'GEN-13: technician on site within 72 hours'),
    ('5', '5.4', 'The Supplier should identify the technicians wh'):
        ('needs_engineer', 'no row names the technicians who perform startup service'),
    ('6', '6.1', 'The two highest scoring Proposers shall each c'):
        ('deviation', 'MBR-47: pilot unit available for 60 to 120 days, not 150'),
    ('6', '6.2', 'The pilot unit shall be operated on the mixed'):
        ('needs_engineer', 'MBR-47 gives a containerized pilot unit but does not say what liquor it runs on'),
    ('6', '6.3', 'During the final 30 days of operation, the pil'):
        ('needs_engineer', 'nitrogen has only claims (BIO-02, BIO-03, BIO-04, AER-01); no guarantee'),
    ('6', '6.5', 'The Supplier shall submit a pilot test report w'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('6', '6.6', 'The cost of pilot testing shall be included in'):
        ('comply_with_clarification', 'MBR-47 bills pilot rental and support separately; the price must include them'),
    ('7', '7.1', 'The Supplier shall warrant all equipment again'):
        ('comply_with_clarification', 'GEN-01: 12 months from startup or 18 months from shipment, whichever comes first; the bid must state the shipment limit'),
    ('7', '7.2', 'The Supplier shall provide a process performan'):
        ('comply_with_clarification', 'GEN-02: process performance is guaranteed only in a written process performance warranty issued for the project'),
    ('7', '7.3', 'If the performance guarantee is not met, the S'):
        ('needs_engineer', 'no row covers the remedy for a missed guarantee; GEN-02 says only that the guarantee is written'),
    ('8', '8.1', 'Proposal prices shall remain valid for 90 days'):
        ('comply', 'GEN-07: prices valid 90 days'),
    ('8', '8.2', 'The selected Supplier shall furnish a performa'):
        ('comply_with_clarification', 'GEN-05: performance and payment bonds at 100 percent of contract value, at added cost'),
    ('8', '8.3', 'Payment shall be made monthly on the percenta'):
        ('deviation', 'GEN-03: 10 percent with order, 80 on delivery, 10 on startup; no monthly progress payments or retainage'),
    ('8', '8.4', 'The Supplier shall maintain commercial general'):
        ('comply', 'GEN-06: $2,000,000 per occurrence'),
    ('8', '8.5', 'The Supplier shall name the Owner and the Engin'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('9', '9.4', 'Proposers shall state the guaranteed energy, ch'):
        ('needs_engineer', 'GEN-02 limits guarantees to a written process performance warranty; no row guarantees energy, chemical use, or replacement interval'),
    ('9', '9.7', 'Proposers should visit the existing plant befo'):
        ('not_applicable', 'bid-procedure recommendation'),
    ('10', '10.1', 'The proposal shall include a completed Attach'):
        ('not_applicable', 'bid form instruction (Attachment A)'),
    ('10', '10.2', 'The proposal shall include a completed Attach'):
        ('not_applicable', 'bid form instruction (Attachment B)'),
    ('10', '10.3', 'The proposal shall include a completed Attach'):
        ('not_applicable', 'bid form instruction (Attachment C)'),
    ('10', '10.4', 'Values entered on the Technical Data Forms sh'):
        ('needs_engineer', 'GEN-02 limits guarantees to a written warranty; typical rows (MBR-23, MBR-44) cannot be entered as guaranteed values'),
    # --- 00 21 13 Instructions to Proposers ---
    ('00 21 13', '2.1', 'Proposers shall report any conflict, error'):
        ('not_applicable', 'bid-procedure instruction'),
    ('00 21 13', '3.2', 'Proposers shall acknowledge receipt of each a'):
        ('not_applicable', 'bid-procedure instruction (Attachment A)'),
    ('00 21 13', '4.2', 'Requests for approval of an equal product sh'):
        ('not_applicable', 'bid-procedure deadline that the brief tracks'),
    ('00 21 13', '4.3', 'Each request shall include the manufacturer'):
        ('not_applicable', 'bid-procedure instruction (contents of an approved equal request)'),
    ('00 21 13', '5.1', 'Each proposal shall be bound and tabbed in'):
        ('not_applicable', 'bid-procedure instruction'),
    # --- 00 73 00 Supplementary Conditions ---
    ('00 73 00', '1.1', 'The Supplier shall pay the Owner liquidated'):
        ('deviation', 'GEN-04: up to $500 per day, capped at 5 percent of the contract price'),
    ('00 73 00', '2.1', 'The Supplier shall ship equipment to arrive'):
        ('needs_engineer', 'GEN-09 gives shipping time after shop drawing approval, not a delivery window before installation'),
    ('00 73 00', '2.2', 'The Supplier shall insure all equipment in tr'):
        ('needs_engineer', 'GEN-06 covers liability insurance, not insurance of equipment in transit'),
    ('00 73 00', '3.1', 'The warranty period for all equipment shall b'):
        ('deviation', 'GEN-01: warranty runs from startup or shipment, whichever comes first, not from substantial completion'),
    ('00 73 00', '3.2', 'Defective equipment shall be repaired or repla'):
        ('needs_engineer', 'GEN-01 sets the warranty period; no row says who pays removal and reinstallation'),
    # --- 01 33 00 Submittal Procedures ---
    ('01 33 00', '1.03.A', 'The Supplier shall submit a submittal schedule'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.03.B', "Allow 28 days for the Engineer's review"):
        ('not_applicable', "the Engineer's review period"),
    ('01 33 00', '1.04.A', 'Each submittal shall be transmitted electronic'):
        ('comply', 'GEN-16: submittals are searchable PDF files'),
    ('01 33 00', '1.04.B', 'Each submittal shall be identified by specific'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.04.D', 'Submittals should be organized in the order o'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.05.A', 'Shop drawings shall show dimensions, material'):
        ('needs_engineer', 'GEN-08 gives timing, not shop drawing contents'),
    ('01 33 00', '1.05.B', 'Product data shall be marked to show the spec'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.06.A', 'Operation and maintenance manuals shall be sub'):
        ('comply', 'GEN-10: manuals 4 weeks before startup, earlier than the 3 weeks required'),
    ('01 33 00', '1.06.B', 'Manuals shall include equipment descriptions'):
        ('needs_engineer', 'GEN-10 and GEN-18 cover delivery and spare parts, not the full manual contents'),
    ('01 33 00', '1.07.A', 'The certificate of proper installation shall'):
        ('needs_engineer', 'GEN-11 covers the installation check, but no row covers a signed certificate or its timing'),
    ('01 33 00', '1.08.A', 'Resubmittals shall identify every change made'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    # --- 01 60 00 Product Requirements ---
    ('01 60 00', '1.02.A', 'All iron and steel products, manufactured pro'):
        ('comply_with_clarification', 'GEN-15: BABA compliant supply when specified, at added cost'),
    ('01 60 00', '1.02.B', 'The Supplier shall submit a BABA compliance c'):
        ('needs_engineer', 'GEN-15 covers BABA compliant supply, not a certification with each invoice'),
    ('01 60 00', '2.01.A', 'Products shall be new, of current manufacture'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    # --- 46 21 23 Traveling Band Fine Screens ---
    ('46 21 23', '1.03.A', 'Each screen shall be designed for a peak hour'):
        ('comply', 'SCR-03: CF100 handles 50 to 1,500 L/s (1 to 40 mgd)'),
    ('46 21 23', '1.05.A', 'The screen manufacturer shall have at least 1'):
        ('needs_engineer', 'GEN-14 has band screen reference lists but gives no count of installations'),
    ('46 21 23', '1.06.A', 'The band screens shall be warranted against d'):
        ('deviation', 'GEN-01: 12 months from startup or 18 from shipment, not 36 months'),
    ('46 21 23', '2.01.A', 'Band screens shall be Tessaly Screen Systems'):
        ('comply_with_clarification', 'GEN-19: offered as an approved equal, request filed before the deadline'),
    ('46 21 23', '2.02.A', 'Screen frames shall be Type 304L stainless st'):
        ('comply', 'SCR-08: standard Type 304L frame with polypropylene panels'),
    ('46 21 23', '2.02.B', 'Screen panels shall have round perforations of'):
        ('comply', 'SCR-01 and SCR-02: apertures from 2 mm, with 3 mm among the panel options'),
    ('46 21 23', '2.02.C', 'Fasteners and anchor bolts shall be Type 316'):
        ('comply', 'SCR-15: all screen fasteners are Type 316'),
    ('46 21 23', '2.02.D', 'Headloss through a clean screen shall not exc'):
        ('needs_engineer', 'SCR-05 gives typical headloss of 250 to 400 mm (10 to 16 in); meeting 12 in is a sizing question'),
    ('46 21 23', '2.03.A', 'The spray wash water demand of each screen s'):
        ('comply', 'SCR-11: 20 to 30 gpm at 60 psi per screen'),
    ('46 21 23', '2.03.B', 'Spray nozzles should be of the quick disconn'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 23', '2.04.A', 'Screenings discharged from each screen shall'):
        ('deviation', 'SCR-17: screenings discharge at 15 to 20 percent dry solids, below 25 percent'),
    ('46 21 23', '2.04.B', 'Provide one screenings washer compactor for e'):
        ('needs_engineer', 'no row covers a washer compactor; SCR-17 describes screenings without one'),
    ('46 21 23', '2.05.A', 'Each screen shall be furnished with a local c'):
        ('comply', 'SCR-16: NEMA 4X stainless steel control panel'),
    ('46 21 23', '2.05.B', 'Screen drive motors shall be 460 volts, 3 ph'):
        ('comply', 'SCR-12: 460 V, 3 phase, 60 Hz, TEFC'),
    ('46 21 23', '3.02.A', 'After installation, each screen shall be ope'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 23', '3.03.A', "Provide a manufacturer's representative on s"):
        ('comply', 'GEN-11: up to 5 days on site per equipment type'),
    ('46 21 23', '3.03.B', 'Provide not less than 4 hours of operator tra'):
        ('comply', 'GEN-12: one 8-hour session per equipment type'),
    # --- 46 61 23 Submerged Membrane Bioreactor Equipment ---
    ('46 61 23', '1.05.M', 'The membrane system shall be designed to acc'):
        ('not_applicable', 'design input'),
    ('46 61 23', '1.06.A', 'Submit shop drawings showing the cassette arr'):
        ('needs_engineer', 'GEN-08 gives timing, not shop drawing contents'),
    ('46 61 23', '1.06.B', "Submit the membrane manufacturer's written w"):
        ('comply', 'MBR-32: written membrane warranty'),
    ('46 61 23', '1.06.C', 'Submit control system software documentation'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 23', '1.06.D', 'Submit the certificate of proper installatio'):
        ('needs_engineer', 'GEN-11 covers the installation check, but no row covers a signed certificate'),
    ('46 61 23', '1.07.A', 'Membrane modules shall be manufactured at a f'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 23', '1.07.B', 'Membrane modules shall have NSF/ANSI 61 drin'):
        ('comply', 'MBR-14: NSF 61 drinking water approval'),
    ('46 61 23', '1.08.A', 'Membrane modules shall tolerate storage at te'):
        ('comply', 'MBR-37: dry SiC modules can be stored from -20 to 50 degrees C'),
    ('46 61 23', '1.09.A', 'The membrane system, except the membrane modu'):
        ('deviation', 'GEN-01: 12 months from startup or 18 from shipment, not 24 months'),
    ('46 61 23', '1.09.B', 'Warranty claims shall be acknowledged by tele'):
        ('deviation', 'GEN-13: phone response within 24 hours, not 8'),
    ('46 61 23', '2.01.A', 'The membrane system shall be furnished by the'):
        ('not_applicable', 'procurement statement'),
    ('46 61 23', '2.02.A', 'The membrane bioreactor system shall produce'):
        ('needs_engineer', 'nitrogen has only claims (BIO-02, BIO-03, BIO-04, AER-01); no guarantee'),
    ('46 61 23', '2.02.C', 'Parameter: Design average daily flow;'):
        ('not_applicable', 'design input'),
    ('46 61 23', '2.02.C', 'Parameter: Peak hour flow;'):
        ('not_applicable', 'design input'),
    ('46 61 23', '2.02.C', 'Parameter: Number of membrane trains;'):
        ('not_applicable', 'design input'),
    ('46 61 23', '2.02.C', 'Parameter: Mixed liquor suspended solids in'):
        ('not_applicable', 'process design input'),
    ('46 61 23', '2.02.C', 'Parameter: Maximum net flux, design average'):
        ('comply', 'MBR-20: design net flux at average day flow selected from 10 to 25 gfd'),
    ('46 61 23', '2.02.C', 'Parameter: Maximum net flux, peak hour flow'):
        ('comply', 'MBR-21: up to 40 gfd at peak hour flow'),
    ('46 61 23', '2.02.C', 'Parameter: Maintenance clean frequency, maxi'):
        ('comply', 'MBR-24: maintenance clean once per week'),
    ('46 61 23', '2.02.C', 'Parameter: Recovery clean interval, minimum;'):
        ('comply', 'MBR-26: recovery clean every 6 to 12 months'),
    ('46 61 23', '2.02.C', 'Parameter: Maximum membrane tank side water d'):
        ('comply', 'MBR-38: cassettes fit tanks of 9 to 14 ft side water depth'),
    ('46 61 23', '2.02.C', 'Parameter: Permeate pump turndown, minimum;'):
        ('deviation', 'MBR-35: 4:1 turndown with VFDs, not 5:1'),
    ('46 61 23', '2.02.D', 'Permeate turbidity shall not exceed 0.2 NTU.'):
        ('comply_with_clarification', 'MBR-29: 0.2 NTU or less 95 percent of the time; the bid must state the 95 percent basis'),
    ('46 61 23', '2.02.E', 'Permeate total suspended solids shall not exc'):
        ('comply', 'MBR-30: permeate TSS 5 mg/L or less'),
    ('46 61 23', '2.02.F', 'Permeate BOD5 shall not exceed 2 mg/L'):
        ('deviation', 'MBR-31 guarantees 5 mg/L or less, not 2 mg/L'),
    ('46 61 23', '2.03.A', 'Each cassette shall be removable from its tan'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 23', '2.03.B', 'Cassette frames shall be fabricated from Type'):
        ('comply', 'MBR-34: Type 316L stainless steel frames'),
    ('46 61 23', '2.03.C', 'Each cassette shall weigh not more than 5,000'):
        ('needs_engineer', 'MBR-39 gives up to 6,000 lb; a cassette under 5,000 lb is a design question'),
    ('46 61 23', '2.04.A', 'Membranes shall have a nominal pore size not'):
        ('deviation', 'MBR-01: 0.1 micron pore size, not 0.05 micron or smaller'),
    ('46 61 23', '2.04.B', 'Membrane modules shall carry a full replacem'):
        ('comply', 'MBR-32: full replacement for years 1 to 5 from startup'),
    ('46 61 23', '2.04.C', 'Membranes shall tolerate a cumulative sodium'):
        ('comply', 'MBR-04: 5,000,000 ppm-hours chlorine tolerance'),
    ('46 61 23', '2.04.D', 'Membrane modules should have an expected ser'):
        ('comply', 'MBR-33: expected SiC membrane life of 15 years or more'),
    ('46 61 23', '2.05.A', 'Permeate pumps shall be driven by variable f'):
        ('comply', 'MBR-35: permeate pumps with VFDs'),
    ('46 61 23', '2.06.A', 'Blower sound pressure level shall not exceed'):
        ('comply', 'MBR-36: 85 dBA or less at 3 ft in enclosures'),
    ('46 61 23', '2.07.A', 'Permeate flow meters shall be magnetic flow m'):
        ('comply', 'MBR-43: magnetic flow meters, plus or minus 0.5 percent of reading'),
    ('46 61 23', '2.08.A', 'The membrane system control panel shall be fu'):
        ('comply', 'MBR-40: NEMA 4X enclosure with a PLC'),
    ('46 61 23', '2.08.B', 'The PLC and network switches shall run on an'):
        ('deviation', 'MBR-41: UPS for 15 minutes, not 20'),
    ('46 61 23', '2.08.C', 'The operator interface shall store trends fo'):
        ('deviation', 'MBR-42: 90 days of 1-minute trends, not 120'),
    ('46 61 23', '2.09.A', 'Backpulse shall occur every 8 to 12 minutes.'):
        ('comply', 'MBR-44: backpulse every 8 to 12 minutes'),
    ('46 61 23', '2.10.A', 'Notify the Engineer at least 7 days before th'):
        ('comply', 'GEN-17: 14 days notice of factory tests'),
    ('46 61 23', '2.11.B', 'Furnish one set of special tools for each typ'):
        ('comply', 'GEN-18: one set of special tools per equipment type'),
    ('46 61 23', '3.02.A', 'Perform a clean water test on each train to'):
        ('needs_engineer', 'MBR-46 gives a factory clean water permeability test and a field pressure decay test, not a field clean water test'),
    ('46 61 23', '3.03.A', 'Perform a pressure decay test on each train'):
        ('comply', 'MBR-46: the field integrity test is a pressure decay test'),
    ('46 61 23', '3.04.A', 'Conduct a performance test of 30 days after'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 23', '3.05.A', 'Operate the system in manual mode for not les'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 23', '3.06.A', "A manufacturer's process engineer shall be on"):
        ('comply_with_clarification', 'GEN-11: 5 days on site included; extra days at $1,600 per day plus expenses'),
    ('46 61 23', '3.07.A', 'Provide not less than 12 hours of operator tra'):
        ('deviation', 'GEN-12: one 8-hour session per equipment type, not 12 hours in two sessions'),
    ('46 61 23', '3.08.A', 'Submit a final operation and maintenance manu'):
        ('needs_engineer', 'GEN-10 covers manuals before startup, not an update after the performance test'),
    ('46 61 23', '3.08.B.1', 'Final as-built drawings of the membrane syst'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 23', '3.08.B.2', 'A summary of operator training sessions with'):
        ('needs_engineer', 'GEN-12 covers the training session, not a summary or attendance records'),
    ('46 61 23', '3.08.B.3', 'The Supplier shall hold the unit prices of re'):
        ('needs_engineer', 'MBR-32 covers the warranty only; no row covers holding replacement module prices'),
    # --- Changed by an addendum: the addendum's version is the one labeled ---
    ('46 61 23', '2.11.A', 'Furnish spare membrane modules equal to 4 per'):
        ('deviation', 'MBR-45: spare modules are 2 percent of installed modules, not 4'),
    ('01 33 00', '1.04.C', 'Individual submittal files shall not exceed 10'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 23', '3.08.C', 'The Supplier shall provide remote monitoring'):
        ('needs_engineer', 'GEN-13 covers service response, not remote monitoring support after startup'),
    # --- 46 43 13 Circular Secondary Clarifier Equipment, as reissued by Addendum 3 ---
    ('46 43 13', '1.05.A', 'Each mechanism shall be furnished for an exist'):
        ('comply', 'CLR-09: mechanisms for tanks from 20 to 200 ft in diameter'),
    ('46 43 13', '1.06.A', 'The clarifier mechanisms shall be warranted ag'):
        ('deviation', 'GEN-01: 12 months from startup or 18 from shipment, not 24 months'),
    ('46 43 13', '2.01.A', 'The clarifier drive unit shall be furnished b'):
        ('deviation', 'GEN-19 offers equipment as an approved equal; this clause allows no substitution'),
    ('46 43 13', '2.02.A', 'The drive shall have a continuous torque rati'):
        ('comply', 'CLR-03: drives rated 10,000 to 1,000,000 ft-lb, sized per project'),
    ('46 43 13', '2.02.B', 'The drive shall be rated for a service life o'):
        ('deviation', 'CLR-04: 20 years under the AGMA rating, not 25'),
    ('46 43 13', '2.02.C', 'Drive motors shall be 460 volts, 3 phase, tot'):
        ('comply', 'CLR-08: 0.5 to 1.5 hp, 460 V, 3 phase, TEFC'),
    ('46 43 13', '2.03.A', 'The torque overload device shall sound an ala'):
        ('comply', 'CLR-05: alarm at 100 percent of continuous torque'),
    ('46 43 13', '2.03.B', 'The torque overload device shall shut down t'):
        ('comply', 'CLR-05: motor shutdown at 120 percent of continuous torque'),
    ('46 43 13', '2.04.A', 'Scraper blades shall travel at a tip speed of'):
        ('comply', 'CLR-07: tip speed 8 to 12 ft/min, within the 15 ft/min limit'),
    ('46 43 13', '2.05.A', 'Submerged carbon steel shall be blast cleaned'):
        ('comply', 'CLR-11: SSPC-SP10 blast and a two-coat epoxy system'),
    ('46 43 13', '3.01.A', 'Operate each mechanism in the dry for not les'):
        ('comply', 'CLR-12: 1-hour dry run'),
    ('46 43 13', '3.01.B', 'Operate each mechanism with water for not le'):
        ('comply_with_clarification', 'CLR-12: the standard wet test is 24 hours; longer tests at added cost'),
    ('46 43 13', '3.02.A', "Provide a manufacturer's representative on s"):
        ('comply', 'GEN-11: up to 5 days on site per equipment type'),
}
