from __future__ import annotations

import html
import textwrap
from typing import Iterable

import streamlit as st

from .config import ACCESS_DATE, SOURCES


def _html(markup: str) -> None:
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


def anchor(name: str) -> None:
    _html(f'<span id="{html.escape(name)}" class="story-anchor"></span>')


def section_header(kicker: str, title: str, dek: str) -> None:
    _html(
        f"""
        <div class="section-heading">
          <div class="eyebrow">{html.escape(kicker)}</div>
          <h2>{html.escape(title)}</h2>
          <p>{html.escape(dek)}</p>
        </div>
        """
    )


def subsection_header(title: str, dek: str | None = None, meta: str | None = None) -> None:
    meta_html = f'<div class="viz-heading__meta">{html.escape(meta)}</div>' if meta else ""
    dek_html = f'<p>{html.escape(dek)}</p>' if dek else ""
    _html(
        f"""
        <div class="viz-heading">
          {meta_html}
          <h3>{html.escape(title)}</h3>
          {dek_html}
        </div>
        """
    )


def story_card(number: str, title: str, body: str, accent: str = "blue") -> None:
    _html(
        f"""
        <article class="story-card story-card--{html.escape(accent)}">
          <div class="story-card__number">{html.escape(number)}</div>
          <h3>{html.escape(title)}</h3>
          <p>{body}</p>
        </article>
        """
    )


def insight_card(title: str, body: str, value: str | None = None) -> None:
    value_html = f'<div class="insight-card__value">{html.escape(value)}</div>' if value else ""
    _html(
        f"""
        <div class="insight-card">
          <div class="insight-card__label">{html.escape(title)}</div>
          {value_html}
          <div class="insight-card__body">{body}</div>
        </div>
        """
    )


def callout(title: str, body: str, kind: str = "note") -> None:
    _html(
        f"""
        <aside class="callout callout--{html.escape(kind)}">
          <strong>{html.escape(title)}</strong>
          <span>{body}</span>
        </aside>
        """
    )


def source_note(source_keys: list[str], extra: str | None = None) -> None:
    rows: list[str] = []
    for key in source_keys:
        source = SOURCES[key]
        items = source if isinstance(source, list) else [source]
        for title, url in items:
            rows.append(
                f'<li><a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">'
                f'{html.escape(title)}</a></li>'
            )
    extra_html = f'<p class="source-extra">{html.escape(extra)}</p>' if extra else ""
    _html(
        f"""
        <details class="source-note">
          <summary><strong>Sumber: BPS</strong>, akses {ACCESS_DATE}</summary>
          <ul>{''.join(rows)}</ul>
          {extra_html}
        </details>
        """
    )


def source_note_geospatial(extra: str | None = None) -> None:
    pdrb_title, pdrb_url = SOURCES["pdrb"]
    boundary_title, boundary_url = SOURCES["boundary"]
    extra_html = f'<p class="source-extra">{html.escape(extra)}</p>' if extra else ""
    _html(
        f"""
        <details class="source-note">
          <summary><strong>Sumber: BPS</strong>, akses {ACCESS_DATE}</summary>
          <ul>
            <li><a href="{html.escape(pdrb_url)}" target="_blank" rel="noopener noreferrer">{html.escape(pdrb_title)}</a></li>
            <li><a href="{html.escape(boundary_url)}" target="_blank" rel="noopener noreferrer">{html.escape(boundary_title)}</a></li>
          </ul>
          {extra_html}
        </details>
        """
    )


def chapter_nav() -> None:
    _html(
        """
        <nav class="site-nav" aria-label="Navigasi cerita">
          <a class="site-nav__brand" href="#pembuka" aria-label="Kembali ke pembuka">
            <span class="site-nav__mark"></span>
            <span>Jejak IMK</span>
          </a>
          <div class="site-nav__links">
            <a href="#pembuka">Pembuka</a>
            <a href="#multivariat">Profil provinsi</a>
            <a href="#hierarki">Hierarki</a>
            <a href="#geospasial">Geospasial</a>
            <a href="#epilog">Epilog</a>
            <a href="#metode">Metode</a>
          </div>
        </nav>
        """
    )
