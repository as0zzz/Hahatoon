window.ttmModal = {
  async show({ title, text, type = 'confirm', placeholder = '', confirmText = 'Подтвердить', cancelText = 'Отмена', confirmColor = '#ef4444' }) {
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'ttm-modal-overlay';
      
      const modal = document.createElement('div');
      modal.className = 'ttm-modal';
      
      let inputHtml = '';
      if (type === 'prompt') {
        inputHtml = `<input type="text" class="ttm-modal-input" placeholder="${placeholder}" />`;
      }

      modal.innerHTML = `
        <button class="ttm-modal-close" aria-label="Закрыть">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
        <h3 class="ttm-modal-title">${title}</h3>
        ${text ? `<p class="ttm-modal-text">${text}</p>` : ''}
        ${inputHtml}
        <div class="ttm-modal-actions">
          <button class="ttm-modal-btn ttm-modal-cancel">${cancelText}</button>
          <button class="ttm-modal-btn ttm-modal-confirm" style="background: ${confirmColor}; color: white;">${confirmText}</button>
        </div>
      `;
      
      overlay.appendChild(modal);
      document.body.appendChild(overlay);

      const input = modal.querySelector('.ttm-modal-input');
      if (input) input.focus();
      
      const close = () => {
        overlay.classList.add('ttm-modal-closing');
        setTimeout(() => overlay.remove(), 200);
      };

      modal.querySelector('.ttm-modal-close').onclick = () => { close(); resolve(false); };
      modal.querySelector('.ttm-modal-cancel').onclick = () => { close(); resolve(false); };
      modal.querySelector('.ttm-modal-confirm').onclick = () => {
        close();
        if (type === 'prompt') resolve(input ? input.value : '');
        else resolve(true);
      };
      
      overlay.onclick = (e) => {
        if (e.target === overlay) { close(); resolve(false); }
      };

      if (input) {
        input.onkeydown = (e) => {
          if (e.key === 'Enter') {
            close();
            resolve(input.value);
          }
        };
      }
      
      requestAnimationFrame(() => overlay.classList.add('ttm-modal-open'));
    });
  },
  
  async confirm(title, text, confirmText = 'Подтвердить', confirmColor = '#ef4444') {
    return this.show({ title, text, type: 'confirm', confirmText, confirmColor });
  },

  async prompt(title, placeholder = '') {
    return this.show({ title, text: '', type: 'prompt', placeholder, confirmText: 'Сохранить', confirmColor: 'var(--blue)' });
  }
};
