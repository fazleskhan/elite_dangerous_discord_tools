"""Compatibility shim for callers importing `db`."""

from ed_tinydb import EDTinyDB, SystemInfo, main

DB = EDTinyDB


if __name__ == "__main__":
    main()
