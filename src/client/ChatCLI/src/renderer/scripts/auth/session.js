import { store } from '../core/store.js';
import { setAccess, apiRequest } from '../core/api.js';
import { showToast } from '../ui/toasts.js';
import { showModal, hideModal, showConfirmationModal } from '../ui/modals.js';

export async function autoLoginOrRedirect() {
  store.username = await window.secureStore.get('username');

  if (!store.username || store.preventReconnect) {
    console.error('No stored username or reconnect prevented, redirecting to login.');
    window.location.href = 'index.html';
    return false;
  }

  const savedSession = await window.secureStore.get('session_token');
  if (savedSession) {
    setAccess(savedSession);
    return true;
  }

  try {
    const r = await window.auth.refresh(store.username);
    if (!r || !r.ok || !r.access_token) throw new Error('Refresh failed');

    setAccess(r.access_token);

    if (r.refresh_token && window.auth?.storeRefresh) {
      await window.auth.storeRefresh(store.username, r.refresh_token);
    }
    if (window.secureStore?.set) {
      await window.secureStore.set('session_token', r.access_token);
    }

    return true;
  } catch {
    showToast('Session expired. Please log in again.', 'error');
    console.error('Session refresh failed, redirecting to login.');
    window.location.href = 'index.html';
    return false;
  }
}


