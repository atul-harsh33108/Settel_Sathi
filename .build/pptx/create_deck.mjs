import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const root = 'C:/Project/Paytm_SettelSathi';
const skill = 'C:/Users/atuls/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations';
const build = path.join(root, '.build', 'pptx');
const outputDir = path.join(root, 'output');
const draft = path.join(build, 'SettleSaathi_pitch_draft.pptx');
const finalPath = path.join(outputDir, 'SettleSaathi_Pitch_Deck.pptx');
const W = 1280, H = 720;
const C = {
  navy: '#002970', blue: '#0057B8', cyan: '#00B9F2', pale: '#EAF7FC',
  ice: '#F5FAFD', ink: '#102A43', muted: '#516579', white: '#FFFFFF',
  line: '#BCD9E8', green: '#16846B', orange: '#B85C00', soft: '#D7EEF7'
};
const FONT = 'Arial';
const deck = Presentation.create({ slideSize: { width: W, height: H } });

function shape(slide, geometry, x, y, w, h, fill = 'none', lineFill = 'none', lineWidth = 0, name) {
  return slide.shapes.add({
    geometry, name,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: 'solid', fill: lineFill, width: lineWidth }
  });
}
function rect(slide, x, y, w, h, fill, name) {
  return shape(slide, 'rect', x, y, w, h, fill, 'none', 0, name);
}
function text(slide, value, x, y, w, h, size, color = C.ink, bold = false, opts = {}) {
  const s = shape(slide, 'textbox', x, y, w, h, 'none', 'none', 0, opts.name);
  s.text = value;
  s.text.style = {
    typeface: FONT, fontSize: size, color, bold,
    alignment: opts.align ?? 'left', verticalAlignment: opts.valign ?? 'top',
    wrap: 'square', autoFit: 'shrinkText', insets: 0,
    lineSpacing: opts.lineSpacing ?? 1.08
  };
  return s;
}
function base(title, n, note, subtitle) {
  const s = deck.slides.add();
  s.background.fill = C.white;
  rect(s, 0, 0, W, 12, C.cyan, `top-accent-${n}`);
  text(s, title, 76, 48, 1128, 66, 43, C.navy, true, { name: `title-${n}` });
  if (subtitle) text(s, subtitle, 78, 120, 1100, 46, 22, C.muted, false, { name: `subtitle-${n}` });
  rect(s, 76, 660, 1128, 1, C.line, `footer-rule-${n}`);
  text(s, 'SettleSaathi  /  Independent project concept', 76, 674, 920, 22, 14, C.muted, false);
  text(s, String(n).padStart(2, '0'), 1150, 671, 52, 24, 15, C.blue, true, { align: 'right' });
  s.speakerNotes.text = note;
  return s;
}
function sectionLabel(s, value, x, y, w = 450, color = C.blue) {
  text(s, value.toUpperCase(), x, y, w, 24, 15, color, true);
}
function line(s, x, y, w, h = 2, color = C.line) { rect(s, x, y, w, h, color); }

// 1. Cover
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  rect(s, 0, 0, W, 14, C.cyan, 'cover-accent');
  rect(s, 0, 584, W, 136, C.blue, 'cover-lower-band');
  text(s, 'SETTLEMENT OPERATIONS', 82, 92, 560, 28, 17, C.cyan, true);
  text(s, 'SettleSaathi', 78, 150, 970, 90, 72, C.white, true, { name: 'cover-title' });
  text(s, 'Settlement issues, owned through verified resolution', 82, 260, 890, 86, 34, C.white, false, { name: 'cover-subtitle' });
  text(s, 'An AI-powered merchant operations platform', 84, 373, 760, 40, 24, '#D9EFF8', false);
  line(s, 84, 452, 170, 5, C.cyan);
  text(s, 'Paytm-inspired blue palette. Independent project concept, not affiliated with Paytm.', 82, 628, 1100, 28, 17, C.white, false);
  s.speakerNotes.text = 'Project pitch based on the repository README, SettleSaathi PRD v1.0, and Release 0 delivery tracker. The visual palette takes inspiration from Paytm blue and cyan. This is an independent project concept and does not claim Paytm affiliation or integration.';
}

