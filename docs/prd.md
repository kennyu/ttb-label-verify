# TTB AI Label Verification Tool
## Product Requirements Document
**Version 1.6 — February 2026**

---

## 1. Document Purpose & Scope

This document refines the original take-home PRD for the TTB AI Label Verification prototype. It corrects ambiguities, surfaces gaps that would block development, and provides sharper acceptance criteria based on stakeholder interview notes and current TTB regulations sourced from ttb.gov (27 CFR Parts 4, 5, 7, and 16).

> **Scope Boundary:** This is a standalone proof-of-concept — it does not integrate with the COLA system or store PII. Production deployment concerns (FedRAMP, document retention) are explicitly out of scope.

---

## 2. Users & Context

Two primary user groups emerge from discovery. Compliance agents (47 total, wide tech range, half over 50) are the primary users performing single-label and batch reviews. IT/evaluators are secondary. The UI must be operable without documentation by a non-technical first-time user.

> **Network:** The ML vision model API is approved and assumed accessible. Cloud deployment is approved given no sensitive data is stored.

---

## 3. Requirements Audit

### 3.1 Required Label Fields by Beverage Type

Fields are sourced from TTB's official mandatory labeling guidance. The app must validate each field appropriate to the detected or user-selected beverage type and surface specific, field-level failure reasons in the UI — not just an overall pass/fail status.

> **UI Requirement — Field-Level Failure Reasons:** When a label fails, the UI must display each non-compliant field individually with the specific TTB requirement it violated (e.g., "Government Warning: missing" or "Alcohol Content: present but format invalid — ABV abbreviation not permitted per 27 CFR 7.63"). A generic "label failed" message is not acceptable.

---

#### 3.1.1 Distilled Spirits (27 CFR Part 5)
*Source: ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/labeling*

| Field | Status | Condition / Note | CFR Reference |
|-------|--------|-----------------|---------------|
| Brand Name | **Required** | Must appear on label | 27 CFR 5.32 |
| Class / Type Designation | **Required** | e.g., "Kentucky Straight Bourbon Whiskey" — must conform to standards of identity | 27 CFR 5.32, Part 5 Subpart C |
| Alcohol Content (ABV) | **Required** | Must be stated as % Alc./Vol. Tolerance: ±0.3 percentage points. "ABV" is not a permitted abbreviation — use "Alc." and "Vol." only | 27 CFR 5.32, 5.37 |
| Net Contents | **Required** | e.g., 750 mL | 27 CFR 5.32, 5.38 |
| Name & Address | **Required** | Bottler or importer name and place | 27 CFR 5.32, 5.36 |
| Country of Origin | **Conditional** | Required for imported spirits only. TTB defers to CBP regulations (19 CFR) | 27 CFR 5.32; CBP rules |
| Government Health Warning | **Required** | Exact verbatim text, case-sensitive. See §3.1.4. | 27 CFR Part 16 |
| Age Statement | **Conditional** | Required when age is a factor in the class/type (e.g., "Straight Whiskey" <4 yrs). Optional for most spirits; mandatory when stated. | 27 CFR 5.40 |
| Color Ingredient Disclosure | **Conditional** | Required if FD&C Yellow No. 5, cochineal extract, carmine, or sulfites are present | 27 CFR 5.32(b) |
| Commodity Statement | **Conditional** | Required when applicable (e.g., "made with neutral spirits" for certain products) | 27 CFR 5.32 |

---

#### 3.1.2 Beer / Malt Beverages (27 CFR Part 7)
*Source: ttb.gov/beer/labeling/malt-beverage-mandatory-label-information*

