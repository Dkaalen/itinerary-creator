"""Shared Create PDF editor-commit transaction helpers."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.workflow_transactions import (
    WorkflowTransactionTarget,
    clear_workflow_transaction,
    retry_workflow_transaction,
    start_workflow_transaction,
    workflow_transaction_state,
)


def pdf_transaction_state(state: MutableMapping[str, Any]):
    """Return the Create PDF workflow transaction for a state mapping."""

    return workflow_transaction_state(state, WorkflowTransactionTarget.CREATE_PDF)


def pdf_editor_commit_pending(state: MutableMapping[str, Any]) -> bool:
    """Return whether Create PDF is waiting on an editor-save transaction."""

    transaction = pdf_transaction_state(state)
    return transaction.pending or transaction.timed_out


def start_pdf_editor_commit(state: MutableMapping[str, Any], *, auto_create_pdf: bool = False):
    """Start a Create PDF editor-save transaction."""

    return start_workflow_transaction(state, WorkflowTransactionTarget.CREATE_PDF, auto_create_pdf=auto_create_pdf)


def retry_pdf_editor_commit(state: MutableMapping[str, Any], *, auto_create_pdf: bool = False):
    """Retry a timed-out Create PDF editor-save transaction."""

    return retry_workflow_transaction(state, WorkflowTransactionTarget.CREATE_PDF, auto_create_pdf=auto_create_pdf)


def clear_pdf_editor_commit(state: MutableMapping[str, Any]) -> None:
    """Clear the Create PDF editor-save transaction."""

    clear_workflow_transaction(state, WorkflowTransactionTarget.CREATE_PDF)
