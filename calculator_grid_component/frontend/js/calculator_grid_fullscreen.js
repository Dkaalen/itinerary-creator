let calculatorFullscreen = false;

function toggleCalculatorFullscreen() {
  calculatorFullscreen = !calculatorFullscreen;
  const shell = document.querySelector('.calculator-grid-shell');
  if (!shell) return;
  shell.classList.toggle('fullscreen', calculatorFullscreen);
  setCalculatorHostFullscreen(calculatorFullscreen);
  updateFullscreenButton();
  if (calculatorFullscreen && shell.requestFullscreen && !document.fullscreenElement) {
    shell.requestFullscreen().catch(() => {
      // Browser or iframe refused native fullscreen; keep the host iframe fullscreen fallback active.
    });
  } else if (!calculatorFullscreen && document.fullscreenElement && document.exitFullscreen) {
    document.exitFullscreen().catch(() => {});
  }
  requestAnimationFrame(setCalculatorFrameHeight);
}

function updateFullscreenButton() {
  const button = document.querySelector('[data-action="toggle-fullscreen"]');
  if (button) button.textContent = calculatorFullscreen ? 'Exit fullscreen' : 'Fullscreen calculator';
}

function handleFullscreenChange() {
  if (!document.fullscreenElement && calculatorFullscreen) {
    calculatorFullscreen = false;
    document.querySelector('.calculator-grid-shell')?.classList.remove('fullscreen');
    setCalculatorHostFullscreen(false);
    updateFullscreenButton();
    requestAnimationFrame(setCalculatorFrameHeight);
  }
}
