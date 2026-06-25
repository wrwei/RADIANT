import { ref } from "vue";

// Two draggable splitters for the 3-pane layout. Returns the left/right pane
// widths (px) and pointer-down handlers that drag them within sane bounds.
export function useResizable() {
  const leftWidth = ref(300);
  const rightWidth = ref(340);

  function startDrag(side: "left" | "right", e: PointerEvent): void {
    e.preventDefault();
    const startX = e.clientX;
    const startLeft = leftWidth.value;
    const startRight = rightWidth.value;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    function onMove(ev: PointerEvent): void {
      if (side === "left") {
        leftWidth.value = Math.max(220, Math.min(520, startLeft + (ev.clientX - startX)));
      } else {
        rightWidth.value = Math.max(220, Math.min(620, startRight - (ev.clientX - startX)));
      }
    }
    function onUp(): void {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
  }

  return { leftWidth, rightWidth, startDrag };
}
