# This script updates the valid usage IDs in the specification
# AsciiDoctor files.  If a valid usage entry already contains
# an ID, it skips that entry.  If it does not contain an ID,
# it will generate a new one.
python3 reflow.py -overwrite -noflow -tagvu

