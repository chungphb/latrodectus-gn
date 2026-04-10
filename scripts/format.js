#!/usr/bin/env node
/**
 * Format C++ files using clang-format
 */

const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')
const util = require('./lib/util')


function main() {
  util.loadEnv()

  util.logStart('format')
  console.log(util.SEPARATOR)

  // Find clang-format via CHROMIUM_SRC or CHROMIUM_BUILDTOOLS_PATH
  let buildtoolsPath = process.env.CHROMIUM_BUILDTOOLS_PATH
  if (!buildtoolsPath && process.env.CHROMIUM_SRC) {
    buildtoolsPath = path.join(process.env.CHROMIUM_SRC, 'buildtools')
    process.env.CHROMIUM_BUILDTOOLS_PATH = buildtoolsPath
  }

  if (!buildtoolsPath) {
    console.error('Error: CHROMIUM_SRC not set')
    console.error('Create a .env file with:')
    console.error('  CHROMIUM_SRC=/path/to/chromium/src')
    process.exit(1)
  }

  // Get files to format from args, or default to chromium_src/
  const args = process.argv.slice(2)
  const files = args.length > 0 ? args : ['chromium_src/']

  for (const file of files) {
    const fullPath = path.join(util.ROOT_DIR, file)
    console.log(`Formatting: ${file}`)
    try {
      execSync(`find ${fullPath} -name "*.cc" -o -name "*.h" | xargs clang-format -i`, {
        cwd: util.ROOT_DIR,
        stdio: 'inherit'
      })
    } catch (err) {
      console.error(`Failed to format: ${file}`)
    }
  }

  console.log(util.SEPARATOR)
  util.logFinish('format')
}

main()
