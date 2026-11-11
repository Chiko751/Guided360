# Guided360

An Xbox 360 NXE style **Guide menu for Steam Game Mode** (SteamOS, Bazzite, …), packaged as a [Decky Loader](https://decky.xyz) plugin.
Press the Steam button and get the familiar blade layout: Downloads, Quick settings, your profile/main menu, Performance and Plugins. 

> **Based on [Game Glance](https://github.com/michpalm/game-glance) by Michael Palma (MIT).**
> Guided360 is a derivative work: it keeps only the menu and re-skins and extends it. See [Credits](#credits).

<p>
<img src="docs/image.png" width="32%"> <img src="docs/xbox360-plugins.png" width="32%"> <img src="docs/xbox360-power.png" width="32%">
</p>

## Features

- **Guide menu** with quick settings (brightness, volume, microphone, Wi-Fi, Bluetooth devices), performance controls, downloads, friends with chat, notifications and user switching
- **My games** (recent games and library, per-game options), **Achievements** in NXE style, **Friends** with Favorites/Friends tabs
- **Controller window**: controllers, player order, layouts – and editing of button bindings, input styles, activators and mode settings right in the Guide
- **Quick Resume** tab plus a running-app and window switcher (experimental; works best with the "Pause Games" plugin)
- **System & Power** view (sleep, restart, shut down, desktop, restart Steam / Guided360) and **Update Guided360** straight from GitHub
- **Plugins tab**: Decky plugins inside the Guide (windows grow with their content), buttons for Decky settings and store, and **+** to install a plugin from a ZIP with a file browser right in the Guide
- **Styles**: **Modern-NXE** (default), **Classic NXE** (the 2008 guide, curved blades and player ring), **Metro** (2011 dashboard), **360 Slate**, **Liquid Glass** (tint, opacity and in-game blur), **Dynamic** (accent, blades and window colour from the running game's artwork)
- **Fine-tuning**: scaling, colours (window colour incl. "Dynamic", window opacity and in-game blur for every style), text and font size, animations and sounds, player ring, glow effect for legend and icons, monochrome button icons, hide/reorder tabs, choose the tab for Steam + A, remap buttons
- Sharp on every resolution and aspect ratio (4K TV, Steam Deck, Legion Go …)
- Languages: English, Deutsch, Español, Français, Português (or Auto from the Steam language)

## Install

1. Install [Decky Loader](https://decky.xyz).
2. Download the latest ZIP from [Releases](../../releases):
   - `Guided360-vX.Y.Z.zip` – standard build
   - `Guided360-Clean-vX.Y.Z.zip` – "Clean" build (the vertical name banner only on the main page)
   Install only one of them.
3. In Game Mode: Decky → settings (gear) → Developer → *Install plugin from ZIP*.
4. Restart Steam if the plugin does not appear.

**Updating:** in the Guide open *Quick settings → System & Power → Update Guided360*. It checks the latest release here and installs it through Decky (you confirm in Decky).

Settings live in the Guide itself (gear icon at the top left of the Guide).

## Status

Active hobby project, tested on a few Linux gaming setups only. **Not every Steam client version is covered**: Steam's internal menu code changes, and things like switching to Steam pages can break after a Steam update. Bug reports are very welcome – use the issue template and add a photo.

## Building from source

This repository holds the built plugin (`dist/index.js`) plus the Python backend. The plugin is produced by patching the compiled upstream Game Glance bundle; the build scripts are described in [`BUILDING.md`](BUILDING.md).

## Credits

- **Game Glance** by [Michael Palma](https://github.com/michpalm/game-glance), MIT – the foundation of this plugin.
- Fonts: Carlito, Inter, Poppins and Nunito (SIL OFL 1.1).
- hltb-for-deck by hulkrelax (MIT), via upstream.

Details in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) and [`LICENSE`](LICENSE).

## Disclaimer

Not affiliated with or endorsed by Valve, Microsoft, Sony or the Game Glance author. "Xbox", "Xbox 360", "PlayStation" and "iOS" are trademarks of their owners and are used only to describe the visual inspiration.

## License

MIT. The original copyright notice (Michael Palma) is retained as required.

---

# Deutsch

Guided360 ist ein Guide-Menü im Xbox-360-NXE-Stil für den Steam Game Mode (Decky-Plugin), basierend auf **Game Glance** von Michael Palma (MIT). Stile: Modern-NXE, Classic NXE, Metro, 360 Slate, Liquid Glass und Dynamic.

**Installation:** ZIP aus den [Releases](../../releases) laden (`Guided360` oder `Guided360-Clean`, nur eine davon) und in Decky über Zahnrad → Entwickler → „Plugin aus ZIP installieren“ einspielen. Einstellungen findest du im Guide über das Zahnrad oben links.

**Update:** Im Guide unter Schnelleinstellungen → System & Energie → „Update Guided360“.

**Hinweis:** Nach Steam-Updates kann einzelnes brechen (z. B. der Wechsel zu Steam-Seiten). Fehler bitte mit Foto als Issue melden.