// 2. Problem
{
  const s = base('Settlement status can differ across systems', 2,
    'Source: SettleSaathi PRD v1.0, sections 1 and 4. The problem statement summarizes the repository product brief.',
    'A simple question can require work across separate financial records.');
  sectionLabel(s, 'The merchant question', 82, 205);
  text(s, '“Where is my money?”', 82, 244, 530, 70, 42, C.navy, true);
  text(s, 'Payment activity, provider settlement files, bank statements and support updates often sit in different places.', 82, 337, 480, 106, 25, C.ink, false);
  rect(s, 660, 208, 2, 370, C.line);
  sectionLabel(s, 'The reconciliation gap', 706, 205);
  text(s, 'Provider says “processed”', 706, 250, 450, 42, 28, C.blue, true);
  line(s, 706, 310, 400, 2);
  text(s, 'Bank record has no match', 706, 336, 450, 42, 28, C.navy, true);
  line(s, 706, 396, 400, 2);
  text(s, 'Teams gather evidence, compare references, and follow up manually.', 706, 423, 450, 96, 24, C.muted, false);
  text(s, 'Provider status alone does not prove a bank credit.', 706, 530, 444, 60, 21, C.orange, true);
}

// 3. Product answer
{
  const s = base('One workspace takes an exception from records to resolution', 3,
    'Source: SettleSaathi PRD v1.0 and docs/MVP_SCOPE.md. The product description reflects the intended workflow, not a claim that all parts are implemented.',
    'SettleSaathi connects evidence, reconciliation and case follow-through.');
  const columns = [
    { x: 82, label: 'RECONCILE', title: 'Match the records', body: 'Connect transactions to settlement entries, then compare payouts with bank credits.', color: C.blue },
    { x: 476, label: 'INVESTIGATE', title: 'Explain the gap', body: 'Show the IDs, references and statement period behind each exception.', color: C.cyan },
    { x: 870, label: 'RESOLVE', title: 'Carry the case', body: 'Prepare approved follow-up, track responses and verify the final outcome.', color: C.navy }
  ];
  for (const [i, c] of columns.entries()) {
    rect(s, c.x, 222, 5, 280, c.color, `answer-rule-${i}`);
    sectionLabel(s, c.label, c.x + 26, 226, 330, c.color);
    text(s, c.title, c.x + 26, 271, 340, 50, 30, C.navy, true);
    text(s, c.body, c.x + 26, 341, 330, 126, 23, C.ink, false);
  }
  text(s, 'A merchant operations layer across payment providers and supported bank data sources', 82, 557, 1100, 42, 22, C.blue, true);
}

// 4. Synthetic demo evidence
{
  const s = base('Synthetic demo: ₹18,450 reported settled, ₹0 matched in bank data', 4,
    'Source: docs/DEMO_SCENARIO.md and fixtures/synthetic/v1/expected_results.json, scenario SCN-02. All names, records, amounts and outcomes in this scenario are synthetic. “₹0 matched” describes only the imported statement period and does not mean the funds are lost.',
    'The product reports what the available evidence supports.');
  const figures = [
    { x: 84, label: 'COLLECTED', amount: '₹18,450', detail: 'Completed transactions', color: C.blue },
    { x: 476, label: 'PROVIDER REPORTED', amount: '₹18,450', detail: 'Payout reference present', color: C.cyan },
    { x: 868, label: 'BANK MATCH', amount: '₹0', detail: 'No qualified credit in import', color: C.navy }
  ];
  for (let i = 0; i < figures.length; i++) {
    const d = figures[i];
    sectionLabel(s, d.label, d.x, 228, 330, d.color);
    text(s, d.amount, d.x, 278, 345, 78, 50, C.navy, true);
    rect(s, d.x, 376, 270, 4, d.color);
    text(s, d.detail, d.x, 404, 324, 58, 21, C.muted, false);
    if (i < 2) text(s, '›', d.x + 330, 308, 36, 50, 38, C.cyan, true, { align: 'center' });
  }
  rect(s, 82, 505, 1115, 1, C.line);
  text(s, 'UNMATCHED', 84, 526, 190, 28, 17, C.orange, true);
  text(s, 'The payout has not been matched in the available bank data. The evidence does not establish that funds are lost.', 265, 520, 920, 62, 22, C.ink, false);
}

