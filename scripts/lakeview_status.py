"""Expected match status for every Lakeview requirement (Phase 2 design 7.3).

Key: (section number or "-", paragraph path, a prefix of the source text that is unique within that path).
Value: (expected status, one-line reason naming the capability or exception ids it rests on).
Written from the status definitions and data/knowledge before any real judge run; changed afterwards only to fix a
labeling error, each change logged with its reason in the Phase 2 execution log.
"""

STATUS: dict[tuple[str, str, str], tuple[str, str]] = {
    ('2', '2.1', 'The Supplier shall furnish the membrane filtrati'):
        ('comply', 'the knowledge base covers band screens (SCR), clarifiers (CLR), and SiC MBR (MBR)'),
    ('2', '2.2', 'The Supplier shall provide equipment design, fab'):
        ('comply', 'GEN-11 field service covers installation check, startup, and training; GEN-12 training'),
    ('2', '2.3', 'Equipment shall be delivered to the site within '):
        ('comply', 'GEN-09: ships 20 to 26 weeks after approved shop drawings'),
    ('2', '2.4', 'Shop drawings shall be submitted within 10 weeks'):
        ('comply', 'GEN-08: shop drawings 8 weeks after the purchase order'),
    ('2', '2.5', 'The Supplier may propose packaged skids for the '):
        ('not_applicable', 'a permission, not an obligation'),
    ('3', '3.2', 'Proposals shall be delivered to the Town Clerk, '):
        ('not_applicable', 'bid-procedure instruction (proposal delivery) that the brief tracks'),
    ('3', '3.3', 'Requests for approval of an equal product shall '):
        ('not_applicable', 'bid-procedure deadline that the brief tracks'),
    ('3', '3.4', 'Questions about this Request for Proposals shall'):
        ('not_applicable', 'bid-procedure instruction'),
    ('4', '4.1', 'The Supplier shall submit a list of at least thr'):
        ('needs_engineer', 'GEN-14 lists five SiC MBR plants but not their years in municipal service'),
    ('4', '4.2', "For each installation, provide the owner's name,"):
        ('not_applicable', 'bid form instruction (Form B)'),
    ('4', '4.3', 'The Supplier shall maintain a service center abl'):
        ('deviation', 'GEN-13: technician on site within 72 hours, not 48'),
    ('4', '4.4', 'The Supplier should identify the location of its'):
        ('needs_engineer', 'no warehouse location in the knowledge base'),
    ('5', '5.1', 'The Supplier shall conduct an on site pilot test'):
        ('comply', 'MBR-47: pilot unit available for 60 to 120 days'),
    ('5', '5.2', 'The pilot unit shall use full scale membrane mod'):
        ('needs_engineer', 'MBR-47 does not say the pilot uses full scale modules'),
    ('5', '5.3', 'The pilot shall demonstrate permeate total phosp'):
        ('needs_engineer', 'phosphorus has only claims (BIO-01, BIO-03, AER-01); no guarantee'),
    ('5', '5.5', 'The Supplier shall submit a pilot test report wi'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('5', '5.6', 'The cost of pilot testing shall be included in t'):
        ('comply_with_clarification', 'MBR-47 bills pilot rental separately; the price must include it'),
    ('6', '6.1', 'The Supplier shall warrant all equipment against'):
        ('deviation', 'GEN-01: 12 months from startup or 18 from shipment, not 2 years from completion'),
    ('6', '6.2', 'The Supplier shall guarantee that the membrane s'):
        ('needs_engineer', 'guarantees cover turbidity, TSS, BOD (MBR-29 to 31), not the nutrient limits; GEN-02'),
    ('6', '6.3', 'If the guarantee is not met, the Supplier shall '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('7', '7.1', 'Proposal prices shall remain valid for 120 days '):
        ('deviation', 'GEN-07: prices valid 90 days, not 120'),
    ('7', '7.2', 'The selected Supplier shall furnish a performanc'):
        ('comply_with_clarification', 'GEN-05: 100 percent bond available at added cost'),
    ('7', '7.3', 'Liquidated damages of $1,500 per day shall be as'):
        ('deviation', 'GEN-04: up to $500 per day, capped at 5 percent'),
    ('7', '7.4', 'All iron and steel, manufactured products, and c'):
        ('comply_with_clarification', 'GEN-15: BABA compliant supply when specified, at added cost'),
    ('7', '7.5', 'The Supplier shall submit a BABA certification l'):
        ('comply', 'GEN-15: BABA compliant supply when specified'),
    ('7', '7.6', 'Payment shall be made as follows: 90 percent on '):
        ('deviation', 'GEN-03: 10 percent with order, 80 on delivery, 10 on startup'),
    ('7', '7.7', 'The Supplier shall maintain commercial general l'):
        ('comply', 'GEN-06: $2,000,000 per occurrence'),
    ('7', '7.8', 'The Supplier shall name the Owner and the Engine'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('7', '7.9', 'The Supplier shall indemnify the Owner against c'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('8', '8.5', 'Proposers should visit the existing plant before'):
        ('not_applicable', 'bid-procedure recommendation'),
    ('9', '9.1', 'The proposal shall include a completed Form A an'):
        ('not_applicable', 'bid form instruction'),
    ('01 33 00', '1.03.A', 'The Supplier shall submit a submittal schedule w'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.03.B', "Allow 21 days for the Engineer's initial review "):
        ('not_applicable', "the Engineer's review period"),
    ('01 33 00', '1.03.C', 'Submittals should be organized by specification '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.04.A', 'Each submittal shall be transmitted electronical'):
        ('comply', 'GEN-16: submittals are searchable PDF files'),
    ('01 33 00', '1.04.B', 'Each submittal shall include a cover sheet listi'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.04.C', 'Individual submittal files shall not exceed 50 M'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.05.A', 'Shop drawings shall be drawn to scale'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.05.A', 'shall show dimensions, materials, equipment weig'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.05.B', 'Product data shall be marked to show the specifi'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('01 33 00', '1.06.A', 'Manuals shall include equipment descriptions, op'):
        ('needs_engineer', 'GEN-10 and GEN-18 cover delivery and spare parts, not the full manual contents'),
    ('01 33 00', '1.06.B', 'Operation and maintenance manuals shall be submi'):
        ('deviation', 'GEN-10: manuals 4 weeks before startup, not 30 days'),
    ('01 33 00', '1.06.C', 'Preliminary manuals shall be reviewed by the Eng'):
        ('not_applicable', "the Engineer's review step"),
    ('01 33 00', '1.07.A', 'Resubmittals shall identify every change made si'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '1.04.A', 'Submit shop drawings for the band screens in acc'):
        ('comply', 'GEN-08: shop drawings 8 weeks after the purchase order'),
    ('46 21 00', '1.04.B', 'Submit hydraulic calculations showing the headlo'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '1.05.A', 'Screens shall be the product of a manufacturer r'):
        ('comply', 'GEN-14 reference lists for band screens; SCR rows'),
    ('46 21 00', '1.06.A', 'The band screens shall be warranted against defe'):
        ('deviation', 'GEN-01: 12 months from startup or 18 from shipment, not 2 years'),
    ('46 21 00', '2.01.A', 'Band screens shall be Brightwater Systems Model '):
        ('comply_with_clarification', 'GEN-19: offered as an approved equal, request filed before the deadline'),
    ('46 21 00', '2.01.B', 'Each screen shall pass the peak hour flow of 5.0'):
        ('comply', 'SCR-03: CF100 handles 50 to 1,500 L/s (1 to 40 mgd)'),
    ('46 21 00', '2.01.D', 'Headloss through a clean screen shall not exceed'):
        ('needs_engineer', 'SCR-05 gives typical headloss of 250 to 400 mm; meeting 6 in is a sizing question'),
    ('46 21 00', '2.02.A', 'Screen frames, panels, and wetted parts shall be'):
        ('comply_with_clarification', 'SCR-08 standard frame is 304L with polypropylene panels; SCR-14 offers Type 316 at added cost'),
    ('46 21 00', '2.02.B', 'Anchor bolts and fasteners shall be Type 316 sta'):
        ('comply', 'SCR-15: all screen fasteners are Type 316'),
    ('46 21 00', '2.02.C', 'Seals and brushes shall be resistant to grease, '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '2.03.A', 'Provide a spray wash system with a dedicated boo'):
        ('needs_engineer', 'SCR-11 gives wash water demand, not a supplied booster pump'),
    ('46 21 00', '2.03.B', 'Each booster pump shall deliver not less than 40'):
        ('needs_engineer', 'SCR-11 gives 20 to 30 gpm at 60 psi demand, not pump supply'),
    ('46 21 00', '2.03.C', 'Spray nozzles should be of the quick disconnect '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '2.03.D', 'The screen should be arranged for future additio'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '2.04.A', 'Provide one screenings washer compactor for each'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '2.04.B', 'Washed and compacted screenings shall have a sol'):
        ('needs_engineer', 'SCR-17 is typical, without a washer compactor'),
    ('46 21 00', '2.04.C', 'The washer compactor shall reduce the organic co'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '2.05.A', 'Each screen shall be furnished with a NEMA 4X st'):
        ('comply', 'SCR-16: NEMA 4X stainless steel control panel'),
    ('46 21 00', '2.05.B', 'The screen shall start automatically on high dif'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '2.05.C', 'Provide a level sensor upstream and downstream o'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '2.05.D', 'Motors shall be premium efficiency, totally encl'):
        ('comply', 'SCR-12: 460 V, 3 phase, 60 Hz, TEFC, premium efficiency'),
    ('46 21 00', '3.01.A', 'Install the screens in accordance with the manuf'):
        ('not_applicable', "the installing contractor's duty"),
    ('46 21 00', '3.02.A', 'After installation, each screen shall be operate'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '3.02.B', 'The Supplier shall furnish a written field test '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 21 00', '3.03.A', "Provide a manufacturer's representative on site "):
        ('comply', 'GEN-11: up to 5 days on site per equipment type'),
    ('46 21 00', '3.03.B', 'Provide not less than 8 hours of operator traini'):
        ('comply', 'GEN-12: one 8-hour session per equipment type'),
    ('46 43 00', '1.03.A', 'Each clarifier shall be designed for a peak hour'):
        ('not_applicable', 'design input'),
    ('46 43 00', '1.03.B', 'Each clarifier shall be designed for a surface o'):
        ('not_applicable', 'design input for tank sizing'),
    ('46 43 00', '1.04.A', 'Submit drive torque calculations and structural '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 43 00', '1.04.B', "Submit the drive manufacturer's certification of"):
        ('needs_engineer', 'CLR-04 states the AGMA rating basis, not a service factor certification'),
    ('46 43 00', '1.05.A', 'The clarifier drives shall be warranted for 5 ye'):
        ('deviation', 'GEN-01: 12 months from startup or 18 from shipment, not 5 years'),
    ('46 43 00', '2.01.A', 'Clarifier mechanisms, drives, and skimmers shall'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 43 00', '2.02.A', 'The drive shall have a continuous torque rating '):
        ('comply', 'CLR-03: drives rated 10,000 to 1,000,000 ft-lb, sized per project'),
    ('46 43 00', '2.02.B', 'The drive shall be rated for a service life of n'):
        ('comply', 'CLR-04: 20 years under the AGMA rating'),
    ('46 43 00', '2.02.C', 'Drive motors shall be 1 hp, 460 volts, 3 phase, '):
        ('comply', 'CLR-08: 0.5 to 1.5 hp, 460 V, 3 phase, TEFC'),
    ('46 43 00', '2.03.A', 'Provide a torque overload device that stops the '):
        ('comply', 'CLR-05: shutdown at 120 percent of continuous torque'),
    ('46 43 00', '2.03.B', 'The torque overload device shall have a local to'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 43 00', '2.03.C', 'The clarifier drive should be furnished with a t'):
        ('comply', 'CLR-06: torque overload alarm contact'),
    ('46 43 00', '2.04.A', 'Provide two collector arms with steel scraper bl'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 43 00', '2.04.B', 'Scraper blades shall travel at a tip speed of no'):
        ('comply', 'CLR-07: tip speed 8 to 12 ft/min, set by the drive speed'),
    ('46 43 00', '2.05.A', 'Provide a full radius skimmer that moves scum to'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 43 00', '2.05.B', 'The skimmer should discharge to a scum box locat'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 43 00', '2.06.A', 'Submerged steel shall be galvanized after fabric'):
        ('deviation', 'CLR-11: SSPC-SP10 blast and epoxy, not galvanizing'),
    ('46 43 00', '2.06.B', 'Anchor bolts, nuts, and washers for the mechanis'):
        ('comply', 'CLR-10: Type 316 anchor bolts and submerged fasteners'),
    ('46 43 00', '2.07.A', 'Provide an energy dissipating influent well with'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 43 00', '2.07.B', 'Provide fiberglass density current baffles aroun'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 43 00', '3.01.A', 'Install the mechanisms under the supervision of '):
        ('comply', "GEN-11: installation check by the manufacturer's representative"),
    ('46 43 00', '3.01.B', 'Grout the drive support to provide full bearing '):
        ('not_applicable', "the installing contractor's duty"),
    ('46 43 00', '3.02.A', 'Operate each mechanism in the dry for not less t'):
        ('deviation', 'CLR-12: standard dry run is 1 hour'),
    ('46 43 00', '3.02.B', 'Operate each mechanism with water for not less t'):
        ('comply', 'CLR-12: 24-hour wet test'),
    ('46 43 00', '3.03.A', "Provide a manufacturer's representative on site "):
        ('comply', 'GEN-11: up to 5 days on site per equipment type'),
    ('46 61 00', '1.05.C', 'The membrane system shall be designed to accept '):
        ('not_applicable', 'design input'),
    ('46 61 00', '1.06.A', 'Submit operation and maintenance manuals per Sec'):
        ('comply', 'GEN-10: O&M manuals as searchable PDF'),
    ('46 61 00', '1.06.B', 'Submit shop drawings showing the cassette arrang'):
        ('needs_engineer', 'GEN-08 gives timing, not shop drawing contents'),
    ('46 61 00', '1.06.C', 'Submit a process design report showing the flux,'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '1.06.D', "Submit the membrane manufacturer's written warra"):
        ('comply', 'MBR-32: written membrane warranty'),
    ('46 61 00', '1.06.E', 'Submit control system programming documentation,'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '1.07.A', 'The membrane modules shall be manufactured under'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '1.07.B', 'The membrane system supplier shall have single s'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '1.07.C', 'The membrane system control panel shall be liste'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '1.08.A', 'Membrane modules shall be shipped in sealed cont'):
        ('deviation', 'MBR-37: SiC modules are stored dry without preservative'),
    ('46 61 00', '1.08.B', 'Store membrane modules indoors at temperatures b'):
        ('not_applicable', 'storage instruction for whoever stores the modules (MBR-37 range is wider)'),
    ('46 61 00', '1.08.C', 'Membrane modules shall not be allowed to dry out'):
        ('not_applicable', 'handling instruction for whoever stores the modules'),
    ('46 61 00', '1.09.A', 'The membrane system, except the membrane modules'):
        ('deviation', 'GEN-01: 12 months from startup or 18 from shipment, not 2 years'),
    ('46 61 00', '1.09.B', 'Warranty claims shall be answered within 5 worki'):
        ('comply', 'GEN-13: phone response within 24 hours'),
    ('46 61 00', '2.01.A', 'The membrane system shall be furnished by the Su'):
        ('not_applicable', 'procurement statement'),
    ('46 61 00', '2.01.B', 'Membranes shall be immersed hollow fiber or flat'):
        ('deviation', 'MBR-01: 0.1 micron SiC, not 0.04 micron or smaller'),
    ('46 61 00', '2.02.A', 'The membrane system shall produce effluent total'):
        ('needs_engineer', 'phosphorus has only claims (BIO-01, BIO-03, AER-01); no guarantee'),
    ('46 61 00', '2.02.B', 'Parameter: Design average daily flow;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Maximum month flow;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Peak day flow;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Peak hour flow;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Number of membrane trains;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Trains in service at peak hour flow;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Mixed liquor temperature, minimum;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Mixed liquor temperature, maximum;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Influent BOD5, design average;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Influent TSS, design average;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Influent TKN, design average;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Influent total phosphorus, design average;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Influent ammonia nitrogen, design average;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Influent alkalinity, minimum;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Influent pH;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Design BOD5 load;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Design TSS load;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Mixed liquor suspended solids in membrane tanks;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Solids retention time;'):
        ('not_applicable', 'design input'),
    ('46 61 00', '2.02.B', 'Parameter: Maximum net flux, design average flow, all trains in service;'):
        ('comply', 'MBR-20: design net flux at average flow selected from 10 to 25 gfd'),
    ('46 61 00', '2.02.B', 'Parameter: Maximum net flux, peak day flow, all trains in service;'):
        ('comply', 'MBR-20 and MBR-21: design flux selected for the project; 18 gfd fits'),
    ('46 61 00', '2.02.B', 'Parameter: Maximum net flux, peak hour flow, one train out of service;'):
        ('comply', 'MBR-21: up to 40 gfd at peak hour'),
    ('46 61 00', '2.02.B', 'Parameter: Minimum installed membrane area per train;'):
        ('needs_engineer', 'MBR-22 gives up to 2,400 ft2 per cassette; the area per train is sizing'),
    ('46 61 00', '2.02.B', 'Parameter: Spare cassette space per train, minimum;'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.02.B', 'Parameter: Maximum membrane tank side water depth;'):
        ('comply', 'MBR-38: cassettes fit tanks of 9 to 14 ft side water depth'),
    ('46 61 00', '2.02.B', 'Parameter: Maximum air scour demand per train;'):
        ('needs_engineer', 'MBR-23 is a typical design value; the total depends on sizing'),
    ('46 61 00', '2.02.B', 'Parameter: Maintenance clean frequency, maximum;'):
        ('comply', 'MBR-24: maintenance clean once per week'),
    ('46 61 00', '2.02.B', 'Parameter: Recovery clean interval, minimum;'):
        ('comply', 'MBR-26: recovery clean every 6 to 12 months'),
    ('46 61 00', '2.02.B', 'Parameter: Sodium hypochlorite for maintenance cleaning;'):
        ('comply', 'MBR-25: 200 to 500 mg/L'),
    ('46 61 00', '2.02.B', 'Parameter: Citric acid for recovery cleaning;'):
        ('comply', 'MBR-27: 2,000 to 5,000 mg/L'),
    ('46 61 00', '2.02.B', 'Parameter: Permeate pump turndown, minimum;'):
        ('comply', 'MBR-35: 4:1 turndown with VFDs'),
    ('46 61 00', '2.02.B', 'Parameter: Maximum permeate pump suction lift;'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.02.B', 'Parameter: Mixed liquor recycle from membrane tanks;'):
        ('not_applicable', 'process or civil design input'),
    ('46 61 00', '2.02.B', 'Parameter: Dissolved oxygen in membrane tanks, minimum;'):
        ('not_applicable', 'process or civil design input'),
    ('46 61 00', '2.02.B', 'Parameter: Membrane tank freeboard, minimum;'):
        ('not_applicable', 'process or civil design input'),
    ('46 61 00', '2.02.B', 'Parameter: Permeate BOD5, maximum;'):
        ('comply_with_clarification', 'MBR-31: 5 mg/L only when the supplier designs the biological process'),
    ('46 61 00', '2.02.B', 'Parameter: Permeate ammonia nitrogen, maximum;'):
        ('needs_engineer', 'ammonia has only claims (BIO-04); no guarantee'),
    ('46 61 00', '2.02.B', 'Parameter: Maximum transmembrane pressure;'):
        ('comply', 'MBR-28: TMP below 10 psi'),
    ('46 61 00', '2.02.B', 'Parameter: Permeate total nitrogen, maximum;'):
        ('needs_engineer', 'nitrogen has only claims (BIO-02, BIO-03, AER-01); no guarantee'),
    ('46 61 00', '2.02.C', 'Permeate turbidity shall not exceed 0.2 NTU 95 p'):
        ('comply', 'MBR-29: 0.2 NTU or less 95 percent of the time'),
    ('46 61 00', '2.02.D', 'Permeate total suspended solids shall not exceed'):
        ('deviation', 'MBR-30 guarantees 5 mg/L, not 1 mg/L'),
    ('46 61 00', '2.03.A', 'Each cassette shall be removable from its tank w'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.03.B', 'Cassette frames shall be Type 316 stainless stee'):
        ('comply', 'MBR-34: Type 316L stainless steel frames'),
    ('46 61 00', '2.03.C', 'Membrane cassettes should be interchangeable bet'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.03.D', 'Each cassette shall weigh not more than 4,000 po'):
        ('needs_engineer', 'MBR-39 gives up to 6,000 lb; a cassette under 4,000 lb is a design question'),
    ('46 61 00', '2.04.A', 'Membrane fibers shall be made of polyvinylidene '):
        ('deviation', 'MBR-07: silicon carbide flat plates, not PVDF fibers'),
    ('46 61 00', '2.04.C', 'Each module shall be tested for integrity at the'):
        ('needs_engineer', 'MBR-46 is a factory permeability test, not an integrity test'),
    ('46 61 00', '2.04.D', 'Membranes shall tolerate a cumulative sodium hyp'):
        ('comply', 'MBR-04: 5,000,000 ppm-hours chlorine tolerance'),
    ('46 61 00', '2.05.A', 'Provide one permeate pump for each train, plus o'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.05.B', 'Each permeate pump shall deliver 1,160 gpm at pe'):
        ('needs_engineer', 'pump sizing; no evidence in the knowledge base'),
    ('46 61 00', '2.05.C', 'The Supplier may furnish permeate pumps of eithe'):
        ('not_applicable', 'a permission, not an obligation'),
    ('46 61 00', '2.05.D', 'Permeate pumps shall be driven by variable frequ'):
        ('comply', 'MBR-35: permeate pumps with VFDs'),
    ('46 61 00', '2.05.E', 'Permeate pumps shall be capable of reverse flow '):
        ('comply', 'MBR-44: the system backpulses'),
    ('46 61 00', '2.06.A', 'Provide one air scour blower for each train and '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.06.B', 'Blowers shall be rotary lobe or rotary screw typ'):
        ('needs_engineer', 'MBR-36 gives sound enclosures but not the blower type'),
    ('46 61 00', '2.06.C', 'Blower sound pressure level shall not exceed 80 '):
        ('deviation', 'MBR-36: 85 dBA, not 80'),
    ('46 61 00', '2.07.A', 'Provide a chemical cleaning system for maintenan'):
        ('needs_engineer', 'MBR-24 and MBR-26 give the cleaning chemicals, not the supplied system'),
    ('46 61 00', '2.07.B', 'Chemical metering pumps shall be peristaltic hos'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.07.C', 'Each chemical storage tank shall hold not less t'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.07.D', 'Provide secondary containment sized for 110 perc'):
        ('not_applicable', 'civil work for the contractor'),
    ('46 61 00', '2.08.A', 'Provide a turbidimeter on the combined permeate '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.08.B', 'Provide a transmembrane pressure transmitter on '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.08.C', 'Flow meters shall be magnetic flow meters with a'):
        ('comply', 'MBR-43: plus or minus 0.5 percent of reading'),
    ('46 61 00', '2.09.A', 'Provide a programmable logic controller (PLC) co'):
        ('comply', 'MBR-40: NEMA 4X, which exceeds NEMA 12'),
    ('46 61 00', '2.09.B', 'The control panel shall communicate with the pla'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.09.C', 'Provide an uninterruptible power supply that kee'):
        ('deviation', 'MBR-41: UPS for 15 minutes, not 30'),
    ('46 61 00', '2.09.D', 'The control system shall automatically take a tr'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.10.A', 'The membrane system shall operate in automatic m'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.10.B', 'In production mode the PLC shall adjust the perm'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.10.C', 'Train flow setpoints shall follow the influent f'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.10.D', 'Relaxation or backpulse shall occur every 10 to '):
        ('needs_engineer', 'MBR-44 gives 8 to 12 minutes, typical, and does not say it is adjustable'),
    ('46 61 00', '2.10.E', 'Air scour shall run continuously while a train i'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.10.F', 'The PLC shall start a maintenance clean on each '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.10.G', 'The PLC shall lock out a train in recovery clean'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.10.H', 'High transmembrane pressure, low permeability, h'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.10.I', 'Alarm setpoints shall be adjustable from the ope'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.10.J', 'The operator interface shall trend flux, transme'):
        ('comply', 'MBR-42: 90 days of 1-minute trends'),
    ('46 61 00', '2.10.K', 'Provide a color touchscreen operator interface n'):
        ('comply', 'MBR-40: 15 in color operator interface'),
    ('46 61 00', '2.11.A', 'Test the control panel at the factory with the f'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.11.B', 'Notify the Engineer at least 21 days before the '):
        ('deviation', 'GEN-17: 14 days notice, not 21'),
    ('46 61 00', '2.11.C', 'Permeate pumps shall be tested at the factory in'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.11.D', 'Air scour blowers shall be tested at the factory'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.11.E', 'Submit certified factory test reports before the'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.12.A', 'Shop prime and finish coat ferrous metal surface'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '2.12.B', 'Submerged components shall be stainless steel or'):
        ('needs_engineer', 'MBR-34 frames are stainless; SiC plates are ceramic, not plastic'),
    ('46 61 00', '2.13.A', 'Furnish spare membrane modules equal to 5 percen'):
        ('deviation', 'MBR-45: 2 percent spare modules, not 5'),
    ('46 61 00', '2.13.B', 'Furnish one spare permeate pump seal kit and one'):
        ('needs_engineer', 'GEN-18 does not list these parts'),
    ('46 61 00', '3.01.A', 'Verify that membrane tanks are clean and free of'):
        ('not_applicable', "the installing contractor's duty"),
    ('46 61 00', '3.02.A', 'Install cassettes level to within 0.25 inch acro'):
        ('not_applicable', "the installing contractor's tolerance"),
    ('46 61 00', '3.02.B', 'Do not install membrane modules until the tanks '):
        ('not_applicable', 'construction sequence for the contractor'),
    ('46 61 00', '3.03.A', 'Perform a clean water test on each train to conf'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.03.B', 'Clean water permeability shall be not less than '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.04.A', 'Perform a pressure decay test on each train befo'):
        ('comply', 'MBR-46: the field integrity test is a pressure decay test'),
    ('46 61 00', '3.04.B', 'The pressure decay rate shall not exceed 0.5 psi'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.04.C', 'Repair or replace modules that fail the integrit'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.05.A', 'Demonstrate every control mode, alarm, and inter'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.05.B', 'Demonstrate a maintenance clean and a recovery c'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.05.C', 'Simulate a power failure and show that the syste'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.06.A', 'Conduct a performance test of 30 days after the '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.06.B', 'During the test the system shall treat the desig'):
        ('comply', 'MBR-20 flux and MBR-28 TMP are within the Article 2.02 limits'),
    ('46 61 00', '3.06.C', 'Collect composite permeate samples three times p'):
        ('not_applicable', 'sampling by the owner or contractor'),
    ('46 61 00', '3.06.D', 'If the performance test fails, the Supplier shal'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.07.A', 'Seed the membrane tanks with mixed liquor from t'):
        ('comply', "GEN-11: startup service by the manufacturer's representative"),
    ('46 61 00', '3.07.B', 'Operate the system in manual mode for not less t'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.08.A', "Provide a manufacturer's process engineer on sit"):
        ('comply_with_clarification', 'GEN-11: 5 days included; extra days at $1,600 per day'),
    ('46 61 00', '3.08.B', 'Field service reports shall be submitted within '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.08.C.1', 'Inspection of each membrane tank before cassette'):
        ('comply', 'GEN-11: installation check by field service'),
    ('46 61 00', '3.08.C.2', 'Inspection of the cassette installation and alig'):
        ('comply', 'GEN-11: installation check by field service'),
    ('46 61 00', '3.08.C.3', 'Witnessing of the clean water test.'):
        ('comply', 'GEN-11: startup field service'),
    ('46 61 00', '3.08.C.4', 'Calibration checks of the transmembrane pressure'):
        ('comply', 'GEN-11: startup field service'),
    ('46 61 00', '3.08.C.5', 'Verification of the PLC programming and alarm se'):
        ('comply', 'GEN-11: startup field service'),
    ('46 61 00', '3.08.C.6', 'Supervision of the first maintenance clean.'):
        ('comply', 'GEN-11: startup field service'),
    ('46 61 00', '3.08.C.7', 'The Contractor shall provide a factory-trained s'):
        ('comply_with_clarification', 'GEN-11: 5 days included; extra days at $1,600 per day'),
    ('46 61 00', '3.08.C.8', 'Assistance with the performance test and the tes'):
        ('comply', 'GEN-11: startup field service'),
    ('46 61 00', '3.09.A', 'Provide not less than 16 hours of operator train'):
        ('deviation', 'GEN-12: one 8-hour session per equipment type, not 16 hours'),
    ('46 61 00', '3.09.B', 'Training shall cover normal operation, cleaning '):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.09.C', 'Training sessions shall be video recorded and th'):
        ('needs_engineer', 'no evidence in the knowledge base'),
    ('46 61 00', '3.10.A', 'Spare membrane modules should be stored in the o'):
        ('not_applicable', 'storage instruction for the owner'),
    ('46 61 00', '2.04.B', 'Membrane modules shall carry a full replacement '):
        ('deviation', 'MBR-32: full replacement for 5 years from startup, then prorated'),
    ('46 21 00', '2.01.C', 'Screen panels shall have perforations of 2 mm di'):
        ('comply', 'SCR-01 and SCR-02: apertures from 2 mm'),
}
