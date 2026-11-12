# Changelog

## 1.37.0
**Media Player, rebuilt after the Xbox 360 media blade**
- Top: *Spotify library* and *YouTube Music library*, each on its own page. Playlists and albums open their **track list** – start a single track (it plays inside its playlist) or "Play all".
- Bottom: **one player** for whatever is playing – cover with a small source badge (Spotify green / YouTube Music red), play/pause, previous, **stop**, next, **shuffle** (handed to the running player) and a floating **volume** scale (up/down, A or B closes); title, time and a progress line underneath, a little equaliser while music plays.
- Only one source plays at a time: starting one pauses the other; if both run (e.g. Spotify started from the phone), the one started last wins.
- Spotify: the whole library (playlists, albums, artists, podcasts, Liked Songs), read from the app itself – no longer only what its sidebar showed. Covers for mixed playlists fixed.
- YouTube Music: Guided always controls its own invisible player, never a YouTube Music tab you opened in Steam's browser; it picks up a sign-in made there automatically, keeps your volume when you switch playlists and replaces its player by itself if it ever stops responding.
- Help: the Tabs page lists the Media Player; the Media Player help describes the new layout.

## 1.36.0
**Media Player**
- New **Media Player** tab (can be hidden under Guided › Tab settings), like the media player in the Xbox 360 guide: **Spotify** or **YouTube Music**, with now playing (cover, title, artist, progress), previous / play-pause / next and your own library.
- Spotify uses the installed Spotify app (Flatpak `com.spotify.Client`, signed in once); Guided starts it invisibly in the background and lists your playlists, albums and Liked Songs.
- YouTube Music runs in an invisible Steam browser; "Sign in to YouTube Music" opens the sign-in in Steam's browser (shared cookies). Without sign-in you get recommendations.
- Music keeps playing while the Guide is closed and while you play; starting one source pauses the other.

**Presets and layouts**
- 14 presets: Xbox (Modern NXE, Classic NXE, Modern NXE Dark, Liquid Glass, Dynamic, Metro), PlayStation (PS5, PS3), Nintendo (Switch light / dark), Steam (Big Picture, 2004), Steam Deck (Deck, OLED). A preset now sets the whole look – colours, shapes, sizes, font and button symbols.
- 8 layouts: Modern, Classic, Metro blades, tabs on top, dock at the bottom, sidebar left, rail right and **stacked cards**. Vertical layouts get a tab list you reach with left (right for the rail), up/down switches tabs; LB/RB work everywhere.
- Window position horizontal and vertical (centre / left / right, top / bottom), with equal margins.
- **One build only:** the former "Clean" build is now the setting *Appearance › Shapes › Banner* (on every page / main page only). If you used Guided360 Clean, install Guided360 and remove the Clean plugin.

**Appearance**
- Profile picture ring on/off, colours and rainbow; more accent, window, tab and text colours.
- "Reset appearance" resets only the look; "Reset all" keeps your custom themes. Custom themes can be renamed (✎).
- PlayStation button symbols centred, glow colours per symbol (✕ blue, ○ red, □ pink, △ green).
- Light windows (e.g. Switch) keep icons, switches, friends and library readable.

**Settings, navigation, plugins**
- Settings restructured: Appearance (Shapes, Colours, Text & symbols, Effects & sound), Guided (page and tab settings), Controller & Keyboard, System & updates, Help. The settings window grows while open; tabs stay visible but locked.
- Back (B) returns to the row that opened a page. Long pages scroll fully to the top/bottom.
- Dropdowns of embedded Decky plugins open in the Guide's own dropdown; after a Steam dialog the Guide returns to the plugin. Plugins can request a wider window (`data-gx-panel-width`).
- "+" install shows a progress bar and a notification when Decky has loaded the plugin.
- Quick settings without gaps when elements are hidden.
- Help rewritten for the current menus and layouts; missing translations added; words no longer break mid-word in narrow windows.
- Fix: no more "missing localization token" errors logged by Steam.

