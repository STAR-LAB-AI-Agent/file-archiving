"""支持 `python -m file_organizer` 方式运行。"""

from file_organizer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
