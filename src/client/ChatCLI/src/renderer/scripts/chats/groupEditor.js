import { store, selfName } from '../core/store.js';
import { apiRequest } from '../core/api.js';
import { showToast } from '../ui/toasts.js';
import { hideModal, showModal, showConfirmationModal } from '../ui/modals.js';
import { loadChats } from './chatList.js';
import { selectChat } from './chatSession.js';

// Initializes event listeners for the group editor modal
export function initGroupEditor() {
  const {
    groupEditorModal, groupMemberList, editMemberInput, editMemberAddBtn,
    closeGroupEditorBtn, cancelGroupEditBtn, saveGroupChangesBtn
  } = store.refs;

  if (closeGroupEditorBtn) closeGroupEditorBtn.addEventListener('click', () => hideModal(groupEditorModal));
  if (cancelGroupEditBtn) cancelGroupEditBtn.addEventListener('click', () => hideModal(groupEditorModal));
  if (saveGroupChangesBtn) saveGroupChangesBtn.addEventListener('click', () => hideModal(groupEditorModal));

  if (editMemberAddBtn) {
    editMemberAddBtn.addEventListener('click', async () => {
      const username = editMemberInput.value.trim();
      if (!username) return;
      if (store.currentMembers.includes(username)) {
        return showToast(`${username} is already in the group`, 'warning');
      }
      try {
        await apiRequest('/chat/add-members', {
          body: JSON.stringify({
            session_token: store.token,
            chatID: store.currentChatID,
            members: [username]
          })
        });

        const userItem = document.createElement('div');
        userItem.classList.add('user-item');
        const userName = document.createElement('span');
        userName.textContent = username;
        const removeBtn = document.createElement('span');
        removeBtn.classList.add('user-remove');
        removeBtn.textContent = '×';

        removeBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          const doRemove = async () => {
            try {
              await apiRequest('/chat/remove-members', {
                body: JSON.stringify({
                  session_token: store.token,
                  chatID: store.currentChatID,
                  members: [username]
                })
              });
              userItem.remove();
              store.currentMembers = store.currentMembers.filter(u => u !== username);
            } catch (err) {
              showToast('Failed to remove member: ' + err.message, 'error');
            }
          };
          if (username.toLowerCase() === selfName()) {
            showConfirmationModal(
              'Are you sure you want to leave this group? This cannot be undone unless someone else adds you back.',
              'Leave Group',
              async () => {
                await doRemove();
                await loadChats();
                selectChat(null);
              }
            );
          } else {
            doRemove();
          }
        });

        userItem.appendChild(userName);
        userItem.appendChild(removeBtn);
        groupMemberList.appendChild(userItem);

        store.currentMembers.push(username);
        editMemberInput.value = '';
      } catch (err) {
        showToast('Failed to add member: ' + (err.message || 'Unknown error'), 'error');
      }
    });
  }
}

export async function openGroupEditor() {
  if (!store.currentChatID) return;
  let members;
  try {
    const res = await apiRequest('/chat/get-members', {
      body: JSON.stringify({ session_token: store.token, chatID: store.currentChatID })
    });
    members = res.members;
  } catch (err) {
    return showToast('Failed to load group members: ' + err.message, 'error');
  }
  if (!Array.isArray(members)) {
    return showToast('Failed to load group members', 'error');
  }
  store.currentMembers = members;

  const { groupMemberList, groupEditorModal } = store.refs;
  groupMemberList.innerHTML = '';
  const me = selfName();

  members.forEach(member => {
    const userItem = document.createElement('div');
    userItem.classList.add('user-item');
    const userName = document.createElement('span');
    userName.textContent = member;
    const removeBtn = document.createElement('span');
    removeBtn.classList.add('user-remove');
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', e => {
      e.stopPropagation();
      const performRemoval = async () => {
        try {
          await apiRequest('/chat/remove-members', {
            body: JSON.stringify({
              session_token: store.token,
              chatID: store.currentChatID,
              members: [member]
            })
          });
          userItem.remove();
          store.currentMembers = store.currentMembers.filter(u => u !== member);
        } catch (err) {
          showToast('Failed to remove member: ' + err.message, 'error');
        }
      };
      if (member.toLowerCase() === me) {
        showConfirmationModal(
          'Are you sure you want to leave this group? This cannot be undone unless someone else adds you back.',
          'Leave Group',
          async () => {
            await performRemoval();
            await loadChats();
            selectChat(null);
            hideModal(groupEditorModal);
          }
        );
      } else {
        performRemoval();
      }
    });
    userItem.append(userName, removeBtn);
    groupMemberList.appendChild(userItem);
  });

  showModal(groupEditorModal);
}
