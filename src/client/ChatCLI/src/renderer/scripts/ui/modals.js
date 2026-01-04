import { store } from '../core/store.js';

export function setupModalClosing() {
  document.querySelectorAll('.modal-close').forEach(button => {
    button.addEventListener('click', () => {
      const modal = button.closest('.modal');
      if (modal) hideModal(modal);
    });
  });
  document.querySelectorAll('.modal-button.secondary').forEach(button => {
    if (button.id.includes('cancel') || button.textContent.includes('Cancel')) {
      button.addEventListener('click', () => {
        const modal = button.closest('.modal');
        if (modal) hideModal(modal);
      });
    }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      const activeModal = document.querySelector('.modal.active');
      if (activeModal) hideModal(activeModal);
    }
  });
}

export function showModal(modal) {
  let isMouseDownOnBackdrop = false;

  const handleMouseDown = (e) => {
    isMouseDownOnBackdrop = (e.target === modal);
  };

  const handleMouseUp = (e) => {
    if (e.target === modal && isMouseDownOnBackdrop) {
      hideModal(modal);
    }
    isMouseDownOnBackdrop = false;
  };

  if (modal._onMouseDown) {
    modal.removeEventListener('mousedown', modal._onMouseDown);
    modal.removeEventListener('mouseup', modal._onMouseUp);
  }

  modal._onMouseDown = handleMouseDown;
  modal._onMouseUp = handleMouseUp;

  modal.addEventListener('mousedown', handleMouseDown);
  modal.addEventListener('mouseup', handleMouseUp);

  modal.classList.add('active');
  modal.style.pointerEvents = 'all';
  const content = modal.querySelector('.modal-content');
  if (content) content.style.transform = 'translateY(0)';
}

export function hideModal(modal) {
  if (!modal) return;

  if (modal._onMouseDown) {
    modal.removeEventListener('mousedown', modal._onMouseDown);
    modal.removeEventListener('mouseup', modal._onMouseUp);
    delete modal._onMouseDown;
    delete modal._onMouseUp;
  }

  modal.classList.remove('active');
  modal.style.pointerEvents = 'none';
  const content = modal.querySelector('.modal-content');
  if (content) content.style.transform = 'translateY(20px)';
}

export function showConfirmationModal(message, title = 'Confirm Action', onConfirm) {
  const {
    confirmationModal, confirmationTitle, confirmationMessage,
    confirmActionBtn, cancelConfirmBtn, closeConfirmationModalBtn
  } = store.refs;

  confirmationMessage.textContent = message;
  confirmationTitle.textContent = title;
  showModal(confirmationModal);

  const keyHandler = (event) => {
    if (event.key === 'Enter') { event.preventDefault(); confirmHandler(); }
    if (event.key === 'Escape') { cleanup(); hideModal(confirmationModal); }
  };
  document.addEventListener('keydown', keyHandler);

  function cleanup() {
    document.removeEventListener('keydown', keyHandler);
    confirmActionBtn.onclick = null;
    cancelConfirmBtn.onclick = null;
    closeConfirmationModalBtn.onclick = null;
  }

  const confirmHandler = async () => {
    cleanup(); hideModal(confirmationModal);
    await onConfirm?.();
  };

  confirmActionBtn.onclick = confirmHandler;
  cancelConfirmBtn.onclick = () => { cleanup(); hideModal(confirmationModal); };
  closeConfirmationModalBtn.onclick = () => { cleanup(); hideModal(confirmationModal); };

  return cleanup;
}
