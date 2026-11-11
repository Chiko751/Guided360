# Building

`dist/index.js` is **not** hand-written. It is generated from the compiled Game Glance bundle (`orig/game-glance/dist/index.js`)
by a set of patch scripts (`work/patch.py`, `work/stage2.py`, snippets in `work/snip/`, styles in `work/skin.js`,
translations in `work/i18n/`), followed by tree-shaking (`esbuild`) and dead-code pruning (`acorn`).

The build tree lives in the development folder of the maintainer. To publish it here, copy these into the repository root:

```
orig/   work/   tests/   tools/   build.sh   package-lock.json (if any)
```

Then:

```bash
npm install        # esbuild, acorn
./build.sh         # prints BUILD_OK
```

Add the upstream Game Glance `dist` and `py_modules` under `orig/game-glance/` (MIT, keep its `LICENSE`).
