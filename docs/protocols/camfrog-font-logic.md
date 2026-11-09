# Camfrog Desktop Client — Font Logic (REA Evidence)

Source: REA reverse-engineering of `camfrog.exe` (sha256: `0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06`)

## Key Finding: No Rich Text in Outgoing Messages

Camfrog desktop client **does not support rich text** in outgoing chat messages. All messages sent via UI Automation are plain text only.

Font styling is **client-side only** — each user controls their own display font locally. The bot cannot change how its messages appear in other users' clients.

## GDI Font API Imports (3 confirmed)

| Import | DLL | Purpose |
|--------|-----|---------|
| `CreateFontIndirectW` | GDI32.dll | Create logical font from `LOGFONTW` structure |
| `EnumFontFamiliesExW` | GDI32.dll | Enumerate installed font families |
| `ChooseFontW` | COMDLG32.dll | Standard Windows Font Dialog |

No HTML/CSS/BBCode/RTF parsing libraries are imported.

## Font-Related Strings (302 matches)

### Chat/Message Fonts (function `sub_140437e60`)

| String | Purpose |
|--------|---------|
| `main_font` | Primary chat message font |
| `gray_font` | System/grayed text |
| `white_font` | White text (dark mode) |
| `white_transparent_font` | Transparent background white text |
| `link_font` | Hyperlink font |
| `button_font` | Button text |
| `button_no_font` | Button disabled state |
| `main_no_font` | Main font disabled |
| `gray_no_font` | Gray font disabled |
| `groupbox_font` | Group box labels |

### IM/Private Message Fonts (functions `sub_1404adc70`, `sub_1409fe530`)

| String | Purpose |
|--------|---------|
| `IMFont` | Instant message font name |
| `IMFontSize` | Instant message font size |
| `FontName` | Font name setting |
| `im_and_chat_im_font` | Combined IM/chat font |

### Font Settings UI (functions `sub_1403c2100`, `sub_1403c39a0`, `sub_1403c3c80`, `sub_1403c3df0`, `sub_1403c4170`, `sub_1403c28f0`, `sub_1403c3080`)

| Control | Strings |
|---------|---------|
| Font name combo | `fontname_combo_font` (×5 refs) |
| Font size combo | `size_combo_font` (×5 refs) |
| Color combo | `color_combo_font` (×5 refs) |
| Bold | `bold_font` (×4 refs) |
| Italic | `italic_font` (×4 refs) |
| Underline | `underline_font` (×4 refs) |

### HTML/CSS Rendering (function `sub_140446470`, `sub_14097a240`, `sub_140974310`, `sub_140976980`)

Camfrog renders **incoming** messages with HTML-like CSS internally:

```html
<!-- Username links in chat -->
<a class='username' style='color: %1%; font-weight: %2%; text-decoration: underline;' href='camfrog:room:openvideo:%3%'>%4%</a>
<span class='username' style='color: %1%; font-weight: %2%;'>%3%</span>

<!-- General HTML -->
<P style=" color: #808080; font-family: Segoe UI; font-size: 10pt; text-align: center;">

<!-- Inline styles -->
font-weight: bold;
font-style: italic;
font-size: ;
font-family: ;
```

**Important:** This HTML/CSS is for **incoming message rendering only** (display). Outgoing messages sent via UIA are plain text — no HTML, no CSS, no rich text.

## Registry/Config Keys

| Key | Purpose |
|-----|---------|
| `IMFont` | Instant message font name |
| `IMFontSize` | Instant message font size |
| `FontName` | General font name |
| `FontName_VCHR` | Video chat room font |

## Implications for AutoDJ

| Feature | Supported? | How |
|---------|-----------|-----|
| Bot's own message font in room | **NO** | Recipient controls their own display font client-side |
| Font preview in AutoDJ GUI | **YES** | Tkinter preview panel only (config: `message_style`) |
| Bold/Italic/Underline in chat | **NO** | Plain text only via UIA |
| Color in chat | **NO** | Plain text only via UIA |
| Font size in chat | **NO** | Plain text only via UIA |

## AutoDJ `message_style` Config (GUI Preview Only)

```toml
message_style = {
  font_family = "Consolas",
  font_size = 14,
  font_color = "#FF0000",
  bold = false,
  italic = false,
  underline = false
}
```

This configuration is used **only** for the FontEditor preview panel in the AutoDJ Settings GUI. Sent messages are always plain text.

## Evidence Files

| Evidence ID | Operation | Subject |
|-------------|-----------|---------|
| `ev_2572ae388956` | `native_functions_search` pattern "font" | camfrog.exe |
| `ev_127165a14cd5` | `native_strings_find` pattern "font" | camfrog.exe |
| `ev_3690a6d9e0bf` | `native_strings_find` pattern "IMFont" | camfrog.exe |
| `ev_11c7ce39e195` | `native_strings_find` pattern "SetFontStyles" | camfrog.exe |