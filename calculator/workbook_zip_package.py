"""Clone XLSX ZIP packages while replacing only approved parts."""

from __future__ import annotations

from io import BytesIO
from typing import Mapping
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def clone_xlsx_package(
    source: ZipFile,
    replacements: Mapping[str, bytes],
) -> bytes:
    """Return a metadata-preserving package clone with selected replacements."""

    buffer = BytesIO()
    with ZipFile(buffer, "w") as target:
        for info in source.infolist():
            data = replacements.get(info.filename)
            if data is None:
                data = source.read(info.filename)
            target.writestr(_clone_zip_info(info), data)
    return buffer.getvalue()


def _clone_zip_info(info: ZipInfo) -> ZipInfo:
    clone = ZipInfo(info.filename, date_time=info.date_time)
    clone.compress_type = info.compress_type if info.compress_type is not None else ZIP_DEFLATED
    clone.comment = info.comment
    clone.extra = info.extra
    clone.internal_attr = info.internal_attr
    clone.external_attr = info.external_attr
    clone.create_system = info.create_system
    clone.create_version = info.create_version
    clone.extract_version = info.extract_version
    clone.flag_bits = info.flag_bits
    clone.volume = info.volume
    return clone
