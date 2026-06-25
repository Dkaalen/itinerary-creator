/** Responsibility split from render.js. */
function summaryPage(summary) {
  const glance = summary?.trip_glance || {};
  const arc = summary?.journey_arc || [];
  const columns = summary?.journey_arc_columns || {};
  const glanceRows = Object.keys(glance).map(key => `<div class="glance-row"><div class="glance-label">${esc(key)}</div>${editableText(glance[key], `summary.trip_glance.${key}`, 'glance-value', `Trip glance ${key}`)}</div>`).join('');
  const arcRows = arc.map((row, idx) => `<tr><td>${editableText(row.chapter, `summary.journey_arc.${idx}.chapter`, '')}</td><td>${editableText(row.days, `summary.journey_arc.${idx}.days`, '')}</td><td>${editableText(row.experience, `summary.journey_arc.${idx}.experience`, '')}</td></tr>`).join('');
  const bg = picturesAdded() ? (model.cover?.summary_image?.data_uri || model.cover?.cover_background_data_uri || '') : '';
  const summaryFocus = model.cover?.summary_image?.crop_focus || 'top';
  const isBooknordics = model?.brand?.output_brand === 'booknordics_customer';
  const overlay = isBooknordics ? 'rgba(250,250,251,.58)' : 'rgba(244,239,232,.40)';
  const summaryStyle = bg ? `background-image: linear-gradient(${overlay}, ${overlay}), url('${escAttr(bg)}'); background-position: center center, ${focusPos(summaryFocus)}; background-size: cover, cover; background-repeat: no-repeat, no-repeat;` : '';
  return `<div class="a4-page summary-page" style="${summaryStyle}"><div class="page-content">
    ${coverImageControls('summary_image', 'Page 2 background image', model.cover?.summary_image)}
    <div class="summary-card">${editableText(summary?.trip_glance_title || 'Your Trip at a Glance', 'summary.trip_glance_title', 'summary-title', 'Trip glance title')}${glanceRows}</div>
    <div class="summary-card">${editableText(summary?.journey_arc_title || 'Your Journey Arc', 'summary.journey_arc_title', 'summary-title', 'Journey arc title')}<table class="journey-table"><thead><tr><th>${editableSpan(columns.chapter || 'Chapter', 'summary.journey_arc_columns.chapter', 'table-header-edit', 'Chapter column')}</th><th>${editableSpan(columns.days || 'Days', 'summary.journey_arc_columns.days', 'table-header-edit', 'Days column')}</th><th>${editableSpan(columns.experience || 'What You’ll Experience', 'summary.journey_arc_columns.experience', 'table-header-edit', 'Experience column')}</th></tr></thead><tbody>${arcRows}</tbody></table></div>
  </div></div>`;
}
