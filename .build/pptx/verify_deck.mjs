import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const file = 'C:/Project/Paytm_SettelSathi/.build/pptx/SettleSaathi_pitch_draft.pptx';
const deck = await PresentationFile.importPptx(await FileBlob.load(file));
const inspected = await deck.inspect({ kind: 'slide,notes', maxChars: 12000 });
console.log(JSON.stringify({ slideCount: deck.slides.items.length, inspection: inspected.ndjson }, null, 2));
