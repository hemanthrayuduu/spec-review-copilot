# Lakeview status labels, for owner review

Each of the 232 Lakeview requirements, with the status the judge should reach and why. The labels were written
from the status definitions in the Phase 2 design (section 7.3) and from `data/knowledge/`, before any real judge
run. No judge output exists yet, so none is shown. Ids such as `GEN-11` or `MBR-32` are rows of
`data/knowledge/capabilities.csv`.

To change a label, edit `scripts/lakeview_status.py` and regenerate with `uv run python scripts/make_lakeview.py`.

| Status | Count |
|---|---|
| needs_engineer | 98 |
| comply | 59 |
| not_applicable | 46 |
| deviation | 21 |
| comply_with_clarification | 8 |

| # | Doc p. | Section | Path | Requirement | Status | Reason |
|---|---|---|---|---|---|---|
| 1 | rfp p.2 | 2 | 2.1 | The Supplier shall furnish the membrane filtration system, two band screens, and two circular primary clarifier mechanisms as specified. | comply | the knowledge base covers band screens (SCR), clarifiers (CLR), and SiC MBR (MBR) |
| 2 | rfp p.2 | 2 | 2.2 | The Supplier shall provide equipment design, fabrication, delivery to the site, installation supervision, startup, testing, and operator training. | comply | GEN-11 field service covers installation check, startup, and training; GEN-12 training |
| 3 | rfp p.2 | 2 | 2.3 | Equipment shall be delivered to the site within 40 weeks after approval of the shop drawings. | comply | GEN-09: ships 20 to 26 weeks after approved shop drawings |
| 4 | rfp p.2 | 2 | 2.4 | Shop drawings shall be submitted within 10 weeks after the notice of assignment. | comply | GEN-08: shop drawings 8 weeks after the purchase order |
| 5 | rfp p.2 | 2 | 2.5 | The Supplier may propose packaged skids for the chemical cleaning equipment. | not_applicable | a permission, not an obligation |
| 6 | rfp p.3 | 3 | 3.2 | Proposals shall be delivered to the Town Clerk, 41 Harbor Street, Lakeview, in a sealed envelope marked with the RFP number. | not_applicable | bid-procedure instruction (proposal delivery) that the brief tracks |
| 7 | rfp p.3 | 3 | 3.3 | Requests for approval of an equal product shall be received no later than 14 days before the proposal due date. | not_applicable | bid-procedure deadline that the brief tracks |
| 8 | rfp p.3 | 3 | 3.4 | Questions about this Request for Proposals shall be submitted in writing to the Engineer. | not_applicable | bid-procedure instruction |
| 9 | rfp p.3 | 4 | 4.1 | The Supplier shall submit a list of at least three (3) installations of the proposed membrane system in municipal wastewater service, each in operation for not less than 2 years. | needs_engineer | GEN-14 lists five SiC MBR plants but not their years in municipal service |
| 10 | rfp p.3 | 4 | 4.2 | For each installation, provide the owner's name, a contact person, the design flow, and the date of startup on Form B. | not_applicable | bid form instruction (Form B) |
| 11 | rfp p.3 | 4 | 4.3 | The Supplier shall maintain a service center able to place a technician on site within 48 hours of a request. | deviation | GEN-13: technician on site within 72 hours, not 48 |
| 12 | rfp p.3 | 4 | 4.4 | The Supplier should identify the location of its nearest parts warehouse. | needs_engineer | no warehouse location in the knowledge base |
| 13 | rfp p.3 | 5 | 5.1 | The Supplier shall conduct an on site pilot test of the proposed membrane system for not less than 90 days. | comply | MBR-47: pilot unit available for 60 to 120 days |
| 14 | rfp p.3 | 5 | 5.2 | The pilot unit shall use full scale membrane modules of the type proposed. | needs_engineer | MBR-47 does not say the pilot uses full scale modules |
| 15 | rfp p.3 | 5 | 5.3 | The pilot shall demonstrate permeate total phosphorus not exceeding 0.1 mg/L for the final 30 days of operation. | needs_engineer | phosphorus has only claims (BIO-01, BIO-03, AER-01); no guarantee |
| 16 | rfp p.3 | 5 | 5.5 | The Supplier shall submit a pilot test report within 30 days after the end of pilot testing. | needs_engineer | no evidence in the knowledge base |
| 17 | rfp p.3 | 5 | 5.6 | The cost of pilot testing shall be included in the proposal price. | comply_with_clarification | MBR-47 bills pilot rental separately; the price must include it |
| 18 | rfp p.3 | 6 | 6.1 | The Supplier shall warrant all equipment against defects in materials and workmanship for 2 years from substantial completion. | deviation | GEN-01: 12 months from startup or 18 from shipment, not 2 years from completion |
| 19 | rfp p.3 | 6 | 6.2 | The Supplier shall guarantee that the membrane system meets the effluent requirements of Section 46 61 00 for 1 year after startup. | needs_engineer | guarantees cover turbidity, TSS, BOD (MBR-29 to 31), not the nutrient limits; GEN-02 |
| 20 | rfp p.3 | 6 | 6.3 | If the guarantee is not met, the Supplier shall furnish additional equipment and labor at no cost to the Owner. | needs_engineer | no evidence in the knowledge base |
| 21 | rfp p.3 | 7 | 7.1 | Proposal prices shall remain valid for 120 days after the proposal due date. | deviation | GEN-07: prices valid 90 days, not 120 |
| 22 | rfp p.3 | 7 | 7.2 | The selected Supplier shall furnish a performance bond in the amount of 100 percent of the contract price. | comply_with_clarification | GEN-05: 100 percent bond available at added cost |
| 23 | rfp p.4 | 7 | 7.3 | Liquidated damages of $1,500 per day shall be assessed for each day that equipment delivery is late. | deviation | GEN-04: up to $500 per day, capped at 5 percent |
| 24 | rfp p.4 | 7 | 7.4 | All iron and steel, manufactured products, and construction materials shall comply with the Build America, Buy America Act (BABA). | comply_with_clarification | GEN-15: BABA compliant supply when specified, at added cost |
| 25 | rfp p.4 | 7 | 7.5 | The Supplier shall submit a BABA certification letter with the shop drawings. | comply | GEN-15: BABA compliant supply when specified |
| 26 | rfp p.4 | 7 | 7.6 | Payment shall be made as follows: 90 percent on delivery and 10 percent on final acceptance. | deviation | GEN-03: 10 percent with order, 80 on delivery, 10 on startup |
| 27 | rfp p.4 | 7 | 7.7 | The Supplier shall maintain commercial general liability insurance of not less than $2,000,000 per occurrence. | comply | GEN-06: $2,000,000 per occurrence |
| 28 | rfp p.4 | 7 | 7.8 | The Supplier shall name the Owner and the Engineer as additional insureds on its liability policies. | needs_engineer | no evidence in the knowledge base |
| 29 | rfp p.4 | 7 | 7.9 | The Supplier shall indemnify the Owner against claims arising from defects in the equipment. | needs_engineer | no evidence in the knowledge base |
| 30 | rfp p.4 | 8 | 8.5 | Proposers should visit the existing plant before submitting a proposal. | not_applicable | bid-procedure recommendation |
| 31 | rfp p.4 | 9 | 9.1 | The proposal shall include a completed Form A and a completed Form B. | not_applicable | bid form instruction |
| 32 | specs p.3 | 01 33 00 | 1.03.A | The Supplier shall submit a submittal schedule within 14 days after the notice to proceed. | needs_engineer | no evidence in the knowledge base |
| 33 | specs p.3 | 01 33 00 | 1.03.B | Allow 21 days for the Engineer's initial review of each submittal. | not_applicable | the Engineer's review period |
| 34 | specs p.3 | 01 33 00 | 1.03.C | Submittals should be organized by specification paragraph. | needs_engineer | no evidence in the knowledge base |
| 35 | specs p.3 | 01 33 00 | 1.04.A | Each submittal shall be transmitted electronically in PDF format with a transmittal form. | comply | GEN-16: submittals are searchable PDF files |
| 36 | specs p.3 | 01 33 00 | 1.04.B | Each submittal shall include a cover sheet listing the project name, the specification Section, and the paragraph numbers covered. | needs_engineer | no evidence in the knowledge base |
| 37 | specs p.3 | 01 33 00 | 1.04.C | Individual submittal files shall not exceed 50 MB. | needs_engineer | no evidence in the knowledge base |
| 38 | specs p.3 | 01 33 00 | 1.05.A | Shop drawings shall be drawn to scale | needs_engineer | no evidence in the knowledge base |
| 39 | specs p.3 | 01 33 00 | 1.05.A | shall show dimensions, materials, equipment weights, and anchor bolt locations | needs_engineer | no evidence in the knowledge base |
| 40 | specs p.3 | 01 33 00 | 1.05.B | Product data shall be marked to show the specific model, options, and accessories proposed. | needs_engineer | no evidence in the knowledge base |
| 41 | specs p.3 | 01 33 00 | 1.06.A | Manuals shall include equipment descriptions, operating procedures, lubrication schedules, troubleshooting guides, and a recommended spare parts list. | needs_engineer | GEN-10 and GEN-18 cover delivery and spare parts, not the full manual contents |
| 42 | specs p.3 | 01 33 00 | 1.06.B | Operation and maintenance manuals shall be submitted in searchable PDF format no later than 30 days before startup. | deviation | GEN-10: manuals 4 weeks before startup, not 30 days |
| 43 | specs p.3 | 01 33 00 | 1.06.C | Preliminary manuals shall be reviewed by the Engineer before the final manuals are prepared. | not_applicable | the Engineer's review step |
| 44 | specs p.4 | 01 33 00 | 1.07.A | Resubmittals shall identify every change made since the previous submission. | needs_engineer | no evidence in the knowledge base |
| 45 | specs p.129 | 46 21 00 | 1.04.A | Submit shop drawings for the band screens in accordance with Section 01 33 00. | comply | GEN-08: shop drawings 8 weeks after the purchase order |
| 46 | specs p.129 | 46 21 00 | 1.04.B | Submit hydraulic calculations showing the headloss through each screen at peak hour flow with the screen 30 percent blinded. | needs_engineer | no evidence in the knowledge base |
| 47 | specs p.129 | 46 21 00 | 1.05.A | Screens shall be the product of a manufacturer regularly engaged in producing band screens for municipal service. | comply | GEN-14 reference lists for band screens; SCR rows |
| 48 | specs p.129 | 46 21 00 | 1.06.A | The band screens shall be warranted against defects in materials and workmanship for 2 years from substantial completion. | deviation | GEN-01: 12 months from startup or 18 from shipment, not 2 years |
| 49 | specs p.129 | 46 21 00 | 2.01.A | Band screens shall be Brightwater Systems Model BS-300, or approved equal. | comply_with_clarification | GEN-19: offered as an approved equal, request filed before the deadline |
| 50 | specs p.130 | 46 21 00 | 2.01.B | Each screen shall pass the peak hour flow of 5.0 MGD with the other screen out of service. | comply | SCR-03: CF100 handles 50 to 1,500 L/s (1 to 40 mgd) |
| 51 | specs p.130 | 46 21 00 | 2.01.D | Headloss through a clean screen shall not exceed 6 inches at peak hour flow. | needs_engineer | SCR-05 gives typical headloss of 250 to 400 mm; meeting 6 in is a sizing question |
| 52 | specs p.130 | 46 21 00 | 2.02.A | Screen frames, panels, and wetted parts shall be Type 316 stainless steel. | comply_with_clarification | SCR-08 standard frame is 304L with polypropylene panels; SCR-14 offers Type 316 at added cost |
| 53 | specs p.130 | 46 21 00 | 2.02.B | Anchor bolts and fasteners shall be Type 316 stainless steel. | comply | SCR-15: all screen fasteners are Type 316 |
| 54 | specs p.130 | 46 21 00 | 2.02.C | Seals and brushes shall be resistant to grease, hydrogen sulfide, and chlorine. | needs_engineer | no evidence in the knowledge base |
| 55 | specs p.130 | 46 21 00 | 2.03.A | Provide a spray wash system with a dedicated booster pump for each screen. | needs_engineer | SCR-11 gives wash water demand, not a supplied booster pump |
| 56 | specs p.130 | 46 21 00 | 2.03.B | Each booster pump shall deliver not less than 40 gpm at 80 psi. | needs_engineer | SCR-11 gives 20 to 30 gpm at 60 psi demand, not pump supply |
| 57 | specs p.130 | 46 21 00 | 2.03.C | Spray nozzles should be of the quick disconnect type. | needs_engineer | no evidence in the knowledge base |
| 58 | specs p.130 | 46 21 00 | 2.03.D | The screen should be arranged for future addition of a second wash water booster pump. | needs_engineer | no evidence in the knowledge base |
| 59 | specs p.130 | 46 21 00 | 2.04.A | Provide one screenings washer compactor for each screen. | needs_engineer | no evidence in the knowledge base |
| 60 | specs p.130 | 46 21 00 | 2.04.B | Washed and compacted screenings shall have a solids content of not less than 40 percent. | needs_engineer | SCR-17 is typical, without a washer compactor |
| 61 | specs p.130 | 46 21 00 | 2.04.C | The washer compactor shall reduce the organic content of the screenings by not less than 80 percent. | needs_engineer | no evidence in the knowledge base |
| 62 | specs p.130 | 46 21 00 | 2.05.A | Each screen shall be furnished with a NEMA 4X stainless steel local control panel. | comply | SCR-16: NEMA 4X stainless steel control panel |
| 63 | specs p.130 | 46 21 00 | 2.05.B | The screen shall start automatically on high differential level and on an adjustable timer. | needs_engineer | no evidence in the knowledge base |
| 64 | specs p.130 | 46 21 00 | 2.05.C | Provide a level sensor upstream and downstream of each screen to measure differential level. | needs_engineer | no evidence in the knowledge base |
| 65 | specs p.130 | 46 21 00 | 2.05.D | Motors shall be premium efficiency, totally enclosed, and rated for 460 volts, 3 phase, 60 Hz. | comply | SCR-12: 460 V, 3 phase, 60 Hz, TEFC, premium efficiency |
| 66 | specs p.130 | 46 21 00 | 3.01.A | Install the screens in accordance with the manufacturer's written instructions and the approved shop drawings. | not_applicable | the installing contractor's duty |
| 67 | specs p.130 | 46 21 00 | 3.02.A | After installation, each screen shall be operated for not less than 8 hours without malfunction. | needs_engineer | no evidence in the knowledge base |
| 68 | specs p.130 | 46 21 00 | 3.02.B | The Supplier shall furnish a written field test report signed by the manufacturer's representative. | needs_engineer | no evidence in the knowledge base |
| 69 | specs p.131 | 46 21 00 | 3.03.A | Provide a manufacturer's representative on site for not less than 4 days for installation inspection and startup of the screens. | comply | GEN-11: up to 5 days on site per equipment type |
| 70 | specs p.131 | 46 21 00 | 3.03.B | Provide not less than 8 hours of operator training on the band screens. | comply | GEN-12: one 8-hour session per equipment type |
| 71 | specs p.132 | 46 43 00 | 1.03.A | Each clarifier shall be designed for a peak hour flow of 2.5 MGD. | not_applicable | design input |
| 72 | specs p.132 | 46 43 00 | 1.03.B | Each clarifier shall be designed for a surface overflow rate not exceeding 2,500 gpd/sf at peak hour flow. | not_applicable | design input for tank sizing |
| 73 | specs p.132 | 46 43 00 | 1.04.A | Submit drive torque calculations and structural calculations for the clarifier mechanisms, sealed by a professional engineer. | needs_engineer | no evidence in the knowledge base |
| 74 | specs p.132 | 46 43 00 | 1.04.B | Submit the drive manufacturer's certification of the AGMA service factor. | needs_engineer | CLR-04 states the AGMA rating basis, not a service factor certification |
| 75 | specs p.132 | 46 43 00 | 1.05.A | The clarifier drives shall be warranted for 5 years from substantial completion. | deviation | GEN-01: 12 months from startup or 18 from shipment, not 5 years |
| 76 | specs p.132 | 46 43 00 | 2.01.A | Clarifier mechanisms, drives, and skimmers shall be furnished by a single manufacturer. | needs_engineer | no evidence in the knowledge base |
| 77 | specs p.132 | 46 43 00 | 2.02.A | The drive shall have a continuous torque rating of not less than 45,000 ft-lb. | comply | CLR-03: drives rated 10,000 to 1,000,000 ft-lb, sized per project |
| 78 | specs p.132 | 46 43 00 | 2.02.B | The drive shall be rated for a service life of not less than 20 years at continuous torque. | comply | CLR-04: 20 years under the AGMA rating |
| 79 | specs p.132 | 46 43 00 | 2.02.C | Drive motors shall be 1 hp, 460 volts, 3 phase, totally enclosed. | comply | CLR-08: 0.5 to 1.5 hp, 460 V, 3 phase, TEFC |
| 80 | specs p.133 | 46 43 00 | 2.03.A | Provide a torque overload device that stops the drive motor at 120 percent of the continuous torque rating. | comply | CLR-05: shutdown at 120 percent of continuous torque |
| 81 | specs p.133 | 46 43 00 | 2.03.B | The torque overload device shall have a local torque indicator. | needs_engineer | no evidence in the knowledge base |
| 82 | specs p.133 | 46 43 00 | 2.03.C | The clarifier drive should be furnished with a torque overload alarm contact. | comply | CLR-06: torque overload alarm contact |
| 83 | specs p.133 | 46 43 00 | 2.04.A | Provide two collector arms with steel scraper blades and replaceable squeegees. | needs_engineer | no evidence in the knowledge base |
| 84 | specs p.133 | 46 43 00 | 2.04.B | Scraper blades shall travel at a tip speed of not more than 10 feet per minute. | comply | CLR-07: tip speed 8 to 12 ft/min, set by the drive speed |
| 85 | specs p.133 | 46 43 00 | 2.05.A | Provide a full radius skimmer that moves scum to a scum box at each revolution. | needs_engineer | no evidence in the knowledge base |
| 86 | specs p.133 | 46 43 00 | 2.05.B | The skimmer should discharge to a scum box located outside the effluent launder. | needs_engineer | no evidence in the knowledge base |
| 87 | specs p.133 | 46 43 00 | 2.06.A | Submerged steel shall be galvanized after fabrication in accordance with ASTM A123. | deviation | CLR-11: SSPC-SP10 blast and epoxy, not galvanizing |
| 88 | specs p.133 | 46 43 00 | 2.06.B | Anchor bolts, nuts, and washers for the mechanisms shall be Type 316 stainless steel. | comply | CLR-10: Type 316 anchor bolts and submerged fasteners |
| 89 | specs p.133 | 46 43 00 | 2.07.A | Provide an energy dissipating influent well with a diameter of not less than 15 percent of the clarifier diameter. | needs_engineer | no evidence in the knowledge base |
| 90 | specs p.133 | 46 43 00 | 2.07.B | Provide fiberglass density current baffles around the full perimeter. | needs_engineer | no evidence in the knowledge base |
| 91 | specs p.133 | 46 43 00 | 3.01.A | Install the mechanisms under the supervision of the manufacturer's representative. | comply | GEN-11: installation check by the manufacturer's representative |
| 92 | specs p.133 | 46 43 00 | 3.01.B | Grout the drive support to provide full bearing under the drive base. | not_applicable | the installing contractor's duty |
| 93 | specs p.133 | 46 43 00 | 3.02.A | Operate each mechanism in the dry for not less than 4 hours to show freedom from binding. | deviation | CLR-12: standard dry run is 1 hour |
| 94 | specs p.133 | 46 43 00 | 3.02.B | Operate each mechanism with water for not less than 24 hours and record the drive torque. | comply | CLR-12: 24-hour wet test |
| 95 | specs p.133 | 46 43 00 | 3.03.A | Provide a manufacturer's representative on site for not less than 3 days for installation inspection, startup, and training on the clarifier mechanisms. | comply | GEN-11: up to 5 days on site per equipment type |
| 96 | specs p.136 | 46 61 00 | 1.05.C | The membrane system shall be designed to accept flow equalization basin return flows of up to 0.5 MGD without exceeding the design net flux. | not_applicable | design input |
| 97 | specs p.136 | 46 61 00 | 1.06.A | Submit operation and maintenance manuals per Section 01 33 00. | comply | GEN-10: O&M manuals as searchable PDF |
| 98 | specs p.136 | 46 61 00 | 1.06.B | Submit shop drawings showing the cassette arrangement, the piping and valve layouts, and the dimensions of each membrane tank. | needs_engineer | GEN-08 gives timing, not shop drawing contents |
| 99 | specs p.136 | 46 61 00 | 1.06.C | Submit a process design report showing the flux, transmembrane pressure, and air scour demand at each design flow. | needs_engineer | no evidence in the knowledge base |
| 100 | specs p.136 | 46 61 00 | 1.06.D | Submit the membrane manufacturer's written warranty. | comply | MBR-32: written membrane warranty |
| 101 | specs p.136 | 46 61 00 | 1.06.E | Submit control system programming documentation, including control narratives and alarm lists, 60 days before factory testing. | needs_engineer | no evidence in the knowledge base |
| 102 | specs p.136 | 46 61 00 | 1.07.A | The membrane modules shall be manufactured under a quality management system certified to ISO 9001. | needs_engineer | no evidence in the knowledge base |
| 103 | specs p.136 | 46 61 00 | 1.07.B | The membrane system supplier shall have single source responsibility for the membrane modules, permeate pumps, blowers, and controls. | needs_engineer | no evidence in the knowledge base |
| 104 | specs p.136 | 46 61 00 | 1.07.C | The membrane system control panel shall be listed under UL 508A. | needs_engineer | no evidence in the knowledge base |
| 105 | specs p.136 | 46 61 00 | 1.08.A | Membrane modules shall be shipped in sealed containers with a preservative solution. | deviation | MBR-37: SiC modules are stored dry without preservative |
| 106 | specs p.136 | 46 61 00 | 1.08.B | Store membrane modules indoors at temperatures between 40 and 95 degrees F. | not_applicable | storage instruction for whoever stores the modules (MBR-37 range is wider) |
| 107 | specs p.136 | 46 61 00 | 1.08.C | Membrane modules shall not be allowed to dry out after wetting. | not_applicable | handling instruction for whoever stores the modules |
| 108 | specs p.136 | 46 61 00 | 1.09.A | The membrane system, except the membrane modules, shall be warranted against defects in materials and workmanship for 2 years from substantial completion. | deviation | GEN-01: 12 months from startup or 18 from shipment, not 2 years |
| 109 | specs p.136 | 46 61 00 | 1.09.B | Warranty claims shall be answered within 5 working days. | comply | GEN-13: phone response within 24 hours |
| 110 | specs p.136 | 46 61 00 | 2.01.A | The membrane system shall be furnished by the Supplier selected under the Request for Proposals. | not_applicable | procurement statement |
| 111 | specs p.136 | 46 61 00 | 2.01.B | Membranes shall be immersed hollow fiber or flat sheet membranes with a nominal pore size of 0.04 micron or smaller. | deviation | MBR-01: 0.1 micron SiC, not 0.04 micron or smaller |
| 112 | specs p.136 | 46 61 00 | 2.02.A | The membrane system shall produce effluent total phosphorus not exceeding 0.1 mg/L as a monthly average. | needs_engineer | phosphorus has only claims (BIO-01, BIO-03, AER-01); no guarantee |
| 113 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Design average daily flow; Value: 2.0 MGD | not_applicable | design input |
| 114 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Maximum month flow; Value: 2.6 MGD | not_applicable | design input |
| 115 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Peak day flow; Value: 4.0 MGD | not_applicable | design input |
| 116 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Peak hour flow; Value: 5.0 MGD | not_applicable | design input |
| 117 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Number of membrane trains; Value: 4 | not_applicable | design input |
| 118 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Trains in service at peak hour flow; Value: 3 | not_applicable | design input |
| 119 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Mixed liquor temperature, minimum; Value: 10 °C | not_applicable | design input |
| 120 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Mixed liquor temperature, maximum; Value: 28 °C | not_applicable | design input |
| 121 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Influent BOD5, design average; Value: 220 mg/L | not_applicable | design input |
| 122 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Influent TSS, design average; Value: 240 mg/L | not_applicable | design input |
| 123 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Influent TKN, design average; Value: 45 mg/L | not_applicable | design input |
| 124 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Influent total phosphorus, design average; Value: 7.0 mg/L | not_applicable | design input |
| 125 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Influent ammonia nitrogen, design average; Value: 30 mg/L | not_applicable | design input |
| 126 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Influent alkalinity, minimum; Value: 150 mg/L as CaCO3 | not_applicable | design input |
| 127 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Influent pH; Value: 6.5 to 8.5 | not_applicable | design input |
| 128 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Design BOD5 load; Value: 3,670 lb/day | not_applicable | design input |
| 129 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Design TSS load; Value: 4,000 lb/day | not_applicable | design input |
| 130 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Mixed liquor suspended solids in membrane tanks; Value: 8,000 to 10,000 mg/L | not_applicable | design input |
| 131 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Solids retention time; Value: 15 days | not_applicable | design input |
| 132 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Maximum net flux, design average flow, all trains in service; Value: 12 gfd | comply | MBR-20: design net flux at average flow selected from 10 to 25 gfd |
| 133 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Maximum net flux, peak day flow, all trains in service; Value: 18 gfd | comply | MBR-20 and MBR-21: design flux selected for the project; 18 gfd fits |
| 134 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Maximum net flux, peak hour flow, one train out of service; Value: 22 gfd | comply | MBR-21: up to 40 gfd at peak hour |
| 135 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Minimum installed membrane area per train; Value: 76,000 sf | needs_engineer | MBR-22 gives up to 2,400 ft2 per cassette; the area per train is sizing |
| 136 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Spare cassette space per train, minimum; Value: 15 percent | needs_engineer | no evidence in the knowledge base |
| 137 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Maximum membrane tank side water depth; Value: 13 feet | comply | MBR-38: cassettes fit tanks of 9 to 14 ft side water depth |
| 138 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Maximum air scour demand per train; Value: 1,500 scfm | needs_engineer | MBR-23 is a typical design value; the total depends on sizing |
| 139 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Maintenance clean frequency, maximum; Value: 2 per week | comply | MBR-24: maintenance clean once per week |
| 140 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Recovery clean interval, minimum; Value: 6 months | comply | MBR-26: recovery clean every 6 to 12 months |
| 141 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Sodium hypochlorite for maintenance cleaning; Value: 200 mg/L | comply | MBR-25: 200 to 500 mg/L |
| 142 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Citric acid for recovery cleaning; Value: 2,000 mg/L | comply | MBR-27: 2,000 to 5,000 mg/L |
| 143 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Permeate pump turndown, minimum; Value: 4:1 | comply | MBR-35: 4:1 turndown with VFDs |
| 144 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Maximum permeate pump suction lift; Value: 15 feet | needs_engineer | no evidence in the knowledge base |
| 145 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Mixed liquor recycle from membrane tanks; Value: 4 to 5 times design average flow | not_applicable | process or civil design input |
| 146 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Dissolved oxygen in membrane tanks, minimum; Value: 2.0 mg/L | not_applicable | process or civil design input |
| 147 | specs p.137 | 46 61 00 | 2.02.B | Parameter: Membrane tank freeboard, minimum; Value: 18 inches | not_applicable | process or civil design input |
| 148 | specs p.138 | 46 61 00 | 2.02.B | Parameter: Permeate BOD5, maximum; Value: 5 mg/L | comply_with_clarification | MBR-31: 5 mg/L only when the supplier designs the biological process |
| 149 | specs p.138 | 46 61 00 | 2.02.B | Parameter: Permeate ammonia nitrogen, maximum; Value: 1.0 mg/L | needs_engineer | ammonia has only claims (BIO-04); no guarantee |
| 150 | specs p.138 | 46 61 00 | 2.02.B | Parameter: Maximum transmembrane pressure; Value: 12 psi | comply | MBR-28: TMP below 10 psi |
| 151 | specs p.138 | 46 61 00 | 2.02.B | Parameter: Permeate total nitrogen, maximum; Value: 10 mg/L | needs_engineer | nitrogen has only claims (BIO-02, BIO-03, AER-01); no guarantee |
| 152 | specs p.138 | 46 61 00 | 2.02.C | Permeate turbidity shall not exceed 0.2 NTU 95 percent of the time. | comply | MBR-29: 0.2 NTU or less 95 percent of the time |
| 153 | specs p.138 | 46 61 00 | 2.02.D | Permeate total suspended solids shall not exceed 1 mg/L. | deviation | MBR-30 guarantees 5 mg/L, not 1 mg/L |
| 154 | specs p.138 | 46 61 00 | 2.03.A | Each cassette shall be removable from its tank without draining the other trains. | needs_engineer | no evidence in the knowledge base |
| 155 | specs p.138 | 46 61 00 | 2.03.B | Cassette frames shall be Type 316 stainless steel. | comply | MBR-34: Type 316L stainless steel frames |
| 156 | specs p.138 | 46 61 00 | 2.03.C | Membrane cassettes should be interchangeable between trains. | needs_engineer | no evidence in the knowledge base |
| 157 | specs p.138 | 46 61 00 | 2.03.D | Each cassette shall weigh not more than 4,000 pounds when lifted wet from the tank. | needs_engineer | MBR-39 gives up to 6,000 lb; a cassette under 4,000 lb is a design question |
| 158 | specs p.138 | 46 61 00 | 2.04.A | Membrane fibers shall be made of polyvinylidene fluoride (PVDF) with an internal support. | deviation | MBR-07: silicon carbide flat plates, not PVDF fibers |
| 159 | specs p.138 | 46 61 00 | 2.04.C | Each module shall be tested for integrity at the factory before shipment. | needs_engineer | MBR-46 is a factory permeability test, not an integrity test |
| 160 | specs p.138 | 46 61 00 | 2.04.D | Membranes shall tolerate a cumulative sodium hypochlorite exposure of not less than 500,000 ppm hours over the membrane life. | comply | MBR-04: 5,000,000 ppm-hours chlorine tolerance |
| 161 | specs p.138 | 46 61 00 | 2.05.A | Provide one permeate pump for each train, plus one installed spare pump. | needs_engineer | no evidence in the knowledge base |
| 162 | specs p.138 | 46 61 00 | 2.05.B | Each permeate pump shall deliver 1,160 gpm at peak hour flow with one train out of service. | needs_engineer | pump sizing; no evidence in the knowledge base |
| 163 | specs p.138 | 46 61 00 | 2.05.C | The Supplier may furnish permeate pumps of either the end suction or the self priming type. | not_applicable | a permission, not an obligation |
| 164 | specs p.138 | 46 61 00 | 2.05.D | Permeate pumps shall be driven by variable frequency drives. | comply | MBR-35: permeate pumps with VFDs |
| 165 | specs p.138 | 46 61 00 | 2.05.E | Permeate pumps shall be capable of reverse flow for backpulsing. | comply | MBR-44: the system backpulses |
| 166 | specs p.138 | 46 61 00 | 2.06.A | Provide one air scour blower for each train and one installed standby blower. | needs_engineer | no evidence in the knowledge base |
| 167 | specs p.138 | 46 61 00 | 2.06.B | Blowers shall be rotary lobe or rotary screw type with sound enclosures. | needs_engineer | MBR-36 gives sound enclosures but not the blower type |
| 168 | specs p.138 | 46 61 00 | 2.06.C | Blower sound pressure level shall not exceed 80 dBA at 3 feet from the enclosure. | deviation | MBR-36: 85 dBA, not 80 |
| 169 | specs p.138 | 46 61 00 | 2.07.A | Provide a chemical cleaning system for maintenance and recovery cleaning with sodium hypochlorite and citric acid. | needs_engineer | MBR-24 and MBR-26 give the cleaning chemicals, not the supplied system |
| 170 | specs p.138 | 46 61 00 | 2.07.B | Chemical metering pumps shall be peristaltic hose pumps. | needs_engineer | no evidence in the knowledge base |
| 171 | specs p.138 | 46 61 00 | 2.07.C | Each chemical storage tank shall hold not less than 30 days of chemical at design average conditions. | needs_engineer | no evidence in the knowledge base |
| 172 | specs p.139 | 46 61 00 | 2.07.D | Provide secondary containment sized for 110 percent of the largest tank. | not_applicable | civil work for the contractor |
| 173 | specs p.139 | 46 61 00 | 2.08.A | Provide a turbidimeter on the combined permeate of each train. | needs_engineer | no evidence in the knowledge base |
| 174 | specs p.139 | 46 61 00 | 2.08.B | Provide a transmembrane pressure transmitter on each train. | needs_engineer | no evidence in the knowledge base |
| 175 | specs p.139 | 46 61 00 | 2.08.C | Flow meters shall be magnetic flow meters with an accuracy of plus or minus 0.5 percent of rate. | comply | MBR-43: plus or minus 0.5 percent of reading |
| 176 | specs p.139 | 46 61 00 | 2.09.A | Provide a programmable logic controller (PLC) control panel in a NEMA 12 enclosure for indoor installation. | comply | MBR-40: NEMA 4X, which exceeds NEMA 12 |
| 177 | specs p.139 | 46 61 00 | 2.09.B | The control panel shall communicate with the plant SCADA system over EtherNet/IP. | needs_engineer | no evidence in the knowledge base |
| 178 | specs p.139 | 46 61 00 | 2.09.C | Provide an uninterruptible power supply that keeps the PLC running for not less than 30 minutes. | deviation | MBR-41: UPS for 15 minutes, not 30 |
| 179 | specs p.139 | 46 61 00 | 2.09.D | The control system shall automatically take a train out of production when transmembrane pressure exceeds the high setpoint. | needs_engineer | no evidence in the knowledge base |
| 180 | specs p.139 | 46 61 00 | 2.10.A | The membrane system shall operate in automatic mode from the membrane system control panel and from the plant SCADA system. | needs_engineer | no evidence in the knowledge base |
| 181 | specs p.139 | 46 61 00 | 2.10.B | In production mode the PLC shall adjust the permeate pump speed to hold each train at its flow setpoint. | needs_engineer | no evidence in the knowledge base |
| 182 | specs p.139 | 46 61 00 | 2.10.C | Train flow setpoints shall follow the influent flow so that the membrane tank level stays within 6 inches of the level setpoint. | needs_engineer | no evidence in the knowledge base |
| 183 | specs p.139 | 46 61 00 | 2.10.D | Relaxation or backpulse shall occur every 10 to 15 minutes, adjustable by the operator. | needs_engineer | MBR-44 gives 8 to 12 minutes, typical, and does not say it is adjustable |
| 184 | specs p.139 | 46 61 00 | 2.10.E | Air scour shall run continuously while a train is in production. | needs_engineer | no evidence in the knowledge base |
| 185 | specs p.139 | 46 61 00 | 2.10.F | The PLC shall start a maintenance clean on each train at an interval set by the operator. | needs_engineer | no evidence in the knowledge base |
| 186 | specs p.139 | 46 61 00 | 2.10.G | The PLC shall lock out a train in recovery clean mode until the operator confirms that the clean is complete. | needs_engineer | no evidence in the knowledge base |
| 187 | specs p.139 | 46 61 00 | 2.10.H | High transmembrane pressure, low permeability, high permeate turbidity, and blower failure shall each generate an alarm at the control panel and at SCADA. | needs_engineer | no evidence in the knowledge base |
| 188 | specs p.139 | 46 61 00 | 2.10.I | Alarm setpoints shall be adjustable from the operator interface without changes to the PLC program. | needs_engineer | no evidence in the knowledge base |
| 189 | specs p.139 | 46 61 00 | 2.10.J | The operator interface shall trend flux, transmembrane pressure, permeability, and turbidity for each train for not less than 90 days. | comply | MBR-42: 90 days of 1-minute trends |
| 190 | specs p.139 | 46 61 00 | 2.10.K | Provide a color touchscreen operator interface not smaller than 15 inches on the control panel door. | comply | MBR-40: 15 in color operator interface |
| 191 | specs p.139 | 46 61 00 | 2.11.A | Test the control panel at the factory with the final PLC program before shipment. | needs_engineer | no evidence in the knowledge base |
| 192 | specs p.139 | 46 61 00 | 2.11.B | Notify the Engineer at least 21 days before the factory test of the control panel. | deviation | GEN-17: 14 days notice, not 21 |
| 193 | specs p.139 | 46 61 00 | 2.11.C | Permeate pumps shall be tested at the factory in accordance with ANSI/HI 14.6, acceptance grade 1B. | needs_engineer | no evidence in the knowledge base |
| 194 | specs p.140 | 46 61 00 | 2.11.D | Air scour blowers shall be tested at the factory in accordance with ASME PTC 13. | needs_engineer | no evidence in the knowledge base |
| 195 | specs p.140 | 46 61 00 | 2.11.E | Submit certified factory test reports before the equipment ships. | needs_engineer | no evidence in the knowledge base |
| 196 | specs p.140 | 46 61 00 | 2.12.A | Shop prime and finish coat ferrous metal surfaces that will not be submerged. | needs_engineer | no evidence in the knowledge base |
| 197 | specs p.140 | 46 61 00 | 2.12.B | Submerged components shall be stainless steel or plastic and shall not be painted. | needs_engineer | MBR-34 frames are stainless; SiC plates are ceramic, not plastic |
| 198 | specs p.140 | 46 61 00 | 2.13.A | Furnish spare membrane modules equal to 5 percent of the installed modules. | deviation | MBR-45: 2 percent spare modules, not 5 |
| 199 | specs p.140 | 46 61 00 | 2.13.B | Furnish one spare permeate pump seal kit and one spare set of blower drive belts. | needs_engineer | GEN-18 does not list these parts |
| 200 | specs p.140 | 46 61 00 | 3.01.A | Verify that membrane tanks are clean and free of debris before installing cassettes. | not_applicable | the installing contractor's duty |
| 201 | specs p.140 | 46 61 00 | 3.02.A | Install cassettes level to within 0.25 inch across each cassette. | not_applicable | the installing contractor's tolerance |
| 202 | specs p.140 | 46 61 00 | 3.02.B | Do not install membrane modules until the tanks have been flushed and the band screens are in operation. | not_applicable | construction sequence for the contractor |
| 203 | specs p.140 | 46 61 00 | 3.03.A | Perform a clean water test on each train to confirm permeate flow and transmembrane pressure before mixed liquor is introduced. | needs_engineer | no evidence in the knowledge base |
| 204 | specs p.140 | 46 61 00 | 3.03.B | Clean water permeability shall be not less than 90 percent of the value stated in the process design report. | needs_engineer | no evidence in the knowledge base |
| 205 | specs p.140 | 46 61 00 | 3.04.A | Perform a pressure decay test on each train before startup. | comply | MBR-46: the field integrity test is a pressure decay test |
| 206 | specs p.140 | 46 61 00 | 3.04.B | The pressure decay rate shall not exceed 0.5 psi in 10 minutes. | needs_engineer | no evidence in the knowledge base |
| 207 | specs p.140 | 46 61 00 | 3.04.C | Repair or replace modules that fail the integrity test and retest the train. | needs_engineer | no evidence in the knowledge base |
| 208 | specs p.140 | 46 61 00 | 3.05.A | Demonstrate every control mode, alarm, and interlock in the presence of the Engineer. | needs_engineer | no evidence in the knowledge base |
| 209 | specs p.140 | 46 61 00 | 3.05.B | Demonstrate a maintenance clean and a recovery clean on one train. | needs_engineer | no evidence in the knowledge base |
| 210 | specs p.140 | 46 61 00 | 3.05.C | Simulate a power failure and show that the system restarts in automatic mode when power returns. | needs_engineer | no evidence in the knowledge base |
| 211 | specs p.140 | 46 61 00 | 3.06.A | Conduct a performance test of 30 days after the biological process has reached steady state. | needs_engineer | no evidence in the knowledge base |
| 212 | specs p.140 | 46 61 00 | 3.06.B | During the test the system shall treat the design average flow with net flux and transmembrane pressure within the limits in Article 2.02. | comply | MBR-20 flux and MBR-28 TMP are within the Article 2.02 limits |
| 213 | specs p.140 | 46 61 00 | 3.06.C | Collect composite permeate samples three times per week for total phosphorus and TSS. | not_applicable | sampling by the owner or contractor |
| 214 | specs p.141 | 46 61 00 | 3.06.D | If the performance test fails, the Supplier shall modify the system and repeat the test at no cost to the Owner. | needs_engineer | no evidence in the knowledge base |
| 215 | specs p.141 | 46 61 00 | 3.07.A | Seed the membrane tanks with mixed liquor from the existing plant under the direction of the manufacturer's representative. | comply | GEN-11: startup service by the manufacturer's representative |
| 216 | specs p.141 | 46 61 00 | 3.07.B | Operate the system in manual mode for not less than 48 hours before switching to automatic control. | needs_engineer | no evidence in the knowledge base |
| 217 | specs p.141 | 46 61 00 | 3.08.A | Provide a manufacturer's process engineer on site during the performance test. | comply_with_clarification | GEN-11: 5 days included; extra days at $1,600 per day |
| 218 | specs p.141 | 46 61 00 | 3.08.B | Field service reports shall be submitted within 7 days after each visit. | needs_engineer | no evidence in the knowledge base |
| 219 | specs p.141 | 46 61 00 | 3.08.C.1 | Inspection of each membrane tank before cassettes are installed. | comply | GEN-11: installation check by field service |
| 220 | specs p.141 | 46 61 00 | 3.08.C.2 | Inspection of the cassette installation and alignment. | comply | GEN-11: installation check by field service |
| 221 | specs p.141 | 46 61 00 | 3.08.C.3 | Witnessing of the clean water test. | comply | GEN-11: startup field service |
| 222 | specs p.141 | 46 61 00 | 3.08.C.4 | Calibration checks of the transmembrane pressure and turbidity instruments. | comply | GEN-11: startup field service |
| 223 | specs p.141 | 46 61 00 | 3.08.C.5 | Verification of the PLC programming and alarm setpoints. | comply | GEN-11: startup field service |
| 224 | specs p.141 | 46 61 00 | 3.08.C.6 | Supervision of the first maintenance clean. | comply | GEN-11: startup field service |
| 225 | specs p.141 | 46 61 00 | 3.08.C.7 | The Contractor shall provide a factory-trained service technician on site for not less than 10 working days during startup. | comply_with_clarification | GEN-11: 5 days included; extra days at $1,600 per day |
| 226 | specs p.141 | 46 61 00 | 3.08.C.8 | Assistance with the performance test and the test report. | comply | GEN-11: startup field service |
| 227 | specs p.141 | 46 61 00 | 3.09.A | Provide not less than 16 hours of operator training on the membrane system in two sessions. | deviation | GEN-12: one 8-hour session per equipment type, not 16 hours |
| 228 | specs p.141 | 46 61 00 | 3.09.B | Training shall cover normal operation, cleaning procedures, membrane integrity testing, and troubleshooting. | needs_engineer | no evidence in the knowledge base |
| 229 | specs p.141 | 46 61 00 | 3.09.C | Training sessions shall be video recorded and the recordings given to the Owner. | needs_engineer | no evidence in the knowledge base |
| 230 | specs p.141 | 46 61 00 | 3.10.A | Spare membrane modules should be stored in the original shipping containers. | not_applicable | storage instruction for the owner |
| 231 | addendum_1 p.1 | 46 61 00 | 2.04.B | Membrane modules shall carry a full replacement warranty of 7 years from substantial completion. | deviation | MBR-32: full replacement for 5 years from startup, then prorated |
| 232 | addendum_1 p.1 | 46 21 00 | 2.01.C | Screen panels shall have perforations of 2 mm diameter. | comply | SCR-01 and SCR-02: apertures from 2 mm |
