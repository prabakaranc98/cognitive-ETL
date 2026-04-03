#!/usr/bin/env python3

from _bootstrap import bootstrap_src_path

bootstrap_src_path()

from cognitive_etl.site_builder import main


if __name__ == "__main__":
    raise SystemExit(main())
