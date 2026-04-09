#!/usr/bin/env node
/**
 * Sync: Reset gn/ to target commit and apply patches
 */

const util = require('./lib/util')

async function main() {
  util.logStart('sync')
  console.log(util.SEPARATOR)

  // Check gn/ exists
  if (!util.gnDirExists()) {
    console.error('Error: gn/ not found. Run "npm run init" first.')
    process.exit(1)
  }

  const targetCommit = util.getGnVersion()
  console.log(`Target gn version: ${targetCommit}`)

  console.log(util.SEPARATOR)

  // Reset to target commit
  console.log('Resetting gn to target commit...')
  util.runGit(util.GN_DIR, ['fetch', '-q', 'origin'])
  util.runGit(util.GN_DIR, ['checkout', '-q', targetCommit])
  util.runGit(util.GN_DIR, ['reset', '--hard', '-q', targetCommit])
  util.runGit(util.GN_DIR, ['clean', '-fdx', '-q'])

  console.log(util.SEPARATOR)

  // Apply patches
  console.log('Applying patches...')
  require('./applyPatches')()

  console.log(util.SEPARATOR)
  util.logFinish('sync')
}

main().catch(err => {
  console.error('Error:', err.message)
  process.exit(1)
})
