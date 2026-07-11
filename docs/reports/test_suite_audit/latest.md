Test-suite QA health report
===========================
Discovered test modules: 300
Discovered test functions: 1604
Named runner groups: critical, fast, parser, activity, architecture, calculator, editor, images, storage, ui, workflow, quality, pdf, slow
Release candidate groups: critical, fast, calculator, storage, workflow, parser, activity, architecture, editor, images, ui, quality, pdf
Modules covered by at least one named group: 300
Modules covered only by full/remaining: 0
Critical group modules: 3
Fast group modules: 19
Critical/PDF/slow/quality overlap: 0
Fast/PDF/slow/quality overlap: 0
Critical source-contract assertion files: 0
Fast source-contract assertion files: 0
Slow direct isolated targets: 47
Slow modules: 7
Direct non-parametrize pytest markers: 0
Source-file contract assertion files: 1
Explicit static-contract helper files: 57
Generated-output text assertion files: 29
Patch/history-style test filenames: 0

Top source-file contract assertion candidates:
  - test_cleanup_final_regression.py: 3

Explicit static-contract helper files:
  - test_accept_supplier_corrections_regression.py
  - test_add_pictures_workflow_regression.py
  - test_architecture_boundaries_regression.py
  - test_architecture_guard_system.py
  - test_booknordics_cover_contrast_speed.py
  - test_booknordics_preview_pdf_parity_polish.py
  - test_calculator_component_mounting.py
  - test_client_output_quality_regression.py
  - test_code_cleanup_hygiene_regression.py
  - test_compatibility_facade_audit.py
  - test_compound_experience_transport_timing.py
  - test_editor_block_inspector.py
  ... 45 more

Largest test modules by function count:
  - test_test_runner_groups.py: 24
  - test_structural_cleanup_tools.py: 23
  - test_output_truth_contracts.py: 19
  - test_corpus_driven_parser_fixes_regression.py: 19
  - test_stress_logic_followups.py: 18
  - test_architecture_guard_system.py: 17
  - test_calculator_ui_foundation.py: 16
  - test_visual_editor_autosave_contract.py: 15
  - test_resumable_test_orchestrator.py: 14
  - test_vipin_excel_corpus_runner_regression.py: 13
  - test_ui_workflow_state_actions.py: 13
  - test_image_matcher_selection_fallbacks.py: 13
