const { execSync, spawn } = require('child_process')
const crypto = require('crypto')
const path = require('path')
const fs = require('fs')

const ROOT_DIR = path.resolve(__dirname, '..', '..')
const GN_DIR = path.join(ROOT_DIR, 'gn')
const PATCHES_DIR = path.join(ROOT_DIR, 'patches')
const VERSION_FILE = path.join(ROOT_DIR, '.gn-version')
const GN_REPO = 'https://gn.googlesource.com/gn'
const SEPARATOR = '----------------------------------------'

// ANSI formatting
const fmt = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  // Foreground colors
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  white: '\x1b[37m',
  // Background colors
  bgBlack: '\x1b[40m',
}

function loadEnv() {
  const envPath = path.join(ROOT_DIR, '.env')
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf8')
    for (const line of content.split('\n')) {
      const trimmed = line.trim()
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=')
        const value = valueParts.join('=')
        if (key && value && !process.env[key]) {
          process.env[key] = value
        }
      }
    }
  }
}

function logStart(scriptName) {
  console.log(`${fmt.bgBlack}${fmt.white}Start ${scriptName}${fmt.reset}`)
}

function logFinish(scriptName) {
  console.log(`${fmt.bgBlack}${fmt.white}Finish ${scriptName}${fmt.reset}`)
}

function run(cmd, args, options = {}) {
  const defaultOptions = { stdio: 'inherit', cwd: ROOT_DIR }
  const mergedOptions = { ...defaultOptions, ...options }
  console.log(`  > ${cmd} ${args.join(' ')}`)
  return execSync(`${cmd} ${args.join(' ')}`, mergedOptions)
}

function runGit(cwd, args, silent = false) {
  const options = { cwd, encoding: 'utf8' }
  if (silent) {
    options.stdio = 'pipe'
  }
  const result = execSync(`git ${args.join(' ')}`, options)
  return result ? result.trim() : ''
}

function getGnVersion() {
  if (!fs.existsSync(VERSION_FILE)) {
    throw new Error('.gn-version file not found')
  }
  return fs.readFileSync(VERSION_FILE, 'utf8').trim()
}

function gnDirExists() {
  return fs.existsSync(GN_DIR) && fs.existsSync(path.join(GN_DIR, '.git'))
}

function pathToPatchName(filePath) {
  return filePath.replace(/\//g, '-') + '.patch'
}

function patchNameToPath(patchName) {
  return patchName.replace('.patch', '').replace(/-/g, '/')
}

function calculateChecksum(filePath) {
  const content = fs.readFileSync(filePath)
  return crypto.createHash('sha256').update(content).digest('hex')
}

module.exports = {
  ROOT_DIR,
  GN_DIR,
  PATCHES_DIR,
  VERSION_FILE,
  GN_REPO,
  SEPARATOR,
  fmt,
  loadEnv,
  logStart,
  logFinish,
  run,
  runGit,
  getGnVersion,
  gnDirExists,
  pathToPatchName,
  patchNameToPath,
  calculateChecksum,
}
