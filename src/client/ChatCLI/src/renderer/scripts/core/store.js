export const store = {
  WS_URL: (window.appConfig && window.appConfig.WS_URL) || '',

  token: null,
  username: null,

  // chat
  currentChatID: null,
  archivedVisible: false,
  archivedChatsData: [],
  currentMembers: [],

  typingUsers: new Set(),
  typingTimeouts: new Map(),
  seenMessageIDs: new Set(),

  // call
  call: {
    callWS: null,
    pc: null,
    localStream: null,
    inCall: false,
    joiningArmed: false,
    pendingOffer: null,
    isMuted: false,
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    iceCandidateBuffer: []
  },

  // DOM refs (filled in at bootstrap)
  refs: {}
};

export const selfName = () => (store.username || '').toLowerCase();

export async function persistUsername(newUsername) {
  store.username = newUsername;

  // Best-effort persistence in both secureStore and localStorage
  try {
    if (window.secureStore?.set) {
      await window.secureStore.set('username', newUsername);
    }
  } catch (_) { /* ignore */ }

  try {
    localStorage.setItem('username', newUsername);
  } catch (_) { /* ignore */ }
}
