# Wendy — Color Picker Screen

## Purpose

The first screen the user sees when launching Wendy config mode. It captures a single preference — **light or dark mode** — before loading the rest of the UI with the appropriate color scheme applied.

---

## What It Stores

One value, picked by the user at launch:

| Value | Description |
|-------|-------------|
| `"light"` | Light terminal background, dark-on-light colors |
| `"dark"` | Dark terminal background, light-on-dark colors |

This value is passed directly into the main app and used to initialize the full color palette. It is not written to `settings.json` — it is a per-session choice made fresh each time Wendy starts.

---

## Visual Style

### Logo
The **WENDY** wordmark is rendered in ASCII art using the `doom` figlet font, displayed in **bold red**, centered horizontally. Red is Wendy's brand color and the only consistent color across both light and dark modes.

### Greeting
A single line of text appears below the logo — a Donna-from-Suits-style quip, picked randomly from three options at launch and **locked for the session** (it does not change as the user navigates). Rendered in **italics** and wrapped in `"quotes"`:

- *"Before we get started, let's make sure you can actually see me."*
- *"You're going to be staring at me all day. Choose wisely."*
- *"Aesthetics matter. Donna taught me that."*

### Divider
Removed. No divider between the greeting and the selection menu.

### Selection Menu
A minimal vertical list with two options — `LIGHT` and `DARK` — stacked top to bottom. Navigation is `↑ ↓` arrow keys, confirmed with `enter`.

- The **selected option** gets a `>` arrow indicator to its left in **red**, and renders with its full pill contrast (black-on-white for LIGHT, white-on-black for DARK)
- The **unselected option** renders dimmed, same pill style but faded
- No extra labels, no hints, no loading screen — selection goes straight through on confirm
- Content is vertically centered slightly below the midpoint of the terminal for visual balance

---

## Design Principles

- **No noise.** Every non-essential element was removed — no "choose your color mode" prompt, no loading flash, no keyboard hints.
- **Locked randomness.** The greeting is chosen once on launch so it never flickers or shifts while the user is on the screen.
- **Donna voice.** The assistant has personality from the first frame. Confident, direct, a little dry — no generic assistant language.
- **Terminal-native.** Everything is built with `curses` — no external UI libraries, no dependencies beyond the Python standard library.
