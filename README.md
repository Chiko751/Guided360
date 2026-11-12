# Guided360

An Xbox 360 NXE style **Guide menu for Steam Game Mode** (SteamOS, Bazzite, …), packaged as a [Decky Loader](https://decky.xyz) plugin.
Press the Steam button and get the familiar blade layout: Downloads, Quick settings, your profile/main menu, Performance, Plugins and a Media Player – or one of 14 presets in the style of Xbox, PlayStation, Nintendo, Steam and Steam Deck.

> **Based on [Game Glance](https://github.com/michpalm/game-glance) by Michael Palma (MIT).**
> Guided360 is a derivative work: it keeps only the menu and re-skins and extends it. See [Credits](#credits).

<p>
<img src="docs/image.png" width="32%"> <img src="docs/xbox360-plugins.png" width="32%"> <img src="docs/xbox360-power.png" width="32%">
</p>

## Features

- **Guide menu** with quick settings (brightness, volume, microphone, Wi-Fi, Bluetooth and its devices, airplane mode, night mode, do not disturb, text size) and every option of Steam's Performance menu – each element can be hidden – plus downloads, friends with chat, notifications and user switching
- **My games** (recent games and library, per-game options), **Achievements** in NXE style, **Friends** sorted by latest chat, with per-friend actions (message, voice, join, invite, profile, nickname, Remote Play Together, trade …)
- **Controller window**: controllers, player order, layouts – and editing of button bindings, input styles, activators and mode settings right in the Guide
- **Media Player** tab: Spotify (the installed app, invisible in the background) or YouTube Music (sign in through Steam's browser) – your playlists, play/pause, previous/next; music keeps playing while you game
- **Quick Resume** tab for running apps plus a window switcher on the in-game tab (experimental; works best with the "Pause Games" plugin)
- **System & Power** view (sleep, restart, shut down, desktop, restart Steam / Guided360) and **Update Guided360** straight from GitHub
- **Plugins tab**: Decky plugins inside the Guide (windows grow with their content), buttons for Decky settings and store, and **+** to install a plugin from a ZIP with a file browser right in the Guide
- **14 presets**: Xbox – **Modern-NXE** (default), **Classic NXE** (the 2008 guide, curved blades and player ring), **Metro** (2011 dashboard), **Modern NXE Dark**, **Liquid Glass**, **Dynamic** (colours from the running game's artwork); PlayStation – **PS5**, **PS3**; Nintendo – **Switch** light / dark; Steam – **Big Picture**, **2004**; **Steam Deck** and **Steam Deck OLED**. A preset sets colours, shapes, sizes, font and button symbols
- **8 layouts**: Modern / Classic / Metro blades, tabs on top, dock at the bottom, sidebar left, rail right, stacked cards – with window position (left / centre / right, top / bottom)
- **Fine-tuning**: layout independent of the preset, custom themes (rename, delete), name banner on every page or the main page only, profile picture ring (colours, rainbow), scaling, colours (window colour incl. "Dynamic", window opacity and in-game blur for every style), text and font size, effects and sounds, player ring, glow, button symbols (Xbox / Nintendo / PlayStation, three sizes), hide/reorder tabs, choose the tab for Steam + A, remap buttons – every choice in a dropdown
- **Automatic update check** with a Steam notification (can be switched off)
- Sharp on every resolution and aspect ratio (4K TV, Steam Deck, Legion Go …)
- Languages: English, Deutsch, Español, Français, Português (or Auto from the Steam language)

## Install

1. Install [Decky Loader](https://decky.xyz).
2. Download the latest ZIP from [Releases](../../releases):
   `Guided360-vX.Y.Z.zip` (since 1.36 there is only one build – the former "Clean" variant is the setting *Appearance › Shapes › Banner*; if you used Guided360 Clean, remove it).
3. In Game Mode: Decky → settings (gear) → Developer → *Install plugin from ZIP*.
4. Restart Steam if the plugin does not appear.

**Updating:** Guided360 checks for a new release by itself (shortly after start, then every 6 hours) and shows a Steam notification – press it to update. You can also update any time via *Quick settings → System & Power → Update Guided360*. The update is installed through Decky (you confirm in Decky).

Settings live in the Guide itself (gear icon at the top left of the Guide).

## Status

Active hobby project, tested on a few Linux gaming setups only. **Not every Steam client version is covered**: Steam's internal menu code changes, and things like switching to Steam pages can break after a Steam update. Bug reports are very welcome – use the issue template and add a photo.

## Building from source

This repository holds the built plugin (`dist/index.js`) plus the Python backend. The plugin is produced by patching the compiled upstream Game Glance bundle; the build scripts are described in [`BUILDING.md`](BUILDING.md).

## Credits

- **Game Glance** by [Michael Palma](https://github.com/michpalm/game-glance), MIT – the foundation of this plugin.
- Fonts: Carlito, Inter, Poppins and Nunito (SIL OFL 1.1).
- Spotify and YouTube Music are used through their own apps/websites with your own account; Guided360 only controls them.
- hltb-for-deck by hulkrelax (MIT), via upstream.

Details in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) and [`LICENSE`](LICENSE).

## Disclaimer

Not affiliated with or endorsed by Valve, Microsoft, Sony, Nintendo, Spotify, Google or the Game Glance author. "Xbox", "Xbox 360", "PlayStation", "Nintendo Switch", "Steam", "Steam Deck", "Spotify", "YouTube Music" and "iOS" are trademarks of their owners and are used only to describe the visual inspiration.

## License

MIT. The original copyright notice (Michael Palma) is retained as required.

---

# Deutsch

Guided360 ist ein Guide-Menü im Xbox-360-NXE-Stil für den Steam Game Mode (Decky-Plugin), basierend auf **Game Glance** von Michael Palma (MIT). 14 Presets im Stil von Xbox, PlayStation, Nintendo, Steam und Steam Deck, 8 Layouts (Blades, Tabs oben, Dock, Seitenleiste, gestapelt …) und ein Media Player für Spotify und YouTube Music, der auch bei geschlossenem Guide weiterspielt.

**Installation:** ZIP aus den [Releases](../../releases) laden (`Guided360-vX.Y.Z.zip`; seit 1.36 gibt es nur noch diese Version – die frühere „Clean“-Variante ist die Einstellung Darstellung › Formen › Banner) und in Decky über Zahnrad → Entwickler → „Plugin aus ZIP installieren“ einspielen. Einstellungen findest du im Guide über das Zahnrad oben links.

**Update:** Guided360 prüft selbst auf neue Versionen und meldet sich mit einer Steam-Benachrichtigung (abschaltbar unter Einstellungen → System & Updates). Manuell: Schnelleinstellungen → System & Energie → „Update Guided360“.

**Hinweis:** Nach Steam-Updates kann einzelnes brechen (z. B. der Wechsel zu Steam-Seiten). Fehler bitte mit Foto als Issue melden.
