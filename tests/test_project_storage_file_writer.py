from __future__ import annotations

import pytest

from project_storage.file_writer import save_unversioned_file, save_versioned_file


class RecordingRepository:
    def __init__(self) -> None:
        self.uploads: list[str] = []
        self.created_versions: list[dict] = []
        self.registered_files: list[dict] = []
        self.deleted_storage_paths: list[list[str]] = []
        self.deleted_versions: list[str] = []
        self.fail_upload: Exception | None = None
        self.fail_create_version: Exception | None = None
        self.fail_register_file: Exception | None = None
        self.fail_delete_storage: Exception | None = None
        self.fail_delete_version: Exception | None = None

    def upload_file(self, storage_path: str, content: bytes, *, content_type: str) -> None:
        if self.fail_upload is not None:
            raise self.fail_upload
        self.uploads.append(storage_path)

    def create_version(self, **payload):
        if self.fail_create_version is not None:
            raise self.fail_create_version
        self.created_versions.append(payload)
        return {"id": "version-id"}

    def register_file(self, **payload):
        if self.fail_register_file is not None:
            raise self.fail_register_file
        self.registered_files.append(payload)
        return {"id": "file-id"}

    def delete_storage_files(self, storage_paths: list[str]) -> None:
        if self.fail_delete_storage is not None:
            raise self.fail_delete_storage
        self.deleted_storage_paths.append(storage_paths)

    def delete_version(self, version_id: str) -> None:
        if self.fail_delete_version is not None:
            raise self.fail_delete_version
        self.deleted_versions.append(version_id)


def test_versioned_file_write_uploads_before_creating_db_version() -> None:
    repository = RecordingRepository()

    save_versioned_file(
        repository,
        itinerary_id="trip-id",
        version_number=2,
        itinerary_type="agent",
        source_type="manual_save",
        payload={"ok": True},
        file_type="saved_project_json",
        filename="agent-v002.json",
        storage_path="itineraries/trip-id/snapshots/agent-v002.json",
        content=b"{}",
        content_type="application/json",
    )

    assert repository.uploads == ["itineraries/trip-id/snapshots/agent-v002.json"]
    assert repository.created_versions[0]["version_number"] == 2
    assert repository.registered_files[0]["version_id"] == "version-id"
    assert repository.deleted_storage_paths == []
    assert repository.deleted_versions == []


def test_versioned_file_write_does_not_create_version_when_upload_fails() -> None:
    repository = RecordingRepository()
    repository.fail_upload = RuntimeError("upload failed")

    with pytest.raises(RuntimeError, match="upload failed"):
        save_versioned_file(
            repository,
            itinerary_id="trip-id",
            version_number=2,
            itinerary_type="agent",
            source_type="manual_save",
            payload={"ok": True},
            file_type="saved_project_json",
            filename="agent-v002.json",
            storage_path="itineraries/trip-id/snapshots/agent-v002.json",
            content=b"{}",
            content_type="application/json",
        )

    assert repository.created_versions == []
    assert repository.registered_files == []
    assert repository.deleted_storage_paths == []


def test_versioned_file_write_rolls_back_upload_and_version_when_file_registration_fails() -> None:
    repository = RecordingRepository()
    repository.fail_register_file = RuntimeError("register failed")

    with pytest.raises(RuntimeError, match="register failed"):
        save_versioned_file(
            repository,
            itinerary_id="trip-id",
            version_number=2,
            itinerary_type="agent",
            source_type="manual_save",
            payload={"ok": True},
            file_type="saved_project_json",
            filename="agent-v002.json",
            storage_path="itineraries/trip-id/snapshots/agent-v002.json",
            content=b"{}",
            content_type="application/json",
        )

    assert repository.deleted_storage_paths == [["itineraries/trip-id/snapshots/agent-v002.json"]]
    assert repository.deleted_versions == ["version-id"]


def test_unversioned_file_write_rolls_back_upload_when_file_registration_fails() -> None:
    repository = RecordingRepository()
    repository.fail_register_file = RuntimeError("register failed")

    with pytest.raises(RuntimeError, match="register failed"):
        save_unversioned_file(
            repository,
            itinerary_id="trip-id",
            file_type="calculator_xlsx",
            filename="trip.xlsx",
            storage_path="itineraries/trip-id/calculator/trip.xlsx",
            content=b"xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    assert repository.deleted_storage_paths == [["itineraries/trip-id/calculator/trip.xlsx"]]
    assert repository.deleted_versions == [""]


def test_rollback_cleanup_never_masks_original_error() -> None:
    repository = RecordingRepository()
    repository.fail_register_file = RuntimeError("register failed")
    repository.fail_delete_storage = RuntimeError("delete storage failed")
    repository.fail_delete_version = RuntimeError("delete version failed")

    with pytest.raises(RuntimeError, match="register failed"):
        save_versioned_file(
            repository,
            itinerary_id="trip-id",
            version_number=2,
            itinerary_type="agent",
            source_type="manual_save",
            payload={"ok": True},
            file_type="saved_project_json",
            filename="agent-v002.json",
            storage_path="itineraries/trip-id/snapshots/agent-v002.json",
            content=b"{}",
            content_type="application/json",
        )
