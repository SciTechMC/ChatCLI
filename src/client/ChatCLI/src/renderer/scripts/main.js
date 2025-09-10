import { store } from './core/store.js';

import { connectWS, chatSend } from './sockets/chatSocket.js';
import { setupModalClosing } from './ui/modals.js';
import { initTypingIndicator } from './ui/typing.js';
import { showToast } from './ui/toasts.js';

import { autoLoginOrRedirect, wireProfileAndAccount, putUsernameInUI } from './auth/session.js';

import { loadChats } from './chats/chatList.js';
import { renderArchivedChats, archiveChat, handleArchiveChat } from './chats/archive.js';
import { selectChat, sendMessage, updateSendButtonState, onWSNewMessage, onWSTyping, onWSUserStatus } from './chats/chatSession.js';
import { openGroupEditor, initGroupEditor } from './chats/groupEditor.js';
import { loadGroupMembers } from './chats/groupService.js';

import { connectCallWS } from './calls/callSockets.js';
import { startCall, joinCall, endCall, toggleMute } from './calls/rtc.js';

// --- events from ws
window.addEventListener('chat:new-message', onWSNewMessage);
window.addEventListener('chat:user-typing', onWSTyping);
window.addEventListener('chat:user-status', onWSUserStatus);

// archive UX events
window.addEventListener('chat:archive', (ev) => handleArchiveChat(ev.detail.chatID));
window.addEventListener('chat:reload', async () => { await loadChats(); });

