#!/usr/bin/env node
/**
 * Apply all patches from patches/ directory to gn/
 */

const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')
const util = require('./lib/util')

function checkPatchInfo(patchPath, isAlreadyApplied) {
  const patchInfoPath = patchPath + 'info'

  if (!fs.existsSync(patchInfoPath)) {
    return { warning: null }
  }

  try {
    const patchInfo = JSON.parse(fs.readFileSync(patchInfoPath, 'utf8'))

    // Check patch file checksum
    const currentPatchChecksum = util.calculateChecksum(patchPath)
    if (currentPatchChecksum !== patchInfo.patchChecksum) {
      return { warning: 'patch file was modified' }
    }

    // Check target file checksum (only if patch is already applied)
    // The patchinfo stores checksum of the patched state
    if (isAlreadyApplied) {
      for (const target of patchInfo.appliesTo) {
        const targetPath = path.join(util.GN_DIR, target.path)
        if (fs.existsSync(targetPath)) {
          const currentChecksum = util.calculateChecksum(targetPath)
          if (currentChecksum !== target.checksum) {
            return { warning: `patched file was modified: ${target.path}` }
          }
        }
      }
    }

    return { warning: null }
  } catch {
    return { warning: 'invalid patchinfo' }
  }
}

function applyPatches(standalone = false) {
  if (standalone) {
    util.logStart('apply_patches')
    console.log(util.SEPARATOR)
  }

  // Ensure patches directory exists
  if (!fs.existsSync(util.PATCHES_DIR)) {
    console.log('No patches directory found.')
    return
  }

  // Get all .patch files
  const patches = fs.readdirSync(util.PATCHES_DIR)
    .filter(f => f.endsWith('.patch'))
    .sort()

  if (patches.length === 0) {
    console.log('No patches to apply.')
    return
  }

  console.log(`Applying ${patches.length} patch(es)...`)

  for (const patch of patches) {
    const patchPath = path.join(util.PATCHES_DIR, patch)
    process.stdout.write(`- Applying ${util.fmt.bold}${patch}${util.fmt.reset}`)

    try {
      // Check if already applied
      let isAlreadyApplied = false
      try {
        execSync(`git apply --check --reverse "${patchPath}"`, {
          cwd: util.GN_DIR,
          stdio: 'pipe'
        })
        isAlreadyApplied = true
      } catch {
        // Not applied yet
      }

      // Check patchinfo (pass whether patch is already applied)
      const { warning } = checkPatchInfo(patchPath, isAlreadyApplied)
      if (warning) {
        console.log(`(warning: ${warning})`)
      } else {
        console.log('')
      }

      if (isAlreadyApplied) {
        console.log(`  ${util.fmt.bold}${util.fmt.yellow}Skipped.${util.fmt.reset}`)
        continue
      }

      // Apply the patch
      execSync(`git apply "${patchPath}"`, {
        cwd: util.GN_DIR,
        stdio: 'pipe'
      })
      console.log(`  ${util.fmt.bold}${util.fmt.green}Done.${util.fmt.reset}`)
    } catch (err) {
      console.log(`  ${util.fmt.bold}${util.fmt.red}Failed.${util.fmt.reset}`)
      console.error(`    Error: ${err.message}`)
      process.exit(1)
    }
  }

  console.log('All patches applied successfully!')

  if (standalone) {
    console.log(util.SEPARATOR)
    util.logFinish('apply_patches')
  }
}

// Allow both direct execution and require()
if (require.main === module) {
  applyPatches(true)
}

module.exports = applyPatches
