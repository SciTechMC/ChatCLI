let toastContainer;

function ensureContainer() {
  if (toastContainer) return toastContainer;
  toastContainer = document.createElement('div');
  toastContainer.id = 'toast-container';
  Object.assign(toastContainer.style, {
    position: 'fixed', top: '20px', right: '20px', zIndex: '1000'
  });
  document.body.appendChild(toastContainer);
  return toastContainer;
}

export function showToast(message, type = 'info') {
  const container = ensureContainer();
  const toast = document.createElement('div');
  toast.classList.add('toast', type);
  toast.textContent = message;
  Object.assign(toast.style, {
    padding: '12px 16px',
    backgroundColor: type === 'error' ? 'var(--danger-color)' : type === 'warning' ? '#f0ad4e' : 'var(--accent-color)',
    color: 'white',
    borderRadius: '4px',
    marginBottom: '10px',
    boxShadow: '0 2px 10px rgba(0,0,0,.2)',
    transition: 'opacity .5s'
  });
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 500); }, 3000);
}
