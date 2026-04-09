#!/usr/bin/env node
/**
 * Create/update patches from modified files in gn/
 */

const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')
const util = require('./lib/util')

async function getModifiedFiles() {
  try {
    const output = execSync('git diff --diff-filter=M --name-only --ignore-space-at-eol', {
      cwd: util.GN_DIR,
      encoding: 'utf8'
    })
    return output.split('\n').filter(s => s.length > 0)
  } catch {
    return []
  }
}

function getPatchedFileChecksum(filePath) {
  // Get checksum of currently modified file (the patched state)
  const targetPath = path.join(util.GN_DIR, filePath)
  if (fs.existsSync(targetPath)) {
    return util.calculateChecksum(targetPath)
  }
  return null
}

async function writePatchFile(filePath) {
  const patchName = util.pathToPatchName(filePath)
  const patchPath = path.join(util.PATCHES_DIR, patchName)
  const patchInfoPath = patchPath + 'info'

  // Generate patch contents
  const patchContents = execSync(
    `git diff --src-prefix=a/ --dst-prefix=b/ --full-index "${filePath}"`,
    { cwd: util.GN_DIR, encoding: 'utf8' }
  )

  // Check if patch already exists with same content
  if (fs.existsSync(patchPath)) {
    const existingContents = fs.readFileSync(patchPath, 'utf8')
    if (existingContents === patchContents) {
      return { patchName, updated: false }
    }
  }

  // Write patch file
  fs.writeFileSync(patchPath, patchContents)

  // Write patchinfo file
  const patchChecksum = util.calculateChecksum(patchPath)
  const patchedChecksum = getPatchedFileChecksum(filePath)

  const patchInfo = {
    schemaVersion: 1,
    patchChecksum,
    appliesTo: [{
      path: filePath,
      checksum: patchedChecksum
    }]
  }
  fs.writeFileSync(patchInfoPath, JSON.stringify(patchInfo))

  console.log(`Updated: ${util.fmt.bold}${util.fmt.green}${patchName}${util.fmt.reset}`)
  return { patchName, updated: true }
}

async function removeStalePatchFiles(currentPatchNames) {
  if (!fs.existsSync(util.PATCHES_DIR)) return 0

  const existingPatches = fs.readdirSync(util.PATCHES_DIR)
    .filter(f => f.endsWith('.patch'))

  let removedCount = 0
  for (const patch of existingPatches) {
    if (!currentPatchNames.includes(patch)) {
      const patchPath = path.join(util.PATCHES_DIR, patch)
      const patchInfoPath = patchPath + 'info'

      fs.unlinkSync(patchPath)
      if (fs.existsSync(patchInfoPath)) {
        fs.unlinkSync(patchInfoPath)
      }
      console.log(`Removed: ${util.fmt.bold}${util.fmt.red}${patch}${util.fmt.reset}`)
      removedCount++
    }
  }
  return removedCount
}

async function main() {
  util.logStart('update_patches')
  console.log(util.SEPARATOR)

  // Ensure patches directory exists
  fs.mkdirSync(util.PATCHES_DIR, { recursive: true })

  // Get modified files
  const modifiedFiles = await getModifiedFiles()

  // Create/update patches
  const patchNames = []
  let updatedCount = 0
  for (const file of modifiedFiles) {
    const { patchName, updated } = await writePatchFile(file)
    patchNames.push(patchName)
    if (updated) updatedCount++
  }

  // Remove stale patches (patches that no longer have corresponding modifications)
  const removedCount = await removeStalePatchFiles(patchNames)

  console.log(util.SEPARATOR)
  util.logFinish('update_patches')
}

main().catch(err => {
  console.error('Error:', err.message)
  process.exit(1)
})
