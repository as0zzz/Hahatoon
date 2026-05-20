document.addEventListener("DOMContentLoaded", () => {
  let draggedCard = null;
  let sourceContainer = null;
  let placeholder = null;

  function csrfToken() {
    const cookieMatch = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    if (cookieMatch) return decodeURIComponent(cookieMatch[1]);
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  // Create a visual placeholder line that shows where the card will land
  function createPlaceholder() {
    const el = document.createElement("div");
    el.className = "kanban-placeholder";
    return el;
  }

  // Find the card we should insert BEFORE based on cursor Y position
  function getInsertBeforeCard(container, clientY) {
    const cards = [...container.querySelectorAll(".kanban-card:not(.dragging)")];
    for (const card of cards) {
      const rect = card.getBoundingClientRect();
      if (clientY < rect.top + rect.height / 2) {
        return card;
      }
    }
    return null; // append at end
  }

  function removePlaceholder() {
    if (placeholder && placeholder.parentNode) {
      placeholder.parentNode.removeChild(placeholder);
    }
  }

  // --- Init cards ---
  document.querySelectorAll(".kanban-card").forEach((card) => {
    card.addEventListener("dragstart", (event) => {
      draggedCard = card;
      sourceContainer = card.closest(".kanban-cards");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", card.dataset.taskId);
      // Defer so the browser captures the full-opacity card for the ghost
      requestAnimationFrame(() => {
        card.classList.add("dragging");
      });
    });

    card.addEventListener("dragend", () => {
      if (draggedCard) {
        draggedCard.classList.remove("dragging");
      }
      draggedCard = null;
      sourceContainer = null;
      removePlaceholder();
      document.querySelectorAll(".kanban-column.drag-over").forEach((c) => {
        c.classList.remove("drag-over");
      });
    });

    // Prevent navigation after a drag
    card.addEventListener("click", (event) => {
      if (card.dataset.justDropped === "1") {
        event.preventDefault();
        event.stopPropagation();
        delete card.dataset.justDropped;
      }
    });
  });

  // --- Columns ---
  document.querySelectorAll(".kanban-column").forEach((column) => {
    const cardsContainer = column.querySelector(".kanban-cards");
    if (!cardsContainer) return;

    column.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      if (!draggedCard) return;

      column.classList.add("drag-over");

      // Position the placeholder where the card would be inserted
      if (!placeholder) placeholder = createPlaceholder();
      const before = getInsertBeforeCard(cardsContainer, event.clientY);
      if (before) {
        cardsContainer.insertBefore(placeholder, before);
      } else {
        cardsContainer.appendChild(placeholder);
      }
    });

    column.addEventListener("dragleave", (event) => {
      if (!column.contains(event.relatedTarget)) {
        column.classList.remove("drag-over");
        // Only remove placeholder if it's inside THIS column
        if (placeholder && cardsContainer.contains(placeholder)) {
          removePlaceholder();
        }
      }
    });

    column.addEventListener("drop", async (event) => {
      event.preventDefault();
      column.classList.remove("drag-over");

      if (!draggedCard || !sourceContainer) {
        removePlaceholder();
        return;
      }

      const targetStatus = column.dataset.status;
      const srcContainer = sourceContainer;

      // Same column, same position — just clean up
      if (srcContainer === cardsContainer && !placeholder) {
        removePlaceholder();
        return;
      }

      draggedCard.dataset.justDropped = "1";
      draggedCard.classList.remove("dragging");

      // Hide empty message in target
      const targetEmpty = cardsContainer.querySelector("p.empty");
      if (targetEmpty) targetEmpty.remove();

      // Insert card at the placeholder position (or at end if no placeholder)
      if (placeholder && placeholder.parentNode === cardsContainer) {
        cardsContainer.insertBefore(draggedCard, placeholder);
      } else {
        cardsContainer.appendChild(draggedCard);
      }
      removePlaceholder();

      // Show empty in source if it's now empty
      if (srcContainer !== cardsContainer &&
          srcContainer.querySelectorAll(".kanban-card").length === 0) {
        const p = document.createElement("p");
        p.className = "empty";
        p.textContent = "Нет задач.";
        srcContainer.appendChild(p);
      }

      // Skip server call if dropped in the same column
      if (srcContainer === cardsContainer) return;

      // Send to server
      try {
        const body = new URLSearchParams({ status: targetStatus });
        const response = await fetch(draggedCard.dataset.changeUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": csrfToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body,
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (!data.ok) throw new Error("Rejected");
      } catch (err) {
        console.error("Kanban drop failed, reverting:", err);

        // Revert card to source
        srcContainer.appendChild(draggedCard);

        const srcEmpty = srcContainer.querySelector("p.empty");
        if (srcEmpty) srcEmpty.remove();

        if (cardsContainer.querySelectorAll(".kanban-card").length === 0) {
          const p = document.createElement("p");
          p.className = "empty";
          p.textContent = "Нет задач.";
          cardsContainer.appendChild(p);
        }
      }
    });
  });
});