// 5. Workflow
{
  const s = base('A controlled workflow moves from source data to verified outcome', 5,
    'Source: docs/DEMO_SCENARIO.md and docs/AGENTIC_ARCHITECTURE.md. The stages describe the planned end-to-end product flow; case monitoring and verification are not yet implemented in the current MVP tracker.',
    'Each handoff keeps the source evidence attached to the case.');
  const stages = [
    { x: 82, n: '01', title: 'Import', detail: 'Transactions\nSettlement file\nBank statement' },
    { x: 306, n: '02', title: 'Match', detail: 'Deterministic\nreference and\namount rules' },
    { x: 530, n: '03', title: 'Flag', detail: 'Unmatched payout\nwith evidence\nlinks' },
    { x: 754, n: '04', title: 'Approve', detail: 'Review case draft\nbefore external\naction' },
    { x: 978, n: '05', title: 'Verify', detail: 'Close only with\nauthoritative\noutcome evidence' }
  ];
  line(s, 122, 296, 1036, 4, C.soft);
  for (const [i, st] of stages.entries()) {
    shape(s, 'ellipse', st.x + 22, 274, 46, 46, i < 3 ? C.blue : C.navy, 'none', 0, `stage-node-${i}`);
    text(s, st.n, st.x + 22, 286, 46, 22, 15, C.white, true, { align: 'center', valign: 'middle' });
    text(s, st.title, st.x, 344, 180, 42, 25, C.navy, true);
    text(s, st.detail, st.x, 395, 184, 114, 20, C.ink, false, { lineSpacing: 1.2 });
    if (i === 3) text(s, 'Human approval gate', st.x, 530, 192, 30, 16, C.orange, true);
  }
  text(s, 'A successful tool call is not the same as a verified business outcome.', 82, 589, 1100, 32, 22, C.blue, true);
}

// 6. Trust model
{
  const s = base('Deterministic money. Controlled actions.', 6,
    'Source: README.md, SettleSaathi PRD v1.0 sections 1 and 2, and docs/SECURITY_GOVERNANCE.md. The controls are product requirements and do not imply production certification.',
    'Bounded autonomy keeps money facts and consequential actions under explicit controls.');
  const rows = [
    ['Money and matching', 'Deterministic services calculate and classify financial records'],
    ['Agent role', 'Find evidence, explain the exception and prepare permitted workflow steps'],
    ['Restricted action', 'Require an authorized person to approve before submission'],
    ['Case closure', 'Require a supported terminal outcome from authoritative evidence'],
    ['Audit trail', 'Retain source provenance, decisions, approvals and case events']
  ];
  for (let i = 0; i < rows.length; i++) {
    const y = 212 + i * 82;
    text(s, rows[i][0], 84, y, 280, 36, 22, C.blue, true);
    text(s, rows[i][1], 390, y, 780, 46, 22, C.ink, false);
    if (i < rows.length - 1) line(s, 84, y + 58, 1080, 1, C.line);
  }
}

// 7. Wedge and commercial hypothesis
{
  const s = base('Start with settlement reconciliation, then expand by provider', 7,
    'Source: SettleSaathi PRD v1.0 sections 1, 2 and 3. The pricing approach is a commercial hypothesis introduced for validation; no pricing or market-size data appears in the project source.',
    'A narrow initial workflow can test the foundation for a broader operations layer.');
  sectionLabel(s, 'Initial wedge', 84, 220, 340);
  text(s, 'Settlement-to-bank exceptions', 84, 260, 468, 52, 31, C.navy, true);
  text(s, 'A painful, evidence-heavy task with an observable result: a qualified bank match or an unresolved case.', 84, 326, 440, 110, 23, C.ink, false);
  rect(s, 626, 218, 2, 344, C.line);
  sectionLabel(s, 'Expansion path', 680, 220, 340, C.cyan);
  text(s, 'Add providers through adapters', 680, 260, 475, 50, 30, C.navy, true);
  text(s, 'Keep reconciliation logic on a shared financial model as sources and workflows grow.', 680, 326, 444, 100, 23, C.ink, false);
  sectionLabel(s, 'Commercial hypothesis to test', 84, 488, 460, C.blue);
  text(s, 'Subscription tiers by business size and connected data volume', 84, 526, 500, 66, 22, C.blue, true);
}

