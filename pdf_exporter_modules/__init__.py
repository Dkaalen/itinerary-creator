"""Private implementation package for :mod:`pdf_exporter`.

The package initializer is intentionally data-free and side-effect free.  Use
``pdf_exporter`` as the supported application API; import focused implementation
modules directly only inside the PDF subsystem and its renderer-level tests.
"""

__all__: tuple[str, ...] = ()