| Field | Status | Condition / Note | CFR Reference |
|-------|--------|-----------------|---------------|
| Brand Name | **Required** | Must appear on any label; cannot be a class/type designation alone | 27 CFR 7.64 |
| Class / Type Designation | **Required** | e.g., "Ale", "Stout", "Beer", "Lager". Flavored products require a fanciful name + statement of composition | 27 CFR 7.141–7.147 |
| Net Contents | **Required** | May be blown, embossed, or molded into container | 27 CFR 7.70 |
| Name & Address | **Required** | Bottler name and place of bottling. May be blown/embossed into container. | 27 CFR 7.66–7.68 |
| Alcohol Content (ABV) | **Conditional** | Mandatory only when product contains alcohol from added flavors or non-beverage ingredients (other than hops extract). Optional otherwise. "ABV" is not permitted — use "Alc." and "Vol." | 27 CFR 7.63(a)(3) |
| Country of Origin | **Conditional** | Required for imported malt beverages per CBP rules | 27 CFR 7.69; CBP rules |
| Government Health Warning | **Required** | Required on all containers ≥0.5% ABV. Exact verbatim text, case-sensitive. | 27 CFR Part 16 |
| FD&C Yellow No. 5 / Cochineal / Carmine / Sulfites | **Conditional** | Required disclosure if any of these ingredients are present | 27 CFR 7.63(b) |

---

#### 3.1.3 Wine (27 CFR Part 4 for ≥7% ABV; 27 CFR Part 24 for <7% ABV)
*Source: ttb.gov/regulated-commodities/beverage-alcohol/wine*

> **Note:** Wine below 7% ABV is not subject to 27 CFR Part 4 — it falls under FDA food labeling regulations and is out of scope for this prototype. The system should detect or prompt the user to confirm the ABV tier and display an appropriate message if the label appears to be <7% ABV wine.

| Field | Status | Condition / Note | CFR Reference |
|-------|--------|-----------------|---------------|
| Brand Name | **Required** | Must appear on brand label. Minimum type size: 2mm (>187mL containers) | 27 CFR 4.32, 4.38 |
| Class / Type Designation | **Required** | e.g., "Table Wine", "Cabernet Sauvignon", "Sparkling Wine". Must include "wine" or an accepted equivalent. If carbonated >0.392g CO₂/100mL, must include "sparkling" or "carbonated" | 27 CFR 4.32, 4.34, Subpart C |
| Alcohol Content (ABV) | **Required** | Acceptable abbreviations: Alc., Vol., or %. "ABV" is not a listed permitted abbreviation. Tolerance varies by wine type. | 27 CFR 4.32, 4.36 |
| Net Contents | **Required** | Standard fill sizes apply | 27 CFR 4.32, 4.72 |
| Name & Address | **Required** | Bottler or importer name and address | 27 CFR 4.32, 4.35 |
| Appellation of Origin | **Conditional** | Required on brand label if a geographic reference appears anywhere on the label | 27 CFR 4.32, 4.25 |
| Country of Origin | **Conditional** | Required for all imported wine per CBP rules | CBP rules; 27 CFR Part 4 |
| Sulfite Declaration | **Conditional** | Required if sulfites ≥10 ppm. Label must state "Contains Sulfites" | 27 CFR 4.32(e) |
| Government Health Warning | **Required** | Required on all containers ≥0.5% ABV. Exact verbatim text, case-sensitive. | 27 CFR Part 16 |

---

#### 3.1.4 Government Health Warning Statement — Universal (27 CFR Part 16)

The following text must appear verbatim on all alcohol beverage containers ≥0.5% ABV sold or distributed in the United States. Validation must be case-sensitive and character-exact, including punctuation:

```
GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink
alcoholic beverages during pregnancy because of the risk of birth defects.
(2) Consumption of alcoholic beverages impairs your ability to drive a car or
operate machinery, and may cause health problems.
```

- Any deviation — including changed capitalization, missing punctuation, word substitution, or truncation — must produce a **FAIL** result with the specific deviation identified
- "GOVERNMENT WARNING" must appear in all caps
- Both numbered clauses must be present and in order

---

### 3.2 Functional Requirements Status

| Requirement | Status | Notes |
|-------------|--------|-------|
| Label field validation by beverage type | ✅ Specified | Fully defined in §3.1.1–3.1.3 with CFR citations. App must surface field-level failure reasons. |
| Batch upload — max 100 labels | ✅ Clear | Hard limit of 100 labels per batch. See §6 for remaining batch sub-requirements. |
| Imperfect images — retry then escalate | ✅ Clear | If OCR fails to extract a required field, system retries with a specialized OCR prompt. If that also fails, the label is ESCALATED. Escalate is also used for ambiguous data. |
| Escalate for ambiguous labels / false positive reduction | ✅ Clear | Escalation is triggered by ambiguity in extracted data — not by image quality alone. See §5 for full escalation logic. |
| UI: field-level failure reasons per TTB criteria | ✅ Specified | Each failed field must display the specific TTB requirement violated and the relevant CFR citation where possible. |
| Government Warning exact verbatim match | ✅ Clear | Case-sensitive, punctuation-exact. Any deviation = FAIL. Full text in §3.1.4. |

