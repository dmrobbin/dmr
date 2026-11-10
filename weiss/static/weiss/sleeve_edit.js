// The card sleeve form (staff): its conditions' rows, and the cropper for its picture.
(() => {
  const form = document.querySelector("[data-sleeve-form]");
  if (!form) return;

  // --- Conditions: each row's kind says which target select is in use (a disabled one isn't sent, so every row
  // sends exactly one target: the server reads the rows' kinds, targets and counts side by side) -----------------

  const rows = form.querySelector("[data-condition-rows]");
  const template = form.querySelector("[data-condition-template]");

  function showTarget(row) {
    const kind = row.querySelector("[data-kind]");
    const wants = kind.selectedOptions[0] ? kind.selectedOptions[0].dataset.target || "" : "";
    for (const el of row.querySelectorAll("[data-target-for]")) {
      const on = el.dataset.targetFor === wants;
      el.disabled = !on;
      if (el.tagName === "SELECT") el.hidden = !on;
    }
  }

  rows.addEventListener("change", (event) => {
    if (event.target.matches("[data-kind]")) showTarget(event.target.closest("[data-condition-row]"));
  });
  rows.addEventListener("click", (event) => {
    if (event.target.closest("[data-remove-condition]")) event.target.closest("[data-condition-row]").remove();
  });
  form.querySelector("[data-add-condition]").addEventListener("click", () => {
    rows.appendChild(template.content.cloneNode(true));
    const row = rows.lastElementChild;
    showTarget(row);
    row.querySelector("[data-kind]").focus();
  });
  rows.querySelectorAll("[data-condition-row]").forEach(showTarget);

  // --- The cropper: the picture sits in a card-shaped frame, always covering it, dragged to move and zoomed with
  // the slider. Saving draws what the frame shows at the server's size and sends that as the image -------------

  const cropper = form.querySelector("[data-cropper]");
  if (!cropper) return;
  const frame = cropper.querySelector("[data-crop-frame]");
  const image = cropper.querySelector("[data-crop-image]");
  const zoom = cropper.querySelector("[data-crop-zoom]");
  const output = cropper.querySelector("[data-crop-output]");
  const OUT_W = Number(cropper.dataset.width);
  const OUT_H = Number(cropper.dataset.height);

  let view = null; // {scale, x, y}: the picture's size against its own, and where its top left is in the frame (px)
  let drag = null;

  const box = () => ({ w: frame.clientWidth, h: frame.clientHeight });
  const coverScale = () => Math.max(box().w / image.naturalWidth, box().h / image.naturalHeight);

  function place() {
    const { w, h } = box();
    const width = image.naturalWidth * view.scale;
    const height = image.naturalHeight * view.scale;
    view.x = Math.min(0, Math.max(w - width, view.x));
    view.y = Math.min(0, Math.max(h - height, view.y));
    Object.assign(image.style, { width: `${width}px`, height: `${height}px`, left: `${view.x}px`, top: `${view.y}px` });
  }

  // Zoom about the frame's middle, so what's there stays there.
  function zoomTo(level) {
    const { w, h } = box();
    const next = coverScale() * level;
    const cx = (w / 2 - view.x) / view.scale;
    const cy = (h / 2 - view.y) / view.scale;
    view = { scale: next, x: w / 2 - cx * next, y: h / 2 - cy * next };
    place();
  }

  cropper.querySelector("[data-crop-source]").addEventListener("change", (event) => {
    const file = event.target.files[0];
    output.value = "";
    if (!file) return;
    image.src = URL.createObjectURL(file);
  });

  image.addEventListener("load", () => {
    const { w, h } = box();
    const scale = coverScale();
    view = { scale, x: (w - image.naturalWidth * scale) / 2, y: (h - image.naturalHeight * scale) / 2 };
    zoom.value = 1;
    image.hidden = false;
    cropper.querySelector("[data-crop-zoom-label]").hidden = false;
    const current = cropper.querySelector("[data-crop-current]");
    if (current) current.hidden = true;
    cropper.querySelector("[data-crop-help]").textContent = "Drag the picture, and zoom, until the frame shows what the sleeve should.";
    place();
  });
  image.addEventListener("error", () => {
    image.hidden = true;
    view = null;
    cropper.querySelector("[data-crop-help]").textContent = "That picture couldn't be read. Try a PNG, JPEG, GIF or WebP.";
  });

  zoom.addEventListener("input", () => view && zoomTo(Number(zoom.value)));
  frame.addEventListener("wheel", (event) => {
    if (!view) return;
    event.preventDefault();
    zoom.value = Math.min(Number(zoom.max), Math.max(1, Number(zoom.value) - event.deltaY * 0.002));
    zoomTo(Number(zoom.value));
  }, { passive: false });

  frame.addEventListener("pointerdown", (event) => {
    if (!view) return;
    drag = { id: event.pointerId, x: event.clientX - view.x, y: event.clientY - view.y };
    frame.setPointerCapture(event.pointerId);
    frame.classList.add("dragging");
  });
  frame.addEventListener("pointermove", (event) => {
    if (!drag || event.pointerId !== drag.id) return;
    view.x = event.clientX - drag.x;
    view.y = event.clientY - drag.y;
    place();
  });
  const endDrag = () => {
    drag = null;
    frame.classList.remove("dragging");
  };
  frame.addEventListener("pointerup", endDrag);
  frame.addEventListener("pointercancel", endDrag);

  // On saving: what the frame shows, drawn at OUT_W × OUT_H, becomes the form's image.
  let cropped = false;
  form.addEventListener("submit", (event) => {
    if (!view || cropped) return;
    event.preventDefault();
    const { w } = box();
    const canvas = document.createElement("canvas");
    canvas.width = OUT_W;
    canvas.height = OUT_H;
    const ratio = OUT_W / w; // frame pixels to output pixels
    canvas.getContext("2d").drawImage(image, view.x * ratio, view.y * ratio, image.naturalWidth * view.scale * ratio, image.naturalHeight * view.scale * ratio);
    const save = form.querySelector("[data-sleeve-save]");
    save.disabled = true;
    canvas.toBlob((blob) => {
      save.disabled = false;
      if (!blob) {
        cropper.querySelector("[data-crop-help]").textContent = "The picture couldn't be cropped. Try another.";
        return;
      }
      const files = new DataTransfer();
      files.items.add(new File([blob], blob.type === "image/webp" ? "sleeve.webp" : "sleeve.png", { type: blob.type }));
      output.files = files.files;
      cropped = true;
      form.requestSubmit ? form.requestSubmit() : form.submit();
    }, "image/webp", 0.9);
  });
})();
