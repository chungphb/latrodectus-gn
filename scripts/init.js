#!/usr/bin/env node
/**
 * Initialize: Remove old gn/ and clone fresh
 */

const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')
const util = require('./lib/util')

async function main() {
  util.logStart('init')
  console.log(util.SEPARATOR)

  const targetCommit = util.getGnVersion()
  console.log(`Target gn version: ${targetCommit}`)

  console.log(util.SEPARATOR)

  // Remove old gn/ if exists
  if (fs.existsSync(util.GN_DIR)) {
    console.log('Removing old gn/...')
    fs.rmSync(util.GN_DIR, { recursive: true, force: true })
  }

  // Clone fresh
  console.log('Cloning gn...')
  execSync(`git clone ${util.GN_REPO} ${util.GN_DIR}`, { stdio: 'inherit' })

  console.log(util.SEPARATOR)

  // Checkout target commit
  console.log(`Checking out ${targetCommit}...`)
  util.runGit(util.GN_DIR, ['checkout', '-q', targetCommit])

  console.log(util.SEPARATOR)

  // Apply patches
  console.log('Applying patches...')
  require('./applyPatches')()

  console.log(util.SEPARATOR)
  util.logFinish('init')
}

main().catch(err => {
  console.error('Error:', err.message)
  process.exit(1)
})
