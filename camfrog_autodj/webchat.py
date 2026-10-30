"""Camfrog's room window renders chat in an embedded web view, so there is no Document/Edit text to read:
history = a Pane titled 'camfrog://wb-log-room-data.inside/' whose children are flat Static/Hyperlink items
   [avatar Image] <nick> <time> <body...>   repeated per message
(the avatar is an Image with an empty name; inline emoticons are Images WITH a name; an image/sticker message is
a Hyperlink with an empty name). The avatar is the reliable message boundary, so:
  - date headers / system lines that sit between a body and the next avatar are not glued onto that body
  - a body that merely looks like a time ("10:30") cannot start a new message
and the message box = a Pane titled 'camfrog://wb-edit-data.inside/' (a web editor, not an Edit control)."""

from __future__ import annotations

import logging
import re

log = logging.getLogger("autodj")

TIME_RX = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AaPp][Mm])?$")


def tokens_to_lines(tokens: list[str]) -> list[str]:
    """Flat texts -> 'H:MM nick: body' lines. A time token marks a message: the token before it is the
    nick, everything up to the next message's nick is the body. Partial/cut-off messages are skipped."""
    toks = [t.replace("\xa0", " ").strip() for t in tokens]
    idx = [i for i, t in enumerate(toks) if i > 0 and TIME_RX.match(t)]
    out = []
    for n, i in enumerate(idx):
        end = idx[n + 1] - 1 if n + 1 < len(idx) else len(toks)
        nick = toks[i - 1].replace(":", " ").strip()
        body = " ".join(t for t in toks[i + 1 : max(end, i + 1)] if t)
        if nick and body:
            out.append(f"{toks[i]} {nick}: {body}")
    return out


def items_to_lines(items: list[tuple[str, str]], strict: bool = True) -> list[str]:
    """items = (kind, name) with kind in avatar | emo | text | link, in document order.
    Messages are split at avatars; a group is [nick, time, body...]. With strict=True a second plain text
    directly after the first body segment (no emoticon/link between) is a date header or system line and is
    dropped. Groups before the first avatar are partial (cut off by the tail window) and are skipped."""
    groups: list[list[tuple[str, str]]] = []
    seen_avatar = False
    for kind, name in items:
        if kind == "avatar":
            groups.append([])
            seen_avatar = True
        elif seen_avatar:
            groups[-1].append((kind, name))
    out = []
    for g in groups:
        g = [(k, n.replace("\xa0", " ").strip()) for k, n in g]
        toks = [(k, n) for k, n in g if k != "emo" or n]  # keep emoticons as joiners
        if (
            len(toks) < 3
            or toks[0][0] not in ("text", "link")
            or toks[1][0] != "text"
            or not TIME_RX.match(toks[1][1])
        ):
            continue
        nick = toks[0][1].replace(":", " ").strip()
        body: list[str] = []
        prev: str | None = None
        for k, n in toks[2:]:
            if k == "emo":
                prev = "emo"
                continue
            if k == "link" or not body or prev in ("emo", "link") or not strict:
                if n:
                    body.append(n)
                prev = k
            else:
                break  # adjacent plain text = date header / system line
        text = " ".join(body)
        if nick and text:
            out.append(f"{toks[1][1]} {nick}: {text}")
    return out


def find_web_panes(win, view_title: str, input_title: str):
    """(history pane, message-box pane) of a room window, either may be None."""
    view = inp = None
    try:
        panes = win.descendants(control_type="Pane")
    except Exception:
        return None, None
    for p in panes:
        try:
            name = p.element_info.name or ""
        except Exception:
            continue
        if view is None and view_title and view_title in name:
            view = p
        elif inp is None and input_title and input_title in name:
            inp = p
    if view is None:
        log.debug(
            "web pane not found (view_title=%r): %d pane(s) checked; "
            "run AutoDJ.exe --discover to update config.toml",
            view_title,
            len(list(panes)) if hasattr(panes, "__len__") else -1,
        )
    return view, inp


def _history_children(view):
    node = view.element_info
    for _ in range(
        8
    ):  # unwrap single-child wrapper panes down to the flat message list
        kids = node.children()
        if len(kids) == 1 and kids[0].control_type == "Pane":
            node = kids[0]
            continue
        break
    return node, kids


def read_items(view, tail: int = 600) -> list[tuple[str, str]]:
    """Newest `tail` direct children as (kind, name): avatar | emo | text | link."""
    _node, kids = _history_children(view)
    items = []
    for k in kids[-tail:]:
        try:
            ct, name = k.control_type, k.name or ""
        except Exception:
            continue
        if ct == "Image":
            items.append(("emo", name) if name else ("avatar", ""))
        elif ct == "Text" and name:
            items.append(("text", name))
        elif ct == "Hyperlink" and name:
            items.append(("link", name))
    return items


def read_tokens(view, tail: int = 600) -> list[str]:
    """Texts only (legacy path, used when no avatar images are exposed)."""
    return [n for k, n in read_items(view, tail) if k in ("text", "link")]


def read_web(view, tail: int = 600, strict: bool = True) -> list[str]:
    items = read_items(view, tail)
    if any(k == "avatar" for k, _ in items):
        return items_to_lines(items, strict)
    return tokens_to_lines(
        [n for k, n in items if k in ("text", "link")]
    )  # no avatars exposed: old heuristic