---

### 3.3 Non-Functional Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| Results in ≤5 seconds total batch time | ✅ Clear | The 5-second target applies to total batch completion, not per-label. This drives an asynchronous processing architecture — see §6. |
| ML vision model as OCR/extraction provider | ✅ Clear | An ML vision model capable of extracting text from label images will be used. Model selection to be determined in the architecture document. |
| Cloud deployment | ✅ Clear | No sensitive data is stored, so standard cloud deployment is approved. Async batch architecture must respect platform function timeout limits. |
| No PII storage | ✅ Clear | Label images must not be persisted server-side. Confirm the cloud platform and ML provider image retention policies at implementation time. |

---

## 4. UX Requirements

### 4.1 Streaming Results

- Results must be streamed to the UI as they are processed — each label result appears immediately upon completion, not after the full batch finishes
- Each streamed result must be clearly identified by its filename or a user-assigned label name so agents can track which result belongs to which submission
- A persistent progress indicator must show how many labels have completed vs. total submitted (e.g., "12 of 100 processed")
- Agents must be able to review completed results while remaining labels are still processing

### 4.2 Multi-Image Label Grouping

- A single product label may be submitted as 2 or 3 images (e.g., front panel, back panel, neck label). The UI must allow agents to group multiple images into a single product before submission
- Grouping is agent-controlled in the UI — the system does not attempt to auto-detect which images belong together
- Validation runs against the grouped set: required fields may appear on any image within the group, and the system must treat all images in a group as one label for pass/fail/escalate purposes
- The streamed result for a grouped product must display which image each extracted field was found on (e.g., "Government Warning — found on image 2 of 3")
- If a required field is not found across any image in the group after retry, the group is escalated with detail on which field(s) were missing

### 4.3 General UI Constraints

- All primary actions visible without scrolling on desktop — no hidden menus
- Results display must be field-level, not just pass/fail — each checked field shown with its status and the specific TTB requirement it was validated against
- Failure reasons must reference TTB criteria in plain English (e.g., "Alcohol Content missing — required for all distilled spirits per 27 CFR 5.32")
- Batch results must be scannable — agents should see all label statuses at a glance without opening each individually
- Error messages in plain English — no HTTP codes, stack traces, or technical jargon visible to end users
- Single-label and batch upload accessible from the same screen
- Image quality feedback: when a label is escalated due to unreadable fields, the UI must indicate which specific fields were unreadable across which images, and prompt the agent to resubmit clearer images

---

## 5. Escalation Logic

Escalation exists to reduce false positives — cases where the system would auto-fail a label that a human agent would actually approve. The four possible outcomes are:

- **FAIL** — a required field is absent from the label, or the Government Warning text does not match verbatim
- **RETRY** — OCR could not extract a required field; system automatically resends with a specialized OCR prompt (internal processing step, not surfaced to the agent as a status)
- **ESCALATE** — after retry, extraction still fails; or extracted data is present but ambiguous and requires human judgment
- **PASS** — all required fields present, successfully extracted, and compliant with TTB criteria for the beverage type

> **Image Degradation Logic:** There are no AI confidence thresholds. Instead: (1) First OCR pass — standard prompt. (2) If extraction fails for any required field, automatically retry with a specialized OCR prompt optimized for degraded images. (3) If extraction still fails after retry, ESCALATE to agent with field-level detail on what could not be read. This eliminates threshold-tuning and keeps the logic deterministic.

| Scenario | Disposition | Reason |
|----------|-------------|--------|
| Required field absent from label | **FAIL** | Objective absence — no human judgment needed |
| Government Warning text differs (any character) | **FAIL** | Exact match required; no tolerance |
| Image unreadable on first OCR attempt | **RETRY** | System automatically resends with a specialized OCR prompt before surfacing result to agent |
| Image still unreadable after specialized OCR retry | **ESCALATE** | Both OCR passes failed — escalate to agent with note to resubmit a clearer image and details of which fields remain unreadable |
| ABV within tolerance but format uses non-permitted abbreviation ("ABV") | **ESCALATE** | Possible compliance issue but requires agent confirmation; not a clear pass or fail |
| Class/type designation is an informal synonym of a recognized designation | **ESCALATE** | Human judgment needed on trade understanding |
| Name and address partially obscured but readable | **ESCALATE** | Ambiguous extraction — agent can visually confirm |