// DOM ready
document.addEventListener('DOMContentLoaded', async () => {
  // Cache DOM refs
  store.refs = {
    chatListEl: document.querySelector('.chat-list'),
    messagesEl: document.querySelector('.chat-messages'),
    messageInput: document.querySelector('.message-input'),
    charCounter: document.getElementById('charCounter'),
    sendBtn: document.querySelector('.send-button'),
    logoutBtn: document.querySelector('.logout-button'),
    chatTitle: document.querySelector('.chat-title'),
    editMembersBtn: document.getElementById('manageUsersBtn'),

    // placeholder created below
    placeholder: null,

    // modals
    profileModal: document.getElementById('profileModal'),
    profileForm: document.getElementById('profileForm'),
    closeProfileBtn: document.getElementById('closeProfileModal'),
    cancelProfileBtn: document.getElementById('cancelProfile'),
    disableAccountBtn: document.querySelector('#profileModal button[name="disable"]'),
    deleteAccountBtn: document.querySelector('#profileModal button[name="delete"]'),

    createChatModal: document.getElementById('createChatModal'),
    privateChatSection: document.getElementById('privateChatSection'),
    groupChatSection: document.getElementById('groupChatSection'),
    newChatInput: document.querySelector('#privateChatSection input[name="receiver"]'),
    newGroupNameInput: document.querySelector('#groupChatSection input[name="groupName"]'),
    groupMemberInput: document.querySelector('#groupChatSection input[name="members"]'),
    createChatSubmitBtn: document.getElementById('createChatSubmitBtn'),
    closeCreateChatBtn: document.getElementById('closeCreateChat'),
    cancelCreateChatBtn: document.getElementById('cancelCreateChat'),

    groupEditorModal: document.getElementById('groupEditorModal'),
    groupMemberList: document.querySelector('#groupEditorModal .user-list'),
    editMemberInput: document.querySelector('#groupEditorModal .user-add-input'),
    editMemberAddBtn: document.querySelector('#groupEditorModal .user-add-button'),
    closeGroupEditorBtn: document.getElementById('closeGroupEditor'),
    cancelGroupEditBtn: document.getElementById('cancelGroupEdit'),
    saveGroupChangesBtn: document.getElementById('saveGroupChanges'),

    confirmationModal: document.getElementById('confirmationModal'),
    confirmationTitle: document.getElementById('confirmationTitle'),
    confirmationMessage: document.getElementById('confirmationMessage'),
    closeConfirmationModalBtn: document.getElementById('closeConfirmationModal'),
    cancelConfirmBtn: document.getElementById('cancelConfirmBtn'),
    confirmActionBtn: document.getElementById('confirmActionBtn'),

    resetPasswordModal: document.getElementById('resetPasswordModal'),
    closeResetPasswordModalBtn: document.getElementById('closeResetPasswordModal'),
    cancelResetPasswordBtn: document.getElementById('cancelResetPassword'),
    submitResetPasswordBtn: document.getElementById('submitResetPassword'),

    // calls UI
    statusEl: document.getElementById('status'),
    btnStartCall: document.getElementById('btnStartCall'),
    btnJoinCall: document.getElementById('btnJoinCall'),
    btnLeave: document.getElementById('btnLeave'),
    btnMute: document.getElementById('btnMute'),
    remoteAudio: document.getElementById('remoteAudio')
  };

  // disable call buttons initially
  if (store.refs.btnStartCall) store.refs.btnStartCall.disabled = true;
  if (store.refs.btnJoinCall)  store.refs.btnJoinCall.disabled  = true;
  if (store.refs.btnLeave)     store.refs.btnLeave.disabled     = true;
  if (store.refs.btnMute)      store.refs.btnMute.disabled      = true;

  // Placeholder
  const placeholder = document.createElement('div');
  placeholder.id = 'no-chat-selected';
  placeholder.textContent = 'Select a chat to start messaging';
  Object.assign(placeholder.style, {
    display: 'flex', justifyContent: 'center', alignItems: 'center',
    height: '100%', color: 'var(--text-secondary)'
  });
  store.refs.messagesEl.appendChild(placeholder);
  store.refs.placeholder = placeholder;

  setupModalClosing();
  initTypingIndicator();
  initGroupEditor();

  // auto-login
  const ok = await autoLoginOrRedirect();
  if (!ok) return;

  putUsernameInUI();

  // Create chat modal radio switching
  document.querySelectorAll('input[name="chatType"]').forEach(radio => {
    radio.addEventListener('change', function() {
      const { privateChatSection, groupChatSection, newChatInput, newGroupNameInput, groupMemberInput } = store.refs;
      if (this.value === 'private') {
        privateChatSection.classList.remove('hidden');
        groupChatSection.classList.add('hidden');
        if (newGroupNameInput) newGroupNameInput.value = '';
        if (groupMemberInput) groupMemberInput.value = '';
      } else {
        privateChatSection.classList.add('hidden');
        groupChatSection.classList.remove('hidden');
        if (newChatInput) newChatInput.value = '';
      }
    });
  });

  // open create chat modal
  document.getElementById('openCreateChat')?.addEventListener('click', () => {
    const { privateChatSection, groupChatSection, newChatInput, newGroupNameInput, groupMemberInput, createChatModal } = store.refs;
    const selectedType = document.querySelector('input[name="chatType"]:checked')?.value;
    if (selectedType === 'group') {
      privateChatSection.classList.add('hidden');
      groupChatSection.classList.remove('hidden');
    } else {
      privateChatSection.classList.remove('hidden');
      groupChatSection.classList.add('hidden');
    }
    newChatInput.value = '';
    newGroupNameInput.value = '';
    groupMemberInput.value = '';
    import('./ui/modals.js').then(({ showModal }) => showModal(createChatModal));
  });

  // Create chat modal close/cancel
  if (store.refs.closeCreateChatBtn) store.refs.closeCreateChatBtn.addEventListener('click', async () => {
    const { hideModal } = await import('./ui/modals.js');
    hideModal(store.refs.createChatModal);
  });
  if (store.refs.cancelCreateChatBtn) store.refs.cancelCreateChatBtn.addEventListener('click', async () => {
    const { hideModal } = await import('./ui/modals.js');
    hideModal(store.refs.createChatModal);
  });

  // Create chat submit
  if (store.refs.createChatSubmitBtn) {
    store.refs.createChatSubmitBtn.addEventListener('click', async () => {
      const { newChatInput, newGroupNameInput, groupMemberInput, createChatModal } = store.refs;
      const { showModal, hideModal } = await import('./ui/modals.js');
      const { apiRequest } = await import('./core/api.js');
      const { showToast } = await import('./ui/toasts.js');

      const chatType = document.querySelector('input[name="chatType"]:checked')?.value;
      if (!chatType) return showToast('Please select a chat type', 'error');

      if (chatType === 'private') {
        const receiver = newChatInput.value.trim();
        if (!receiver) return showToast('Please enter a username', 'error');

        try {
          await apiRequest('/chat/create-chat', {
            body: JSON.stringify({ receiver, session_token: store.token })
          });
          showToast('Private chat created!', 'info');
          hideModal(createChatModal);
          newChatInput.value = '';
          await loadChats();
        } catch (err) {
          showToast(err.message || 'Could not create private chat', 'error');
        }
      } else {
        const groupName = newGroupNameInput.value.trim();
        const membersInput = groupMemberInput.value.trim();
        if (!groupName)      return showToast('Please enter a group name', 'error');
        if (!membersInput)   return showToast('Please add at least one member', 'error');

        const members = membersInput.split(',').map(m => m.trim()).filter(Boolean);
        try {
          const result = await apiRequest('/chat/create-group', {
            body: JSON.stringify({ session_token: store.token, name: groupName, members })
          });
          if (!result.chatID) throw new Error('Failed to create group');
          const newChatID = result.chatID;
          showToast('Group created!', 'info');
          hideModal(createChatModal);
          newGroupNameInput.value = '';
          groupMemberInput.value = '';
          await loadChats();
          selectChat(newChatID);
        } catch (err) {
          showToast(err.message || 'Could not create group', 'error');
        }
      }
    });
  }

  // Manage group members button
  if (store.refs.editMembersBtn) {
    store.refs.editMembersBtn.addEventListener('click', openGroupEditor);
  }

  // Connect chat WS + initial chats
  connectWS();
  await loadChats();
  updateSendButtonState();

  // Message input events
  if (store.refs.sendBtn) store.refs.sendBtn.addEventListener('click', sendMessage);

  if (store.refs.messageInput) {
    store.refs.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    store.refs.messageInput.addEventListener('input', () => {
      const el = store.refs.messageInput;
      el.style.height = 'auto';
      const maxH = 200;
      const needed = el.scrollHeight;
      if (needed <= maxH) { el.style.height = `${needed}px`; el.style.overflowY = 'hidden'; }
      else                { el.style.height = `${maxH}px`;   el.style.overflowY = 'auto'; }
      updateSendButtonState();

      const len = el.value.length;
      const cc = store.refs.charCounter;
      if (len >= 1950) {
        cc.style.display = 'block';
        cc.textContent = len <= 2100 ? `${len}/2048` : 'Message too long';
      } else {
        cc.style.display = 'none';
      }
      el.classList.toggle('error', len > 2048);
      cc.classList.toggle('error', len > 2048);

      if (!store.currentChatID) return;
      chatSend({ type: 'typing', chatID: store.currentChatID });
    });
  }

  // Call buttons
  if (store.refs.btnStartCall) store.refs.btnStartCall.onclick = startCall;
  if (store.refs.btnJoinCall)  store.refs.btnJoinCall.onclick  = joinCall;
  if (store.refs.btnLeave)     store.refs.btnLeave.onclick     = () => endCall('You left');
  if (store.refs.btnMute)      store.refs.btnMute.onclick      = toggleMute;

  // Profile + account wiring
  wireProfileAndAccount();

  // Sidebar archive confirm
  window.addEventListener('chat:confirm-archive', async (ev) => {
    const { showConfirmationModal } = await import('./ui/modals.js');
    showConfirmationModal(
      'Are you sure you want to archive this chat? You can still rejoin it later.',
      'Archive Chat',
      async () => { 
        const { archiveChat } = await import('./chats/archive.js');
        await archiveChat(ev.detail.chatID);
      }
    );
  });
});
