#!/usr/bin/env node
/**
 * Build latrodectus-gn
 */

const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')
const util = require('./lib/util')

function findNinja() {
  const candidates = [
    '/opt/homebrew/bin/ninja',
    '/usr/local/bin/ninja',
    path.join(process.env.HOME, 'latrodectus-browser/src/third_party/ninja/ninja'),
  ]

  // Try system ninja first
  try {
    execSync('ninja --version', { stdio: 'pipe' })
    return 'ninja'
  } catch {}

  // Try candidates
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate
    }
  }

  return null
}

async function main() {
  util.logStart('build')
  console.log(util.SEPARATOR)

  // Find ninja
  const ninja = findNinja()
  if (!ninja) {
    console.error('Error: ninja not found. Install with: brew install ninja')
    process.exit(1)
  }

  // Generate build files using our wrapper (not the upstream gen.py)
  // Note: gen.py changes to gn/ dir, so out-path is relative to gn/
  console.log('Generating build files...')
  execSync('python3 build/gen.py --out-path=../out', { cwd: util.ROOT_DIR, stdio: 'inherit' })

  console.log(util.SEPARATOR)

  // Run ninja build
  console.log(`Building with ${ninja}...`)
  execSync(`${ninja} -C out`, { cwd: util.ROOT_DIR, stdio: 'inherit' })

  console.log(util.SEPARATOR)

  console.log('Binary at: out/gn')

  console.log(util.SEPARATOR)
  util.logFinish('build')
}

main().catch(err => {
  console.error('Error:', err.message)
  process.exit(1)
})
