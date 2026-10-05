#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""互換のための入口。ページは共用エンジンで作る build_site.py に移った（2026-10-05）。
  python3 build_page.py [日付]   → build_site.py と同じ（全ページを作り直す）
"""
import build_site

if __name__ == "__main__":
    for p in build_site.build_all():
        print(p)