---

## 6. Batch Upload Specifications

Maximum batch size is confirmed at **100 labels**. The following sub-specifications remain open:

- **File types accepted:** JPEG and PNG confirmed. TIFF, HEIC, PDF pages — not yet defined. Recommend limiting to JPEG/PNG for prototype.
- **Processing model:** Asynchronous — the 5-second target applies to total batch time, not per-label. Results stream to the UI as each label completes.
- **Partial failure handling:** If a label fails to process due to a server error (not a compliance failure), agents should see completed results immediately rather than waiting for all 100. Confirm behavior with stakeholders (see Open Questions).
- **Result export:** Agents likely need to export batch results for workflow integration. CSV and/or PDF export not yet specified. Recommend adding for prototype.
- **Duplicate detection:** If the same image appears twice in a batch, recommend flagging the duplicate rather than processing it twice.

> **⚠️ Platform Timeout Risk:** Serverless function timeout limits vary by cloud platform. The async streaming architecture must be designed around the chosen platform's constraints. Resolve in the architecture document before build.

---

## 7. Explicitly Out of Scope

- COLA system integration
- FedRAMP compliance or production security controls
- PII storage or document retention policies
- User authentication or role-based access control
- Application submission workflow (the tool reviews labels only — there are no application values to compare against)
- Historical audit trail of reviews
- Multi-language labels (English only for prototype)
- Wine <7% ABV (subject to FDA, not TTB FAA Act rules)
- Proposed TTB NPRMs (allergen labeling, Alcohol Facts statements) — not yet final rules

---

## 8. Open Questions for Stakeholders

| # | Question | Owner |
|---|----------|-------|
| 1 | Should batch results be exportable (CSV / PDF)? | Sarah Chen / Agents |
| 2 | Partial batch failure: show results as they complete, or hold until all 100 are done? | Sarah Chen (Compliance) |
| 3 | Are TIFF, HEIC, or PDF page uploads needed for prototype, or JPEG/PNG only? | Sarah Chen / Agents |

---

## 9. Acceptance Criteria (Prototype)

The prototype is considered successful when all of the following pass:

- A single JPEG or PNG label is uploaded and returns Pass / Fail / Escalate with a per-field breakdown in ≤5 seconds
- Each failed field displays the specific TTB requirement violated, in plain English, with CFR citation
- The Government Warning is validated character-exact and case-sensitive; any deviation produces a FAIL with the specific difference identified
- Beverage type (Beer, Wine, Distilled Spirits) is either detected automatically or selected by the agent, and the correct required field set is applied
- A batch of up to 100 labels can be uploaded; results stream to the UI as each label completes, identified by filename, without waiting for the full batch to finish
- Multiple images (2–3) can be grouped into a single product in the UI before submission; the system validates the group as one label and the result identifies which image each field was found on
- A label with an unreadable required field triggers an automatic retry with a specialized OCR prompt; if extraction still fails after retry, the label is ESCALATED (not auto-failed), with field-level detail on what could not be read and a prompt to resubmit a clearer image
- A label image taken at an angle or with mild glare is still processed; if extraction fails, the retry logic applies
- The UI is usable without documentation by a non-technical tester on first attempt

---

## 10. Assumptions

- The ML vision model API is accessible from both the deployment environment and the TTB test network
- Label images are submitted as individual files (JPEG/PNG), not embedded in PDFs or multi-page TIFFs, for this prototype
- Application form data for comparison is entered manually by the agent — not auto-fetched from COLA
- Wine submitted for review in the prototype is ≥7% ABV and therefore subject to 27 CFR Part 4 (not FDA rules)
- Prototype does not require a login screen or session management
- Proposed TTB NPRMs (allergen labeling, Alcohol Facts) are not included — validation logic reflects current final rules only

---

*End of Document — v1.6*
