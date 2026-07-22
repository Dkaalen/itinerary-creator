// Global Calculator shortcut ownership.

function handleGlobalCalculatorShortcut(event) {
  const modifier = event.ctrlKey || event.metaKey;
  if (!modifier) return;
  const key = event.key.toLowerCase();
  if (key === 'z' && !event.shiftKey) {
    event.preventDefault();
    undoCalculatorChange();
  } else if (key === 'y' || (key === 'z' && event.shiftKey)) {
    event.preventDefault();
    redoCalculatorChange();
  } else if (key === 'd') {
    event.preventDefault();
    fillSelection('down');
  } else if (key === 'r') {
    event.preventDefault();
    fillSelection('right');
  } else if (key === 'f' || key === 'h') {
    event.preventDefault();
    toggleFindReplace(true);
  }
}

document.addEventListener('keydown', handleGlobalCalculatorShortcut);
