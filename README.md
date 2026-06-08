# latrodectus-gn

Latrodectus GN build system with custom extensions for target modification.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run init` | Initialize the project (clone gn submodule) |
| `npm run sync` | Sync gn submodule to latest |
| `npm run build` | Build the gn binary to `out/gn` |
| `npm run apply_patches` | Apply patches from `patches/` to `gn/` |
| `npm run update_patches` | Update patches from current `gn/` changes |
| `npm run format` | Format C++ source files |
| `npm run deploy` | Deploy built binary |
| `npm test` | Run integration tests |
| `npm run test:verbose` | Run tests with verbose output |
| `npm run test:debug` | Run tests with ninja/gn output |
