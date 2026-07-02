let initialPayload = null;
let model = null;
let uploadedImages = {};
let touchedKeys = new Set();
let lastCommitNonce = null;
let lastSavedPayload = '';
let pendingServerSaveKeys = new Set();
let pendingServerSavePayload = '';
// Browser-local autosave is immediate; server-side autosave is debounced and quiet.
let activeEditKey = null;
let activePageId = null;
let activeBlockId = null;
let activeFieldKey = null;
let savedCanvasSelectionRange = null;
let undoStack = [];
let restoredLocalDraftPendingSave = false;
let restoredLocalDraftInfo = null;
let serverAutosaveTimer = null;
let serverAutosaveInFlight = false;
let localDraftTimer = null;
let lastServerAutosavePayload = "";
let lastServerAutosaveAt = 0;
let editorScrollSnapshot = {top: 0, left: 0, pageId: '', blockId: '', editKey: '', capturedAt: 0};
let suppressNextScrollRestore = false;
const SERVER_AUTOSAVE_DELAY_MS = 30000;
const SERVER_AUTOSAVE_MIN_INTERVAL_MS = 45000;
const LOCAL_DRAFT_SAVE_DELAY_MS = 600;
const AUTOSAVE_IDLE_GRACE_MS = 8000;
const SAVE_STATUS_STALE_MS = 20000;
let lastEditorInteractionAt = Date.now();
// Scroll state implementation lives in editor_scroll_state.js; keep API contract markers here: function captureEditorScrollState, function restoreEditorScrollState, captureEditorScrollState(stateName), restoreEditorScrollState();, allowNextDrawToResetScroll.
// Local draft merging must keep server cover previews: serverCover[key]?.data_uri, serverCover[key]?.auto_data_uri, and summary_image.
let saveState = {
  state: 'ready',
  message: 'Ready',
  lastSavedAt: 0,
  lastAttemptAt: 0,
  localDraftAt: 0,
  serverSavedAt: '',
  serverOk: null,
  serverReason: '',
  recovered: false,
  error: ''
};

const WARNING_PATTERNS = [
  /\bPls\b/i, /\bplz\b/i, /\baddon cost\b/i, /\bpaid on ground\b/i,
  /\btranfers\b/i, /\bDate dependant\b/i, /\bFight\s*:/i,
  /\bPrivate Hotel to\b/i, /\bPrivate Airport to\b/i, /\bPrivate Station to\b/i,
  /\bself Transfer\b/, /\blevi Bus Station\b/, /\brovaniemi Bus Station\b/
];