## 1.33.0
- Settings reorganised: Language, Appearance, Elements, Tabs & menu, Quick settings, Performance, Buttons, Keyboard, System & updates, Help. Glow moved to "Effects & sound", monochrome icons to "Buttons", auto-update and reset to "System & updates"; section headings on Elements, Tabs and Buttons.
- Every choice (language, style, shape, font, colours, tab colour, button mapping, Steam + A tab, glyphs …) opens a dropdown instead of cycling through the values.
- Help texts updated. Code clean-up (removed legacy glass tint, old app-switcher row and unused rules).

## 1.32.0 – 1.32.1
- Quick settings in a fixed two-column layout: Wi-Fi | Bluetooth, Airplane mode | Bluetooth devices, Do not disturb | Night mode; text size slider (Steam's display scaling).
- Performance tab with every option of Steam's Performance menu (incl. tearing, half-rate shading, scaling mode/filter, sharpness, TDP, GPU clock); scaling names straight from Steam's own localisation.
- Every element of Quick settings and Performance can be hidden in the settings.
- Predictable up/down navigation on both pages (row above/below, nearest column).
- Small bouncing "more below" arrow when a page scrolls (once you reached the end it stays away until the Guide is closed; can be switched off).
- Button symbol size small / medium / large. Metro shape: blades always flush with the window.

## 1.31.0
- Automatic update check (90 s after start, then every 6 h, one small conditional GitHub request) with a Steam notification; press it to update.
- Button symbols: Xbox, Nintendo (A/B and X/Y swapped) or PlayStation (✕ ○ □ △).

## 1.30.0
- Friends: sorted by latest chat; the chat opens to the right only when you start it (list becomes compact); per-friend buttons for message, voice chat, join game, invite, and a "More" menu (profile, nickname, Remote Play Together, favourites, trade, inventory, remove, block).
- With Steam's own keyboard open the Guide moves right above it and grows.

## 1.29.0 – 1.29.2
- Fix: the in-game blur slider had no effect on HDR displays.
- Shape setting independent of the style; save the current look as a custom theme (also "save game colours" on the Dynamic hero); style picker with delete.
- Keyboard settings: built-in keyboard on/off, size, tools in the keyboard strip; Steam keyboard detection.
- "360 Slate" renamed to "Modern NXE Dark"; tab colour "Like preset".

## 1.28.1
- Fix: quitting a game from the Guide while another game keeps running no longer leaves Steam's own side menu open.

## 1.28.0
- "+" in the Plugins tab opens a ZIP file browser inside the Guide; Decky installs in the background.
- Window colour option "Dynamic" (from the running game's hero); the Dynamic preset uses it by default.
- Window opacity and in-game blur for every preset (Appearance → Colours); the separate Glass page is gone.

## 1.27.1
- "Power" is now called "System & Power" (DE: "System & Energie").

## 1.16 – 1.27.0
- New styles Classic NXE and Metro; all presets on the Xbox 360 layout; Liquid Glass (tint/opacity/blur) and Dynamic (hero colours) reworked; default renamed to Modern-NXE.
- My games, Achievements, Friends tabs, Controller window with binding editor, Quick Resume, power menu with update from GitHub.
- Plugins tab: Decky settings/store/"install from ZIP" buttons, plugin windows grow with their content.
- Settings reorganised; Steam + A tab choice; slider edit mode; header navigation; player ring; glow effect; mono icons; Nunito font.
- Sharper rendering on all resolutions; Xbox 360 open/close animations.

## 1.15.2
- Beta release.

## 1.10 – 1.15
- Running-app switcher at the bottom of the main menu and window list on the in-game tab (experimental).
- Fixes around switching from the Guide to Steam pages, plugin list layout, power view.

## 1.9
- Power view inside the Guide, Slate restyled like the original NXE tabs, smaller tab icons, shorter titles.

## 1.5 – 1.8
- Language selector (English, Deutsch, Español, Français, Português).
- Styles reduced to Xbox 360 (default), 360 Slate, Liquid Glass, Dynamic and Console.
- Dynamic style: colours follow the artwork of the current game.

## Earlier
- Forked from Game Glance by Michael Palma; everything except the menu was removed and the menu re-skinned.
