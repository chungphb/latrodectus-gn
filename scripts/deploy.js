#!/usr/bin/env node
/**
 * Deploy latrodectus-gn to latrodectus-browser
 *
 * Copies the built GN binary to the browser's buildtools directory.
 * Set CHROMIUM_SRC in .env to specify the browser source path.
 */

const fs = require('fs')
const path = require('path')
const util = require('./lib/util')

function getTargetPath() {
  // Check for CHROMIUM_SRC environment variable
  if (process.env.CHROMIUM_SRC) {
    return path.join(process.env.CHROMIUM_SRC, 'buildtools/mac/gn')
  }

  // Default: assume latrodectus-browser is sibling directory
  const defaultPath = path.resolve(util.ROOT_DIR, '..', 'latrodectus-browser/src/buildtools/mac/gn')
  return defaultPath
}

async function main() {
  util.loadEnv()

  util.logStart('deploy')
  console.log(util.SEPARATOR)

  const sourcePath = path.join(util.ROOT_DIR, 'out/gn')
  const targetPath = getTargetPath()
  const backupPath = targetPath + '.orig'

  // Check if source binary exists
  if (!fs.existsSync(sourcePath)) {
    console.error('Error: GN binary not found at', sourcePath)
    console.error('Run "npm run build" first to build the GN binary.')
    process.exit(1)
  }

  // Check if target directory exists
  const targetDir = path.dirname(targetPath)
  if (!fs.existsSync(targetDir)) {
    console.error('Error: Target directory not found:', targetDir)
    console.error('Set CHROMIUM_SRC in .env to point to your browser source directory.')
    process.exit(1)
  }

  // Backup original if it exists and backup doesn't exist yet
  if (fs.existsSync(targetPath) && !fs.existsSync(backupPath)) {
    console.log('Backing up original GN to', backupPath)
    fs.copyFileSync(targetPath, backupPath)
  }

  // Copy the new binary
  console.log('Copying GN binary...')
  console.log('  From:', sourcePath)
  console.log('  To:  ', targetPath)
  fs.copyFileSync(sourcePath, targetPath)

  // Ensure executable permissions
  fs.chmodSync(targetPath, 0o755)

  console.log(util.SEPARATOR)
  util.logFinish('deploy')
}

main().catch(err => {
  console.error('Error:', err.message)
  process.exit(1)
})
