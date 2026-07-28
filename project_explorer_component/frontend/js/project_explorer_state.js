const PROJECT_EXPLORER_SELECTION_KEY = 'itinerary-project-explorer-selection:v1';

const projectExplorerState = {
  payload: {},
  selectedIds: new Set(),
  selectedProjects: new Map(),
  committedIds: [],
  listRevision: 0,
  eventSequence: 0,
  selectionSessionId: '',
};

function cleanProjectId(value) {
  return String(value ?? '').trim();
}

function normalizeProjectRecord(value) {
  const source = value && typeof value === 'object' ? value : {};
  const id = cleanProjectId(source.id);
  if (!id) return null;
  return {
    id,
    name: String(source.name || 'Untitled itinerary'),
    owner: String(source.owner || 'Unassigned'),
    folder: String(source.folder || '—'),
    last_saved: String(source.last_saved || '—'),
    is_open: Boolean(source.is_open),
  };
}

function uniqueProjectIds(values) {
  const ids = [];
  for (const value of Array.isArray(values) ? values : []) {
    const id = cleanProjectId(value);
    if (id && !ids.includes(id)) ids.push(id);
  }
  return ids;
}

function projectSelectionStorageKey() {
  const sessionId = String(projectExplorerState.selectionSessionId || '').trim();
  return sessionId ? `${PROJECT_EXPLORER_SELECTION_KEY}:${sessionId}` : '';
}

function readStoredProjectSelection() {
  try {
    const key = projectSelectionStorageKey();
    if (!key) return null;
    const raw = window.sessionStorage?.getItem(key);
    const parsed = raw ? JSON.parse(raw) : null;
    if (!parsed || typeof parsed !== 'object') return null;
    return {
      listRevision: Number(parsed.listRevision || 0),
      selectedIds: uniqueProjectIds(parsed.selectedIds),
      selectedProjects: Array.isArray(parsed.selectedProjects)
        ? parsed.selectedProjects.map(normalizeProjectRecord).filter(Boolean)
        : [],
    };
  } catch (_error) {
    return null;
  }
}

function persistProjectSelection() {
  try {
    const selectedProjects = [...projectExplorerState.selectedIds]
      .map((id) => projectExplorerState.selectedProjects.get(id))
      .filter(Boolean);
    const key = projectSelectionStorageKey();
    if (!key) return;
    window.sessionStorage?.setItem(key, JSON.stringify({
      listRevision: projectExplorerState.listRevision,
      selectedIds: [...projectExplorerState.selectedIds],
      selectedProjects,
    }));
  } catch (_error) {
    // Selection remains available in memory when browser session storage is unavailable.
  }
}

function initializeProjectExplorerState(payload) {
  const source = payload && typeof payload === 'object' ? payload : {};
  const revision = Math.max(0, Number(source.list_revision || 0));
  const nextSessionId = String(source.selection_session_id || '').trim();
  const sessionChanged = Boolean(
    projectExplorerState.selectionSessionId
    && nextSessionId
    && projectExplorerState.selectionSessionId !== nextSessionId
  );
  projectExplorerState.selectionSessionId = nextSessionId;
  const serverIds = uniqueProjectIds(source.selected_project_ids);
  const currentRows = Array.isArray(source.rows)
    ? source.rows.map(normalizeProjectRecord).filter(Boolean)
    : [];
  const serverRecords = Array.isArray(source.selected_projects)
    ? source.selected_projects.map(normalizeProjectRecord).filter(Boolean)
    : [];
  const stored = readStoredProjectSelection();
  const revisionChanged = revision !== projectExplorerState.listRevision;
  const firstRender = !projectExplorerState.payload || !Object.keys(projectExplorerState.payload).length;

  projectExplorerState.payload = source;
  projectExplorerState.listRevision = revision;
  for (const record of [...serverRecords, ...currentRows]) {
    projectExplorerState.selectedProjects.set(record.id, record);
  }

  if (sessionChanged || revisionChanged || (firstRender && (!stored || stored.listRevision !== revision))) {
    projectExplorerState.selectedIds = new Set(serverIds);
  } else if (firstRender && stored && stored.listRevision === revision) {
    projectExplorerState.selectedIds = new Set(stored.selectedIds);
    for (const record of stored.selectedProjects) {
      projectExplorerState.selectedProjects.set(record.id, record);
    }
  }

  projectExplorerState.committedIds = serverIds;
  persistProjectSelection();
}

function selectionChangedSinceCommit() {
  const selected = [...projectExplorerState.selectedIds];
  if (selected.length !== projectExplorerState.committedIds.length) return true;
  return selected.some((id, index) => id !== projectExplorerState.committedIds[index]);
}

function selectedProjectPayload() {
  return [...projectExplorerState.selectedIds]
    .map((id) => projectExplorerState.selectedProjects.get(id) || {id, name: 'Untitled itinerary'})
    .map(normalizeProjectRecord)
    .filter(Boolean);
}

function emitProjectExplorerAction(action, extra = {}) {
  projectExplorerState.eventSequence += 1;
  Streamlit.setComponentValue({
    event_id: `${Date.now()}-${projectExplorerState.eventSequence}`,
    action,
    list_revision: projectExplorerState.listRevision,
    selected_project_ids: [...projectExplorerState.selectedIds],
    selected_projects: selectedProjectPayload(),
    ...extra,
  });
}
