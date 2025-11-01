export const store = {
  WS_URL: (window.appConfig && window.appConfig.WS_URL) || '',

  token: null,
  username: null,

  // chat
  currentChatID: null,
  currentChat: null,
  currentChatIsPrivate: false,
  archivedVisible: false,
  archivedChatsData: [],
  currentMembers: [],
  peerUsername: null,

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

  // call UI state machine
  // 'idle' | 'incoming' | 'outgoing' | 'in-call'
  callState: 'idle',
  callIncoming: null,       // { chatID, from, call_id }
  callActiveChatID: null,   // the chat hosting the active call

  // DOM refs (filled in at bootstrap)
  refs: {}
};

export const selfName = () => (store.username || '').toLowerCase();
