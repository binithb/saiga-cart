document.documentElement.dataset.keyboardNav = "ready";

document.addEventListener("keydown", function (event) {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  var tagName = event.target && event.target.tagName;
  if (tagName && /^(INPUT|TEXTAREA|SELECT)$/.test(tagName)) return;

  var destination = null;
  if (event.key === "ArrowLeft") destination = document.querySelector(".page-nav .prev");
  if (event.key === "ArrowRight") destination = document.querySelector(".page-nav .next");

  if (destination && destination.href) {
    window.location.href = destination.href;
  }
});
