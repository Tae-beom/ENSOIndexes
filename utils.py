# -*- coding: utf-8 -*-
"""
공통 유틸 모음
- inject_css: 본문 폭 확장, iframe 가로폭 100%
"""
import streamlit as st


def inject_css(max_width_px: int = 1200):
  css = f"""
  <style>
  .block-container {{ max-width: {max_width_px}px !important; }}
  [data-testid="stIFrame"] {{ width: 100% !important; }}
  </style>
  """
  st.markdown(css, unsafe_allow_html=True)