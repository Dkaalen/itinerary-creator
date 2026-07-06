"""Focused HTML helpers for the itinerary input workspace."""

from __future__ import annotations

import streamlit as st


def render_input_hero() -> None:
    """Render the quiet landing composition for the paste/generate workflow."""

    st.html(
        """
        <div class="home-hero">
          <section class="home-hero-main">
            <span class="home-kicker">Itinerary studio</span>
            <h1 class="home-title">Build the travel document.</h1>
            <p class="home-description">
              Paste supplier rows, open a saved project, or start from the calculator. The app will turn rough operational input into an editable itinerary workspace.
            </p>
            <div class="home-meta-row">
              <span>Paste rows</span>
              <span>Edit copy</span>
              <span>Add images</span>
              <span>Create PDF</span>
            </div>
          </section>
          <aside class="home-hero-side">
            <div class="workspace-help-card">
              <span class="tool-card-title">Suggested flow</span>
              <p class="tool-card-description">Name the itinerary, paste the supplier rows, then generate the internal agent version first.</p>
            </div>
            <div class="workspace-help-card">
              <span class="tool-card-title">Alternate start</span>
              <p class="tool-card-description">Use the calculator when you need to price rows before creating the itinerary.</p>
            </div>
          </aside>
        </div>
        """
    )


def render_section_header(title: str, description: str, *, kicker: str = "Workspace") -> None:
    """Render a compact section heading with consistent product copy."""

    st.html(
        f'''
        <div class="section-header">
          <div>
            <span class="section-kicker">{kicker}</span>
            <h2 class="section-title">{title}</h2>
            <p class="section-description">{description}</p>
          </div>
        </div>
        '''
    )


def render_source_guidance() -> None:
    """Render the calm helper copy above the raw itinerary input."""

    st.html(
        """
        <div class="home-section">
          <div class="section-header">
            <div>
              <span class="section-kicker">Source</span>
              <h2 class="section-title">Paste supplier rows</h2>
              <p class="section-description">
                Use messy Excel or supplier text. Keep day labels, dates, cities, hotels, transfers, flights, activities, and notes in the pasted block.
              </p>
            </div>
            <span class="section-chip">Rows can be messy</span>
          </div>
        </div>
        """
    )


def render_generation_action_bar() -> None:
    """Render the static copy that anchors the generation buttons."""

    st.html(
        """
        <div class="input-action-bar">
          <div class="input-action-copy">
            <strong>Generate itinerary</strong>
            <span>Agent version is recommended first. Customer version uses the same source with client-ready wording.</span>
          </div>
        </div>
        """
    )
