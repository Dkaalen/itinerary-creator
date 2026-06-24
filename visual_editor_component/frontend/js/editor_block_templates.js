/** Controlled editor block templates. */
function controlledBlockTemplate(blockId) {
  const item = controlledPresetGroup('blocks').find(block => block.id === blockId);
  return item?.html || '';
}
