// Favorite stars on the sets pages (set_fav_button.html). They're plain forms; this posts them in the
// background instead, flips the star at once (and every other star for the same set on the page), and
// updates the Favorites tab's count. If the post fails the star flips back and the form posts normally.
(() => {
  const setStar = (id, favorite) => {
    document.querySelectorAll(`form[data-set-fav="${id}"] .set-fav`).forEach((button) => {
      button.setAttribute("aria-pressed", String(favorite));
      button.title = favorite ? "Remove from favorites" : "Add to favorites";
      button.querySelector(".set-fav-star").textContent = favorite ? "★" : "☆";
      const text = button.querySelector(".set-fav-text");
      if (text) text.textContent = favorite ? "Favorited" : "Favorite";
    });
  };

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-set-fav]");
    if (!form) return;
    event.preventDefault();
    const id = form.dataset.setFav;
    const favorite = form.querySelector(".set-fav").getAttribute("aria-pressed") !== "true";
    setStar(id, favorite);
    const body = new FormData(form);
    body.set("favorite", favorite ? "1" : "0");
    try {
      const response = await fetch(form.action, {
        method: "POST", body, headers: { Accept: "application/json" }, credentials: "same-origin",
      });
      if (!response.ok) throw new Error(response.statusText);
      const data = await response.json();
      setStar(id, data.favorite);
      document.querySelectorAll("[data-set-fav-count]").forEach((el) => { el.textContent = data.count; });
    } catch (error) {
      setStar(id, !favorite);
      form.submit();
    }
  });
})();