export function wireProfileAndAccount() {
  const {
    profileModal, profileForm, closeProfileBtn, cancelProfileBtn,
    disableAccountBtn, deleteAccountBtn,
    resetPasswordModal, closeResetPasswordModalBtn, cancelResetPasswordBtn, submitResetPasswordBtn
  } = store.refs;

  // open profile
  document.getElementById('profileBtn')?.addEventListener('click', async () => {
    try {
      const profile = await apiRequest('/user/profile', {
        body: JSON.stringify({ session_token: store.token })
      });
      profileForm.querySelector('input[name="username"]').value = profile.username || '';
      profileForm.querySelector('input[name="email"]').value = profile.email || '';
      store.currentEmail = profile.email;
      showModal(profileModal);
    } catch (err) {
      showToast('Failed to load profile: ' + (err.message || 'Unknown error'), 'error');
    }
  });

  closeProfileBtn.addEventListener('click', () => hideModal(profileModal));
  cancelProfileBtn.addEventListener('click', () => hideModal(profileModal));

  profileForm.addEventListener('submit', async e => {
    e.preventDefault();
  
    const newUsername = profileForm.querySelector('input[name="username"]').value.trim();
    const newEmail    = profileForm.querySelector('input[name="email"]').value.trim();
  
    let storedEmail = null;
    try { storedEmail = await window.secureStore.get('email'); } catch (_) {}

    const usernameChanged = newUsername !== store.username;
    const emailChanged = newEmail !== store.currentEmail;
  
    // Ask for confirmation only if username or email was changed
    if (usernameChanged || emailChanged) {
      showConfirmationModal(
        'Changing your username and/or email requires you to log in again to confirm the update.',
        'Re-login Required',
        async () => {
          try {
            const result = await apiRequest('/user/submit-profile', {
              body: JSON.stringify({
                session_token: store.token,
                username: newUsername,
                email: newEmail
              })
            });
  
            hideModal(profileModal);
  
            const changeType = emailChanged ? 'email' : 'username';

            await forceLogoutAfterProfileChange(
              changeType,
              newUsername
            );
          } catch (err) {
            showToast('Failed to update profile: ' + (err.message || 'Unknown error'), 'error');
          }
        }
      );
  
      return;
    }

    try {
      const result = await apiRequest('/user/submit-profile', {
        body: JSON.stringify({
          session_token: store.token,
          username: newUsername,
          email: newEmail
        })
      });
      hideModal(profileModal);
      showToast('Profile saved.', 'success');
    } catch (err) {
      showToast('Failed to update profile: ' + (err.message || 'Unknown error'), 'error');
    }
  });
  
  // Disable account
  if (disableAccountBtn) {
    disableAccountBtn.addEventListener('click', () => {
      hideModal(profileModal);
      showConfirmationModal(
        'Disabling your account will prevent you from logging in until you reactivate via the email we\'ll send. Continue?',
        'Disable Account',
        async () => {
          try {
            await apiRequest('/user/submit-profile', {
              body: JSON.stringify({ session_token: store.token, disable: 1, delete: 0 })
            });
            showToast('Account disabled.', 'warning');
            await window.secureStore.delete('session_token');
            await window.secureStore.delete('refresh_token');
            await window.secureStore.delete('username');
            await window.secureStore.delete('email');
            window.location.href = 'index.html';
          } catch (err) {
            showToast('Failed to disable account: ' + (err.message || 'Unknown error'), 'error');
          }
        }
      );
    });
  }

  // Delete account
  if (deleteAccountBtn) {
    deleteAccountBtn.addEventListener('click', () => {
      hideModal(profileModal);
      showConfirmationModal(
        'Warning: This will PERMANENTLY DELETE your account and all associated data, including messages and chats. This action cannot be undone. Continue?',
        'Delete Account',
        async () => {
          try {
            await apiRequest('/user/submit-profile', {
              body: JSON.stringify({ session_token: store.token, disable: 0, delete: 1 })
            });
            showToast('Account deleted.', 'error');
            await window.secureStore.delete('session_token');
            await window.secureStore.delete('refresh_token');
            await window.secureStore.delete('username');
            await window.secureStore.delete('email');
            window.location.href = 'index.html';
          } catch (err) {
            showToast('Failed to delete account: ' + (err.message || 'Unknown error'), 'error');
          }
        }
      );
    });
  }

  // Change password
  document.getElementById('changePasswordBtn')?.addEventListener('click', () => {
    document.querySelector('#resetPasswordModal input[name="currentPassword"]').value = '';
    document.querySelector('#resetPasswordModal input[name="newPassword"]').value = '';
    document.querySelector('#resetPasswordModal input[name="confirmPassword"]').value = '';
    showModal(resetPasswordModal);
  });
  closeResetPasswordModalBtn.addEventListener('click', () => hideModal(resetPasswordModal));
  cancelResetPasswordBtn.addEventListener('click', () => hideModal(resetPasswordModal));

  submitResetPasswordBtn.addEventListener('click', async () => {
    const current  = document.querySelector('#resetPasswordModal input[name="currentPassword"]').value.trim();
    const newPw    = document.querySelector('#resetPasswordModal input[name="newPassword"]').value.trim();
    const confirmPw= document.querySelector('#resetPasswordModal input[name="confirmPassword"]').value.trim();

    if (!current || !newPw || !confirmPw) return showToast('All fields are required', 'error');
    if (newPw !== confirmPw)              return showToast('New passwords do not match', 'error');
    if (newPw.length < 8 || !/\d/.test(newPw) || !/[a-zA-Z]/.test(newPw)) {
      return showToast('Password must be at least 8 characters and include letters and numbers', 'error');
    }
    try {
      await apiRequest('/user/change-password', {
        body: JSON.stringify({ session_token: store.token, current_password: current, new_password: newPw })
      });
      showToast('Password updated. Please log in again.', 'info');
      hideModal(resetPasswordModal);
      await window.secureStore.delete('session_token');
      await window.secureStore.delete('refresh_token');
      await window.secureStore.delete('username');
      await window.secureStore.delete('email');
      setTimeout(() => { window.location.href = 'index.html'; }, 1000);
    } catch (err) {
      showToast(err.message || 'Password change failed', 'error');
    }
  });

  // Logout
  if (store.refs.logoutBtn) {
    store.refs.logoutBtn.addEventListener('click', async () => {
      try {
        await apiRequest('/user/logout-all', {
          method: 'POST',
          body: JSON.stringify({ session_token: store.token })
        });
      } catch (err) {
        console.warn('Logout-all server error:', err);
      } finally {
        try {
          if (store.username && window.auth?.clear) await window.auth.clear(store.username);
          await window.secureStore.delete('username');
          await window.secureStore.delete('email');
          await window.secureStore.delete('session_token');
          await window.secureStore.delete('refresh_token');
        } catch (e2) {
          console.warn('Local logout cleanup error:', e2);
        }
        window.location.href = 'index.html';
      }
    });
  }
}

export function putUsernameInUI() {
  const el = document.querySelector('.username');
  if (el) {
    el.textContent = store.username;
    el.style.wordBreak = 'break-all';
    el.style.fontWeight = '500';
    el.style.fontSize = '14px';
    el.style.maxWidth = '100%';
    el.style.overflowWrap = 'break-word';
    el.style.color = 'var(--text-primary)';
  }
}

async function forceLogoutAfterProfileChange(changeType, newUsername) {
  try {
    await apiRequest('/user/logout-all', {
      method: 'POST',
      body: JSON.stringify({ session_token: store.token })
    });
  } catch (_) {}

  try {
    if (store.username && window.auth?.clear) await window.auth.clear(store.username);
    const keysToDelete = ['session_token', 'refresh_token', 'username', 'email'];
    for (const key of keysToDelete) {
      await window.secureStore.delete(key);
    }
  } catch (e) {
    console.warn('Cleanup error:', e);
  }

  if (changeType === 'email') {
    showToast('Email updated. Please verify your new email.', 'info');
    window.location.href = `index.html?username=${encodeURIComponent(newUsername)}#verify`;
  } else {
    showToast('Username updated. Please log in with your new credentials.', 'success');
    window.location.href = 'index.html#login';
  }
}