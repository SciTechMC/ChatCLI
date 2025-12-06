const keytar = require('keytar')
const SERVICE = 'ChatCLI.RefreshToken'

async function saveRefreshToken(accountId, refreshToken) {
  await keytar.setPassword(SERVICE, accountId, refreshToken)
}
async function getRefreshToken(accountId) {
  return keytar.getPassword(SERVICE, accountId) // string | null
}
async function deleteRefreshToken(accountId) {
  await keytar.deletePassword(SERVICE, accountId)
}

module.exports = { saveRefreshToken, getRefreshToken, deleteRefreshToken }