// 8. Delivery status
{
  const s = base('Reconciliation engine is built', 8,
    'Source: docs/implementation/TRACKER.md, Release 0 Delivery Tracker, current status as of 31 October 2026. “Done” and “Not started” reproduce tracked milestone status.',
    'M1 data foundations and M2 reconciliation are done. Case, UI and agent milestones remain.');
  sectionLabel(s, 'Done', 84, 215, 360, C.green);
  text(s, 'M1  Data foundations', 84, 258, 470, 40, 27, C.navy, true);
  text(s, 'Canonical records, validated imports, provenance and synthetic fixtures.', 84, 310, 470, 74, 22, C.ink, false);
  text(s, 'M2  Reconciliation engine', 84, 407, 470, 40, 27, C.navy, true);
  text(s, 'Deterministic matching and 10 scenario classifications against the fixture oracle.', 84, 459, 480, 86, 22, C.ink, false);
  rect(s, 626, 215, 2, 368, C.line);
  sectionLabel(s, 'Next milestones', 680, 215, 410, C.orange);
  const next = [
    ['M3', 'Case state, approvals and audit events'],
    ['M4', 'Dashboard and exception review UI'],
    ['M5–M6', 'Agent workflow, support connector and verification'],
    ['M7', 'Runnable end-to-end demo and release checks']
  ];
  for (let i = 0; i < next.length; i++) {
    const y = 261 + i * 76;
    text(s, next[i][0], 680, y, 114, 32, 18, C.blue, true);
    text(s, next[i][1], 804, y - 3, 360, 54, 21, C.ink, false);
  }
}

// 9. Pilot proposal and ask
{
  const s = deck.slides.add();
  s.background.fill = C.navy;
  rect(s, 0, 0, W, 12, C.cyan, 'close-accent');
  text(s, 'PROPOSED NEXT STEP', 82, 86, 450, 30, 17, C.cyan, true);
  text(s, 'Validate the workflow with design partners', 82, 142, 1010, 60, 44, C.white, true);
  text(s, 'Work with merchant finance and operations teams to map available exports, measure today’s reconciliation effort and test the evidence-backed case flow.', 84, 230, 1010, 92, 25, '#E4F3F9', false);
  line(s, 84, 360, 180, 5, C.cyan);
  text(s, 'Pilot success measures', 84, 395, 440, 38, 26, C.white, true);
  text(s, 'Reconciliation accuracy\nTime to detect and resolve\nEvidence completeness\nFalse closure rate', 84, 454, 630, 150, 23, '#E4F3F9', false, { lineSpacing: 1.32 });
  text(s, 'Begin with synthetic data. Add real data only through authorized connections and consented pilots.', 730, 460, 450, 118, 22, C.white, false);
  rect(s, 0, 650, W, 70, C.blue, 'close-lower-band');
  text(s, 'SettleSaathi  /  Independent project concept', 82, 672, 950, 22, 14, C.white, false);
  text(s, '09', 1150, 670, 52, 24, 15, C.white, true, { align: 'right' });
  s.speakerNotes.text = 'Proposed ask added for pitch context, not stated as an existing project commitment. Success measures come from the project PRD. The project currently uses synthetic data and mock connectors; real provider or bank integrations are out of scope for the current build.';
}

await fs.mkdir(build, { recursive: true });
await fs.mkdir(outputDir, { recursive: true });
for (const [i, s] of deck.slides.items.entries()) {
  const png = await deck.export({ slide: s, format: 'png', scale: 1 });
  await fs.writeFile(path.join(build, `slide-${String(i + 1).padStart(2, '0')}.png`), new Uint8Array(await png.arrayBuffer()));
}
await (await PresentationFile.exportPptx(deck)).save(draft);
const { finalizePresentation } = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);
const stagingDir = path.join(build, 'finalizer');
await fs.mkdir(stagingDir, { recursive: true });
const result = await finalizePresentation({
  explicitTotalSlideCount: 9,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  workspaceDir: root,
  candidatePath: draft,
  finalPath,
  pythonExecutable: 'C:/Users/atuls/AppData/Local/Programs/Python/Python312/python.exe',
  integrityValidatorPath: path.join(skill, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(skill, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-heading-fit'],
  fontPolicy: { basis: 'design', families: [FONT] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, 'SettleSaathi_Pitch_Deck.validation.json')
});
console.log(JSON.stringify({ finalPath, result }, null, 2));
